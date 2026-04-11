import os
import sys
sys.dont_write_bytecode = True
import subprocess
import argparse
import tempfile
import time
import re
import zipfile
import shutil
import io
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Global tqdm and rich handle for safe access
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
    from rich.panel import Panel
    from rich.live import Live
    from rich.table import Table
    console = Console()
except ImportError:
    console = None
    Progress = None

# Platform Check
IS_WINDOWS = sys.platform == 'win32'

# ==========================================
# AUTO-DEPENDENCY INSTALLER
# ==========================================
def install_dependencies():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    req_path = os.path.abspath(os.path.join(script_dir, "..", "requirements.txt"))
    
    print(f"[System] Missing dependencies detected. Installing from {req_path}...")
    
    if not os.path.exists(req_path):
        print(f"[Error] requirements.txt not found at {req_path}")
        sys.exit(1)
        
    try:
        # pip install -r handles environment markers like '; sys_platform == "win32"' automatically
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_path])
        print("[System] Dependencies installed. Restarting script...")
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except subprocess.CalledProcessError as e:
        print(f"[Error] Failed to install dependencies: {e}")
        sys.exit(1)

try:
    import requests
    from bs4 import BeautifulSoup
    import html2text
    import docx
    import pypdf
    # OCR and Image support
    from rapidocr_onnxruntime import RapidOCR
    import cv2 
    from PIL import Image
    
    # COM for .doc (Windows only)
    if IS_WINDOWS:
        import win32com.client
        import pythoncom
    else:
        win32com = None
        pythoncom = None
except ImportError:
    install_dependencies()

# Re-import after ensure
import requests
from bs4 import BeautifulSoup
import html2text
import docx
import pypdf
from rapidocr_onnxruntime import RapidOCR
# win32com handled above with IS_WINDOWS check

# ==========================================
# CONFIGURATION
# ==========================================
class Config:
    MAX_CHARS_DEFAULT = 50000
    TRUNCATION_MSG = "\n\n[SYSTEM: CONTENT TRUNCATED DUE TO LENGTH LIMIT]"
    
    @staticmethod
    def get_script_dir():
        return os.path.dirname(os.path.abspath(__file__))

    @staticmethod
    def get_browser_path():
        # Cross-platform default paths
        if IS_WINDOWS:
            default_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Mozilla Firefox\firefox.exe",
                r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe"
            ]
        elif sys.platform == 'darwin': # macOS
            default_paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                "/Applications/Firefox.app/Contents/MacOS/firefox",
                "/usr/local/bin/google-chrome"
            ]
        else: # Linux/Other
            default_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/microsoft-edge",
                "/usr/bin/firefox",
                "/usr/local/bin/google-chrome"
            ]
        
        explicit = os.getenv("KA_BROWSER_PATH", "").strip()
        if explicit and os.path.exists(explicit):
            return explicit
        detected = next((p for p in default_paths if os.path.exists(p)), "")
        return detected or None

# ==========================================
# LOGGING
# ==========================================
def log(msg, style="blue"):
    if console:
        console.print(f"[bold {style}][Ingester][/bold {style}] {msg}")
    else:
        print(f"[Ingester] {msg}")

def log_success(msg):
    log(msg, "green")

def log_error(msg):
    log(msg, "red")

def log_warning(msg):
    log(msg, "yellow")

# ==========================================
# BROWSER DRIVER
# ==========================================
class BrowserDriver:
    @staticmethod
    def lazy_import_drission():
        try:
            from DrissionPage import ChromiumPage, ChromiumOptions
            return ChromiumPage, ChromiumOptions
        except ImportError:
            return None, None

    @staticmethod
    def fetch_html(url):
        log(f"Switching to DrissionPage for: {url}")
        ChromiumPage, ChromiumOptions = BrowserDriver.lazy_import_drission()
        if not ChromiumPage:
            return None, "[SYSTEM: DrissionPage not installed]"

        page = None
        try:
            co = ChromiumOptions()
            path = Config.get_browser_path()
            if path and os.path.exists(path):
                co.set_browser_path(path)
            
            # [LCS-FIX] 2026-01-23: Disable headless to bypass 403/404 on Zhihu/Cloudflare
            co.headless(False) 
            co.set_argument('--no-sandbox')
            co.set_argument('--disable-gpu')
            co.set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            page = ChromiumPage(co)
            page.get(url)
            time.sleep(3)
            
            # [LCS-FIX] 2026-01-25: Multi-scroll to trigger CSDN/Zhihu lazy loading
            for i in range(3):
                log(f"Scrolling ({i+1}/3)...")
                page.scroll.to_bottom()
                time.sleep(2)
            
            # [LCS-FIX] Handling Zhihu/Generic Login Popups
            try:
                # Zhihu specific close button class
                close_btn = page.ele('.Modal-closeButton', timeout=2)
                if close_btn:
                    log("Detected Zhihu Login Popup. Smashing it.")
                    close_btn.click()
                    time.sleep(1)
            except Exception:
                pass
                
            return page.html, None
        except Exception as e:
            if page: 
                try: page.quit()
                except: pass
            return None, str(e)

# ==========================================
# CONTENT PARSER
# ==========================================
class ContentParser:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        self.ocr_engine = None
        self.drission_lock = threading.Lock()

    def get_ocr_engine(self):
        if not self.ocr_engine:
            try:
                self.ocr_engine = RapidOCR()
            except Exception as e:
                log(f"Failed to initialize RapidOCR: {e}")
        return self.ocr_engine

    def perform_ocr(self, img_path):
        engine = self.get_ocr_engine()
        if not engine: return "[OCR Failed: Engine not available]"
        
        try:
            result, _ = engine(img_path)
            if result:
                text = "\n".join([line[1] for line in result])
                return text
            return "[OCR: No text found]"
        except Exception as e:
            return f"[OCR Error: {e}]"

    def clean_html(self, html, base_url=""):
        # Fix encoding if needed (UTF-8)
        if isinstance(html, bytes):
            html = html.decode('utf-8', errors='replace')
        else:
            # Check for mojibake (UTF-8 bytes misread as Latin-1)
            try:
                # If it's already a string, check if it contains characters that look like misread UTF-8
                # Common pattern: multiple high-byte characters in a row
                if any(ord(c) > 127 for c in html):
                    # Attempt to re-encode to bytes then decode properly
                    test_html = html.encode('latin-1').decode('utf-8')
                    # If it decoded without error and changed the string, use it
                    if test_html != html:
                        html = test_html
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass

        # Parse HTML with BeautifulSoup for advanced cleaning
        soup = BeautifulSoup(html, 'html.parser')

        # Remove script, style, and other non-content tags
        for tag in soup(["script", "style", "nav", "footer", "iframe", "noscript"]):
            tag.decompose()

        # Remove common ad containers by class/id patterns
        ad_patterns = [
            'ad', 'ads', 'advertisement', 'banner', 'sponsor', 'promo',
            'sidebar', 'related', 'recommend', 'popup', 'modal',
            'share', 'social', 'comment', 'disqus', 'newsletter',
            'subscription', 'cookie', 'gdpr', 'consent'
        ]

        for pattern in ad_patterns:
            # Remove by class
            for elem in soup.find_all(class_=re.compile(pattern, re.IGNORECASE)):
                elem.decompose()
            # Remove by id
            for elem in soup.find_all(id=re.compile(pattern, re.IGNORECASE)):
                elem.decompose()

        # Remove elements with common ad attributes
        for elem in soup.find_all(attrs={"data-ad": True}):
            elem.decompose()
        for elem in soup.find_all(attrs={"data-advertisement": True}):
            elem.decompose()

        # Convert back to HTML string for html2text processing
        cleaned_html = str(soup)

        if not html2text:
            log("html2text not installed. Falling back to simple text extraction.")
            return soup.get_text(separator='\n', strip=True)

        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.body_width = 0 # No wrapping
        h.protect_links = True
        if hasattr(h, 'base_url'):
            h.base_url = base_url
        markdown = h.handle(cleaned_html)

        # Post-process markdown to remove noise patterns
        lines = markdown.split('\n')
        cleaned_lines = []

        noise_keywords = [
            '关注', '推荐', '热榜', '专栏', '付费咨询', '知学堂',
            '切换模式', '登录', '注册', '下载', 'App', '验证码',
            '扫码', '开通', '无障碍', '分享', '点赞', '收藏',
            '评论', '转发', '订阅', '关注我们', '加入我们',
            '广告', '赞助', '合作', '联系我们'
        ]

        for line in lines:
            line_stripped = line.strip()
            # Skip empty lines
            if not line_stripped:
                cleaned_lines.append(line)
                continue

            # Check if line contains noise keywords (but not as part of real content)
            is_noise = False
            if len(line_stripped) < 50:  # Short lines are more likely to be UI elements
                for keyword in noise_keywords:
                    if keyword in line_stripped and len(line_stripped) < 30:
                        is_noise = True
                        break

            if not is_noise:
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def extract_metadata(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        def clean_meta_text(value):
            text = re.sub(r"\s+", " ", str(value or "")).strip()
            if text.lower() in {"", "none", "null", "untitled", "unknown"}:
                return ""
            return text

        def first_meta_content(*attribute_sets):
            for attrs in attribute_sets:
                node = soup.find("meta", attrs=attrs)
                if not node:
                    continue
                text = clean_meta_text(node.get("content"))
                if text:
                    return text
            return ""

        def first_heading_text():
            for tag_name in ("h1", "h2"):
                node = soup.find(tag_name)
                if not node:
                    continue
                text = clean_meta_text(node.get_text(" ", strip=True))
                if text:
                    return text
            return ""

        title = clean_meta_text(soup.title.string if soup.title else "")
        if not title:
            title = first_meta_content(
                {"property": "og:title"},
                {"name": "og:title"},
                {"property": "twitter:title"},
                {"name": "twitter:title"},
                {"itemprop": "headline"},
                {"name": "title"},
            )
        if not title:
            title = first_heading_text()
        if not title:
            title = "Untitled"

        author = first_meta_content(
            {"name": "author"},
            {"property": "author"},
            {"name": "article:author"},
            {"property": "article:author"},
            {"property": "og:site_name"},
        ) or "Unknown"
        return f"Title: {title}\nAuthor: {author}\nDate: {time.strftime('%Y-%m-%d')}\n"

    def process_url(self, url):
        log(f"Fetching: {url}")
        html = ""
        
        # [LCS-FIX] 2026-03-16: Force DrissionPage for Zhihu to bypass anti-crawling
        if "zhihu.com" in url:
            log("Zhihu URL detected. Skipping requests and forcing DrissionPage.")
            with self.drission_lock:
                html, err = BrowserDriver.fetch_html(url)
            if not html: return f"Error: {err}"
        else:
            try:
                resp = requests.get(url, headers=self.headers, timeout=15)
                if resp.status_code in [403, 429, 503]:
                    log(f"Requests {resp.status_code}. Invoking DrissionPage.")
                    with self.drission_lock:
                        html, err = BrowserDriver.fetch_html(url)
                    if not html: return f"Error: {err}"
                else:
                    resp.raise_for_status()
                    html = resp.text
            except Exception as e:
                log(f"Requests failed: {e}. Invoking DrissionPage.")
                with self.drission_lock:
                    html, err = BrowserDriver.fetch_html(url)
                if not html: return f"Error: {err}"

        meta = self.extract_metadata(html)
        markdown = self.clean_html(html, base_url=url)
        
        return f"{meta}\n=== CONTENT ===\n{markdown}"

    def extract_images_from_docx(self, file_path):
        """Extracts images from docx and performs OCR (Concurrent)"""
        log("Extracting images from DOCX for OCR...")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    # Find image files
                    image_files = [f for f in zip_ref.namelist() if f.startswith('word/media/') and f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
                    image_files.sort() # Keep order
                    
                    if not image_files:
                        log("No images found in DOCX.")
                        return ""

                    log(f"Found {len(image_files)} images. Processing concurrently...")
                    
                    results_map = {}
                    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
                        future_to_img = {}
                        for i, img_file in enumerate(image_files):
                            # Extract
                            zip_ref.extract(img_file, temp_dir)
                            full_path = os.path.join(temp_dir, img_file)
                            future_to_img[executor.submit(self.perform_ocr, full_path)] = (i, img_file)
                        
                        for future in as_completed(future_to_img):
                            idx, img_name = future_to_img[future]
                            try:
                                text = future.result()
                                if text and not text.startswith("[OCR"):
                                    results_map[idx] = f"\n[IMAGE {idx+1} CONTENT (OCR)]:\n{text}\n"
                                else:
                                    results_map[idx] = f"\n[IMAGE {idx+1}]: {text}\n"
                            except Exception as e:
                                results_map[idx] = f"\n[IMAGE {idx+1}]: OCR Error: {e}\n"
                            
            except zipfile.BadZipFile:
                log("Failed to unzip DOCX. Is it valid?")
                return "\n[ERROR: Failed to extract images from DOCX]"
                
        # Combine in order
        ocr_results = [results_map[i] for i in range(len(image_files))]
        return "\n=== DETECTED IMAGE TEXT ===\n" + "\n".join(ocr_results) if ocr_results else ""

    def _extract_docx_content(self, file_path):
        # Text extraction
        doc = docx.Document(file_path)
        text_content = '\n'.join([para.text for para in doc.paragraphs])
        
        # Image OCR extraction
        image_content = self.extract_images_from_docx(file_path)
        
        return text_content + "\n" + image_content

    def _process_pdf_page(self, page_idx, page):
        """Processes a single PDF page: text + images (OCR)"""
        content = ""
        # Text
        page_text = page.extract_text()
        if page_text:
            content += f"\n=== PAGE {page_idx+1} TEXT ===\n{page_text}\n"
        
        # Images
        try:
            images = page.images
            if images:
                for j, image in enumerate(images):
                    ext = os.path.splitext(image.name)[1] or ".png"
                    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp_img:
                        tmp_img.write(image.data)
                        tmp_img_path = tmp_img.name
                    
                    ocr_text = self.perform_ocr(tmp_img_path)
                    if ocr_text and not ocr_text.startswith("[OCR") and not ocr_text.startswith("[OCR: No text"):
                        content += f"\n[PAGE {page_idx+1} IMAGE {j+1} CONTENT (OCR)]:\n{ocr_text}\n"
                    
                    try: os.remove(tmp_img_path)
                    except: pass
        except Exception as img_err:
            log(f"Error extracting images from page {page_idx+1}: {img_err}")
            
        return content

    def _extract_pdf_content(self, file_path):
        log(f"Extracting content from PDF: {file_path} (Concurrent)")
        try:
            reader = pypdf.PdfReader(file_path)
            num_pages = len(reader.pages)
            log(f"PDF has {num_pages} pages. Processing concurrently...")
            
            results_map = {}
            with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
                future_to_page = {executor.submit(self._process_pdf_page, i, reader.pages[i]): i for i in range(num_pages)}
                
                for future in as_completed(future_to_page):
                    idx = future_to_page[future]
                    try:
                        results_map[idx] = future.result()
                    except Exception as e:
                        results_map[idx] = f"\n[ERROR processing PAGE {idx+1}: {e}]"
            
            # Combine in order
            full_content = "".join([results_map[i] for i in range(num_pages)])
            return full_content
                    
        except Exception as e:
            return f"\n[ERROR processing PDF: {e}]"

    def convert_doc_to_docx(self, doc_path):
        if not IS_WINDOWS:
            return None, "System is not Windows. .doc conversion requires Microsoft Word COM API (Windows only)."

        try:
            import win32com.client
            import pythoncom
        except ImportError:
            return None, "pywin32 not installed. Cannot process .doc files."

        word = None
        temp_docx = os.path.join(tempfile.gettempdir(), f"converted_{int(time.time())}.docx")
        try:
            # Initialize COM
            pythoncom.CoInitialize()
            try:
                word = win32com.client.Dispatch("Word.Application")
            except Exception:
                # Try dispatch ex if standard dispatch fails (sometimes helps)
                word = win32com.client.DispatchEx("Word.Application")
            
            if not word: return None, "Failed to initialize Word Application"

            word.Visible = False
            word.DisplayAlerts = 0
            
            doc = word.Documents.Open(os.path.abspath(doc_path))
            doc.SaveAs2(temp_docx, FileFormat=16) # 16 = wdFormatXMLDocument (docx)
            doc.Close()
            return temp_docx, None
        except Exception as e:
            return None, str(e)
        finally:
            if word:
                try: word.Quit()
                except: pass

    def process_file(self, file_path):
        log(f"Processing file: {file_path}")
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"
        
        ext = os.path.splitext(file_path)[1].lower()
        filename = os.path.basename(file_path)
        meta = f"Title: {filename}\nSource: Local File\nDate: {time.strftime('%Y-%m-%d')}\n"
        content = ""

        try:
            if ext == '.txt':
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    with open(file_path, 'r', encoding='latin-1') as f:
                        content = f.read()
            
            elif ext == '.docx':
                content = self._extract_docx_content(file_path)
            
            elif ext == '.doc':
                log("Detected .doc file. Attempting conversion to .docx...")
                temp_docx, err = self.convert_doc_to_docx(file_path)
                if temp_docx and os.path.exists(temp_docx):
                    content = self._extract_docx_content(temp_docx)
                    # Cleanup
                    try: os.remove(temp_docx)
                    except: pass
                else:
                    return f"{meta}\n=== ERROR ===\nFailed to convert .doc file: {err}\nPlease ensure Microsoft Word is installed or convert to .docx manually."

            elif ext == '.pdf':
                content = self._extract_pdf_content(file_path)
            
            elif ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                # Direct image OCR
                content = self.perform_ocr(file_path)
            
            else:
                log(f"Unknown extension {ext}, trying as text...")
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except:
                    return f"{meta}\n=== ERROR ===\nUnsupported file format: {ext}"

        except Exception as e:
            # import traceback
            # traceback.print_exc()
            return f"{meta}\n=== ERROR ===\nFailed to process file: {str(e)}"

        return f"{meta}\n=== CONTENT ===\n{content}"

# ==========================================
# TRUTH ANCHORING & CONFLICT DETECTION (2026)
# ==========================================
class ConflictDetector:
    def __init__(self):
        self.claims = []

    def detect_conflicts(self, contents):
        """
        [LCS-FEATURE] 2026-01-25: Multi-source conflict detection
        Enhanced for semantic claim extraction and cross-verification.
        """
        log("Running multi-source conflict detection...", "yellow")
        conflicts = []
        
        # 1. Numerical Conflict Detection
        all_numbers = {}
        for idx, content in enumerate(contents):
            # Focus on performance metrics (QPS, Recall, Latency)
            nums = re.findall(r'\d+(?:\.\d+)?', content)
            all_numbers[idx] = set(nums)
            
        for i in range(len(contents)):
            for j in range(i + 1, len(contents)):
                # Find overlapping numbers that might be conflicting values for the same metric
                # This is heuristic-based
                shared_context = self._find_shared_context(contents[i], contents[j])
                if shared_context:
                    for context in shared_context:
                        val1 = self._extract_value_for_context(contents[i], context)
                        val2 = self._extract_value_for_context(contents[j], context)
                        if val1 and val2 and val1 != val2:
                            conflicts.append(f"Conflict in '{context}': Source {i+1} says {val1}, Source {j+1} says {val2}")

        # 2. Claim-based Conflict (Heuristic)
        # Search for opposing sentiment words near keywords
        keywords = ["Milvus", "Zilliz", "Pinecone", "Weaviate", "Qdrant", "Chroma"]
        for kw in keywords:
            sentiments = []
            for idx, content in enumerate(contents):
                if kw in content:
                    # Very simple sentiment heuristic
                    pos = content.find(kw)
                    window = content[max(0, pos-100):min(len(content), pos+200)]
                    if "best" in window.lower() or "fast" in window.lower() or "superior" in window.lower():
                        sentiments.append((idx+1, "Positive"))
                    elif "slow" in window.lower() or "expensive" in window.lower() or "complex" in window.lower():
                        sentiments.append((idx+1, "Negative"))
            
            # If we have mixed sentiments, log as conflict
            if len(set([s[1] for s in sentiments])) > 1:
                detail = ", ".join([f"Source {s[0]}: {s[1]}" for s in sentiments])
                conflicts.append(f"Sentiment conflict on {kw}: {detail}")

        return conflicts

    def _find_shared_context(self, text1, text2):
        # Look for common entities or metrics
        metrics = ["QPS", "Recall", "Latency", "Precision", "Throughput", "Cost"]
        shared = [m for m in metrics if m.lower() in text1.lower() and m.lower() in text2.lower()]
        return shared

    def _extract_value_for_context(self, text, context):
        # Extract the number closest to the context word
        pattern = rf"{context}.*?(\d+(?:\.\d+)?)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1)
        return None

# ==========================================
# FEISHU/LARK MARKDOWN GENERATION (Productivity Track)
# ==========================================
class FeishuMarkdownGenerator:
    def __init__(self, title="Knowledge Audit"):
        self.title = title
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def generate_md(self, content_list, conflicts=None):
        """
        Generates a clean, Feishu-compatible Markdown report.
        Optimized for direct copy-paste into Feishu/Lark Docs.
        """
        log("Generating Feishu-compatible Markdown report...", "cyan")
        
        md_output = f"# {self.title}\n"
        md_output += f"> 📅 审计时间: {self.timestamp}\n\n"
        
        # 1. Conflict Report (High Priority)
        if conflicts:
            md_output += "## 🚨 冲突审计报告\n"
            md_output += "> 以下为多源内容中的潜在冲突点，请重点关注：\n\n"
            for conflict in conflicts:
                # Use quote block for conflicts to make them stand out
                md_output += f"> ⚠️ **冲突点**: {conflict}\n"
            md_output += "\n"
        else:
            md_output += "## ✅ 冲突审计报告\n"
            md_output += "> 未检测到明显的数值或主张冲突。\n\n"

        # 2. Source Content (Iterative)
        md_output += "## 📚 源内容归档\n"
        for i, content in enumerate(content_list):
            md_output += f"---\n\n"
            md_output += f"### 来源 {i+1}\n\n"
            
            # Clean content for Feishu
            # 1. Ensure max 2 consecutive newlines
            clean_content = re.sub(r'\n{3,}', '\n\n', content)
            # 2. Ensure code blocks are properly closed (basic check)
            if clean_content.count("```") % 2 != 0:
                clean_content += "\n```"
            
            md_output += clean_content + "\n\n"

        # 3. Footer
        md_output += "---\n"
        md_output += "*Generated by LCS Knowledge Absorber*\n"
        
        return md_output

# ==========================================
# REPORT GENERATION (LCS Glassmorphism 2.0)
# ==========================================
class ReportGenerator:
    def __init__(self, title="Knowledge Audit", theme="modern"):
        self.title = title
        self.theme = theme
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def generate_html(self, content_list, conflicts=None):
        """
        Generates a standardized LCS Glassmorphism 2.0 HTML report.
        Supports 'modern' (Tech) and 'ink' (Zen/Guoxue) themes.
        """
        log(f"Generating Glassmorphism 2.0 HTML report (Theme: {self.theme})...", "cyan")
        
        # Theme Variables Configuration
        if self.theme == "ink":
            # Ink & Zen Theme (Guoxue)
            # Light: Rice paper bg, Ink text, Vermilion accent
            # Dark: Dark ink stone bg, Gold/Grey text
            css_vars = """
        :root {
            --glass-bg: rgba(253, 251, 247, 0.6); /* Rice Paper */
            --glass-border: rgba(44, 44, 44, 0.1);
            --primary: #b91c1c; /* Vermilion */
            --bg-gradient: radial-gradient(circle at center, #fdfbf7, #e6e2d3);
            --text-main: #2c2c2c; /* Ink Black */
            --font-main: "Noto Serif SC", "Songti SC", serif;
        }
        [data-theme="dark"] {
            --glass-bg: rgba(28, 28, 30, 0.7); /* Ink Stone */
            --glass-border: rgba(255, 255, 255, 0.1);
            --primary: #d4af37; /* Gold */
            --bg-gradient: radial-gradient(circle at center, #1c1c1e, #000000);
            --text-main: #d1d5db;
        }
            """
            font_link = '<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700&display=swap" rel="stylesheet">'
        else:
            # Modern Tech Theme (Default)
            css_vars = """
        :root {
            --glass-bg: rgba(255, 255, 255, 0.4);
            --glass-border: rgba(255, 255, 255, 0.2);
            --primary: #3b82f6;
            --bg-gradient: radial-gradient(circle at top left, #f8fafc, #e2e8f0);
            --text-main: #1e293b;
            --font-main: 'Inter', system-ui, sans-serif;
        }
        [data-theme="dark"] {
            --glass-bg: rgba(15, 23, 42, 0.6);
            --glass-border: rgba(255, 255, 255, 0.1);
            --primary: #60a5fa;
            --bg-gradient: radial-gradient(circle at top left, #0f172a, #1e293b);
            --text-main: #f1f5f9;
        }
            """
            font_link = '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">'

        # Template for the report
        html_template = f"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title} - LCS 真理审计报告</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    {font_link}
    <style>
        {css_vars}
        
        body {{
            font-family: var(--font-main);
            background: var(--bg-gradient);
            background-attachment: fixed;
            color: var(--text-main);
            transition: all 0.5s ease;
        }}
        .glass-panel {{
            background: var(--glass-bg);
            backdrop-filter: blur(12px) saturate(180%);
            border: 1px solid var(--glass-border);
            border-radius: 1rem;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        }}
        .nav-link {{
            position: relative;
            transition: color 0.3s ease;
        }}
        .nav-link::after {{
            content: '';
            position: absolute;
            width: 0;
            height: 2px;
            bottom: -4px;
            left: 0;
            background: var(--primary);
            transition: width 0.3s ease;
        }}
        .nav-link:hover::after {{ width: 100%; }}
        
        /* Markdown Content Styling */
        pre {{
            background: rgba(0,0,0,0.05);
            padding: 1rem;
            border-radius: 0.5rem;
            overflow-x: auto;
        }}
        [data-theme="dark"] pre {{
            background: rgba(255,255,255,0.05);
        }}
    </style>
</head>
<body class="p-4 md:p-8">
    <nav class="fixed top-4 left-1/2 -translate-x-1/2 w-[90%] max-w-6xl glass-panel z-50 px-6 py-3 flex items-center justify-between">
        <div class="flex items-center gap-2">
            <span class="text-2xl">{'☯️' if self.theme == 'ink' else '🧪'}</span>
            <span class="font-bold text-xl tracking-tight">LCS 审计</span>
        </div>
        <div class="flex items-center gap-4 flex-1 max-w-md mx-8">
            <button id="themeToggle" class="p-2 rounded-full bg-white/50 border border-white/20">🌓</button>
            <div class="relative flex-1">
                <input type="text" id="searchBar" placeholder="搜索内容..." onkeyup="searchContent()"
                       class="w-full px-4 py-2 rounded-full border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white/50">
            </div>
        </div>
        <div class="hidden md:flex space-x-6 font-semibold">
            <a href="#overview" class="nav-link">概览</a>
            <a href="#conflicts" class="nav-link">冲突</a>
            <a href="#raw" class="nav-link">源内容</a>
        </div>
    </nav>

    <main class="max-w-6xl mx-auto mt-24 space-y-8">
        <section id="overview" class="glass-panel p-8 content-section">
            <h1 class="text-3xl font-bold mb-4">{self.title}</h1>
            <p class="opacity-70 text-sm">审计时间: {self.timestamp} | 模式: {self.theme.upper()}</p>
        </section>

        <section id="conflicts" class="glass-panel p-8 content-section">
            <h2 class="text-2xl font-bold mb-6">🔍 冲突审计报告</h2>
            <div class="space-y-4">
                {"".join([f'<div class="p-4 bg-red-50/50 border border-red-100 rounded-lg text-red-700 text-sm">{c}</div>' for c in (conflicts or ["未检测到冲突"])])}
            </div>
        </section>

        <section id="raw" class="glass-panel p-8 content-section">
            <h2 class="text-2xl font-bold mb-6">📄 源内容存档</h2>
            <div class="space-y-6">
                {"".join([f'<div class="p-6 bg-white/30 rounded-xl border border-white/20"><h3 class="font-bold mb-2">来源 {i+1}</h3><pre class="text-xs font-mono">{c[:2000]}...</pre></div>' for i, c in enumerate(content_list)])}
            </div>
        </section>
    </main>

    <script>
        // Theme Toggle
        const themeToggle = document.getElementById('themeToggle');
        themeToggle.addEventListener('click', () => {{
            const theme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('theme', theme);
        }});
        
        // Simple Search
        function searchContent() {{
            const q = document.getElementById('searchBar').value.toLowerCase();
            document.querySelectorAll('.content-section').forEach(s => {{
                s.style.display = s.innerText.toLowerCase().includes(q) ? 'block' : 'none';
            }});
        }}

        // Init theme
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
    </script>
</body>
</html>"""
        return html_template

# ==========================================
# MAIN
# ==========================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", help="One or more URLs or Local File Paths")
    parser.add_argument("--output", default="raw_content.txt", help="Path to write the raw content text file")
    parser.add_argument("--no-reports", action="store_true", help="Do not generate HTML/Feishu report side files")
    args = parser.parse_args()
    
    cp = ContentParser()
    detector = ConflictDetector()
    
    log(f"Starting ingestion for {len(args.inputs)} items...", style="cyan")
    
    output_path = os.path.abspath(args.output)
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    results_map = {}
    max_workers = os.cpu_count() or 4
    
    raw_contents = []
    conflicts = []
    
    if Progress:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=None, pulse_style="bright_blue"),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
            expand=True
        ) as progress:
            main_task = progress.add_task("[cyan]Overall Progress", total=len(args.inputs))
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_input = {}
                for i, inp in enumerate(args.inputs):
                    if os.path.exists(inp) and os.path.isfile(inp):
                        future_to_input[executor.submit(cp.process_file, inp)] = i
                    else:
                        if not inp.startswith(('http://', 'https://')):
                            if not inp.startswith('http'):
                                inp = 'https://' + inp
                        future_to_input[executor.submit(cp.process_url, inp)] = i
                
                for future in as_completed(future_to_input):
                    idx = future_to_input[future]
                    try:
                        res = future.result()
                        results_map[idx] = res
                        raw_contents.append(res)
                        log_success(f"Completed: {args.inputs[idx][:50]}...")
                    except Exception as e:
                        results_map[idx] = f"Error processing input {args.inputs[idx]}: {e}"
                        log_error(f"Failed: {args.inputs[idx][:50]}... Error: {e}")
                    progress.update(main_task, advance=1)
    else:
        # Fallback to tqdm or simple loop
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_input = {}
            for i, inp in enumerate(args.inputs):
                if os.path.exists(inp) and os.path.isfile(inp):
                    future_to_input[executor.submit(cp.process_file, inp)] = i
                else:
                    if not inp.startswith(('http://', 'https://')):
                        if not inp.startswith('http'):
                            inp = 'https://' + inp
                    future_to_input[executor.submit(cp.process_url, inp)] = i
            
            iterable = as_completed(future_to_input)
            if tqdm is not None:
                iterable = tqdm(iterable, total=len(args.inputs), desc="Ingesting Content")
                
            for future in iterable:
                idx = future_to_input[future]
                try:
                    res = future.result()
                    results_map[idx] = res
                    raw_contents.append(res)
                except Exception as e:
                    results_map[idx] = f"Error processing input {args.inputs[idx]}: {e}"
    
    # Run conflict detection if multi-source
    if len(raw_contents) > 1:
        conflicts = detector.detect_conflicts(raw_contents)
        if conflicts:
            log_warning(f"Detected {len(conflicts)} potential conflicts.")
            results_map[len(args.inputs)] = "\n=== MULTI-SOURCE CONFLICT REPORT ===\n" + "\n".join(conflicts)

    # Detect Theme (Heuristic)
    theme = "modern"
    combined_text = " ".join(raw_contents).lower()
    ink_keywords = ["guoxue", "国学", "易经", "taoism", "zen", "confucius", "buddhism", "中医", "古文", "classic"]
    if any(k in combined_text for k in ink_keywords) or any(k in " ".join(args.inputs).lower() for k in ink_keywords):
        theme = "ink"
        log(f"Detected Guoxue/Cultural content. Switching to 'Ink & Zen' theme.", "magenta")

    if not args.no_reports:
        rg = ReportGenerator(title="Multi-Source Knowledge Audit", theme=theme)
        html_report = rg.generate_html(raw_contents, conflicts)
        html_report_path = str(Path(output_path).with_suffix(".html"))
        Path(html_report_path).write_text(html_report, encoding="utf-8")
        log_success(f"HTML report ({theme}) saved to: {html_report_path}")

        fg = FeishuMarkdownGenerator(title="Multi-Source Knowledge Audit")
        feishu_md = fg.generate_md(raw_contents, conflicts)
        feishu_path = str(Path(output_path).with_suffix("")) + "_feishu.md"
        Path(feishu_path).write_text(feishu_md, encoding="utf-8")
        log_success(f"Feishu Markdown saved to: {feishu_path}")

    # Combine results
    final_output = ""
    for i in range(len(args.inputs)):
        source_url = args.inputs[i]
        content = results_map.get(i, "Error: Content missing")
        
        separator = f"\n\n" + "="*60 + "\n"
        separator += f"--- SOURCE {i+1}: {source_url} ---\n"
        separator += "="*60 + "\n\n"
        
        final_output += separator + content

    # Add conflict report if exists
    if len(args.inputs) in results_map:
        final_output += "\n\n" + "="*60 + "\n" + results_map[len(args.inputs)] + "\n" + "="*60
    
    # output_path = Config.get_output_path() # Moved to top
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_output)
        log_success(f"All content saved to: {output_path}")
        
        if console:
            console.print(Panel(f"[bold green]Ingestion Complete![/bold green]\nProcessed [cyan]{len(args.inputs)}[/cyan] sources.", title="Success", expand=False))
            
    except Exception as e:
        log_error(f"Failed to save output: {e}")

if __name__ == "__main__":
    main()
