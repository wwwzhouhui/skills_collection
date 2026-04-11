from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


sys.dont_write_bytecode = True

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
LEARNING_HINTS = ("学习", "分析", "解析", "读懂", "解释", "知识卡", "存入知识库", "讲明白")
SUPPORTED_FILE_EXTENSIONS = {".pdf", ".doc", ".docx", ".md", ".markdown", ".txt", ".png", ".jpg", ".jpeg", ".webp", ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".cpp", ".c", ".go", ".rs", ".ipynb"}


sys.path.insert(0, str(SCRIPT_DIR))
from build_source_package import build_audit_report, read_text as read_raw_text  # noqa: E402
from generate_knowledge_card import generate_outputs  # noqa: E402
from system_prompt_contract import load_contract  # noqa: E402
from truth_anchor import build_verification_report  # noqa: E402
from validate_knowledge_card import read_json, read_text, validate_card_payload, validate_interactive_html_text, validate_source_html_text  # noqa: E402
import openai_compatible_client  # noqa: E402
from system_prompt_contract import load_prompt_text  # noqa: E402

BASE_USAGE = '%(prog)s "<链接或本地文件路径>" ["<更多链接或文件路径>"]'
DEFAULT_OUTPUT_NOTE = "默认输出：knowledge_card.md + knowledge_card.interactive.html（仅保留这 2 个文件）\n可选：--poster 生成 Wan 2.7 知识海报 prompt"


def run_command(command: list[str], debug: bool = False) -> None:
    if debug:
        subprocess.run(command, cwd=str(SKILL_DIR), check=True)
        return
    completed = subprocess.run(
        command,
        cwd=str(SKILL_DIR),
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return
    if completed.stdout:
        print(completed.stdout, end="", file=sys.stderr)
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    raise subprocess.CalledProcessError(
        completed.returncode,
        command,
        output=completed.stdout,
        stderr=completed.stderr,
    )


def normalize_segments(raw_inputs: list[str]) -> list[str]:
    if len(raw_inputs) == 1:
        candidate = raw_inputs[0].strip()
        if candidate.startswith("[") and candidate.endswith("]"):
            try:
                parsed = ast.literal_eval(candidate)
            except (ValueError, SyntaxError):
                pass
            else:
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
    return raw_inputs


def strip_wrapping_punctuation(value: str) -> str:
    return value.strip().strip("'\"[](),")


def extract_urls(text: str) -> list[str]:
    matches = re.findall(r"https?://[^\s\]>'\")]+", text, flags=re.IGNORECASE)
    cleaned = []
    for item in matches:
        normalized = item.rstrip(".,;)")
        if normalized not in cleaned:
            cleaned.append(normalized)
    return cleaned


def token_candidates(text: str) -> list[str]:
    pieces = re.split(r"[\s\n\r\t]+", text)
    return [strip_wrapping_punctuation(piece) for piece in pieces if strip_wrapping_punctuation(piece)]


def resolve_existing_path(token: str) -> Path | None:
    candidate = Path(token)
    search_roots = [Path.cwd(), SKILL_DIR.parent, SKILL_DIR]
    path_variants = [candidate]
    if not candidate.is_absolute():
        path_variants.extend(root / candidate for root in search_roots)
    for variant in path_variants:
        if variant.exists() and variant.is_file():
            return variant.resolve()
    return None


def extract_file_targets(segments: list[str]) -> list[str]:
    results: list[str] = []
    seen = set()
    for segment in segments:
        for token in token_candidates(segment):
            path = resolve_existing_path(token)
            if path is None:
                continue
            if path.suffix.lower() not in SUPPORTED_FILE_EXTENSIONS and path.suffix:
                continue
            resolved = str(path)
            if resolved in seen:
                continue
            seen.add(resolved)
            results.append(resolved)
    return results


def has_learning_signal(segments: list[str]) -> bool:
    return any(hint in " ".join(segments) for hint in LEARNING_HINTS)


def resolve_pipeline_targets(raw_inputs: list[str]) -> list[str]:
    segments = normalize_segments(raw_inputs)
    joined = " ".join(segments)
    urls = extract_urls(joined)
    files = extract_file_targets(segments)
    targets: list[str] = []
    for item in [*urls, *files]:
        if item not in targets:
            targets.append(item)
    if targets:
        return targets
    direct_inputs = []
    for segment in segments:
        cleaned = strip_wrapping_punctuation(segment)
        if cleaned.startswith(("http://", "https://")):
            direct_inputs.append(cleaned)
            continue
        path = resolve_existing_path(cleaned)
        if path is not None:
            direct_inputs.append(str(path))
    if direct_inputs:
        return direct_inputs
    if has_learning_signal(segments):
        raise ValueError("检测到学习型请求，但没有提取到可执行对象。请确认输入里包含 URL、文件路径、文档或代码文件。")
    raise ValueError("没有识别到可处理的 URL 或文件。请提供学习型请求，并带上链接、文件路径或附件对象。")


def generate_card_data_with_model(
    raw_content_path: Path,
    audit_report_path: Path,
    verification_report_path: Path,
    output_path: Path,
) -> None:
    """
    Calls the configured LLM to generate the knowledge card JSON data.
    """
    connection = openai_compatible_client.load_env_connection()
    if not connection:
        # Check for profile
        profile_path = SKILL_DIR / "config" / "profile.json" # Assuming standard location, though user might not have it
        connection = openai_compatible_client.load_profile_connection(profile_path)
    
    if not connection:
        print("Warning: No LLM configuration found (KA_BASE_URL/KA_API_KEY or profile.json).", file=sys.stderr)
        print("Falling back to local rule-based generation (Degraded Mode).", file=sys.stderr)
        return

    print(f"Generating knowledge card data using model: {connection['model']}...", file=sys.stderr)

    system_prompt = load_prompt_text()
    
    # Construct user prompt with context
    audit_report = read_json(audit_report_path)
    verification_report = read_json(verification_report_path)
    
    # We use the audit report as the primary source for the model as it is structured
    # but raw content might be needed for full context. 
    # Let's use a combination.
    
    user_prompt = f"""
请基于以下“内容审计报告”和“验证报告”，生成一份符合 System Prompt 定义的 Knowledge Card 数据 JSON。

**注意：**
1. 必须输出纯 JSON 格式，不要包含 Markdown 代码块标记（如 ```json ... ```）。
2. 严格遵守 System Prompt 中的 Schema 定义。
3. 必须覆盖所有 Mandatory 字段。

---
【内容审计报告 (Audit Report)】
{json.dumps(audit_report, ensure_ascii=False, indent=2)}

---
【验证报告 (Verification Report)】
{json.dumps(verification_report, ensure_ascii=False, indent=2)}
"""

    try:
        response_text = openai_compatible_client.chat_text(
            connection=connection,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3, # Slightly creative but structured
            max_tokens=4000,
            timeout_seconds=180
        )
    except Exception as e:
        print(f"Error calling LLM: {e}", file=sys.stderr)
        print("Model generation failed. Local rules are disabled by user request.", file=sys.stderr)
        sys.exit(1)

    # Clean up response (remove potential markdown fences)
    cleaned_json = response_text.strip()
    if cleaned_json.startswith("```json"):
        cleaned_json = cleaned_json[7:]
    if cleaned_json.startswith("```"):
        cleaned_json = cleaned_json[3:]
    if cleaned_json.endswith("```"):
        cleaned_json = cleaned_json[:-3]
    cleaned_json = cleaned_json.strip()

    try:
        # Validate JSON syntax
        data = json.loads(cleaned_json)
        # We could validat schema here, but generate_outputs will do it.
        output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Model generated data saved to: {output_path}", file=sys.stderr)
    except json.JSONDecodeError as e:
        print(f"Error parsing model output as JSON: {e}", file=sys.stderr)
        print(f"Raw output start: {cleaned_json[:500]}...", file=sys.stderr)
        sys.exit(1)


def validate_source_stage(data_path: Path, source_html_path: Path, verification_report_path: Path, audit_report_path: Path) -> None:
    contract = load_contract()
    data = read_json(data_path)
    verification_report = read_json(verification_report_path)
    audit_report = read_json(audit_report_path)
    errors = validate_card_payload(data, contract, audit_report=audit_report, verification_report=verification_report)
    errors.extend(validate_source_html_text(read_text(source_html_path), data, contract, verification_report, audit_report))
    if errors:
        raise ValueError("Source validation failed: " + " | ".join(errors))


def validate_interactive_stage(data_path: Path, source_html_path: Path, interactive_path: Path, verification_report_path: Path, audit_report_path: Path) -> None:
    contract = load_contract()
    data = read_json(data_path)
    verification_report = read_json(verification_report_path)
    audit_report = read_json(audit_report_path)
    errors = validate_card_payload(data, contract, audit_report=audit_report, verification_report=verification_report)
    errors.extend(validate_source_html_text(read_text(source_html_path), data, contract, verification_report, audit_report))
    errors.extend(validate_interactive_html_text(read_text(interactive_path), contract))
    if errors:
        raise ValueError("Interactive validation failed: " + " | ".join(errors))


def cleanup_output_dir(output_dir: Path, keep_names: set[str]) -> None:
    for child in output_dir.iterdir():
        if child.is_file():
            if child.name not in keep_names:
                child.unlink(missing_ok=True)
            continue
        shutil.rmtree(child, ignore_errors=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "把链接、文档、图片或代码整理成学习成品。\n"
            f"{DEFAULT_OUTPUT_NOTE}"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
        usage=BASE_USAGE,
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        metavar="target",
        help="一个或多个链接/本地文件路径；也支持包含链接或路径的自然语言学习请求。",
    )
    parser.add_argument(
        "--poster",
        action="store_true",
        help="生成 Wan 2.7 知识海报 prompt（需要 DASHSCOPE_API_KEY）",
    )
    parser.add_argument(
        "--style",
        default="",
        help="海报风格编号 (1-11)，默认自动检测：国学内容用水墨风格，其他用孟菲斯网格",
    )
    parser.add_argument(
        "--audience",
        default="零基础学习者",
        help="目标读者，默认：零基础学习者",
    )
    parser.add_argument(
        "--size",
        default="2K",
        help="海报分辨率，默认：2K",
    )
    parser.add_argument(
        "--ratio",
        default="3:4",
        help="海报比例，默认：3:4",
    )
    return parser.parse_args()


def print_success_summary(
    resolved_targets: list[str],
    markdown_path: Path,
    interactive_path: Path,
    poster_prompt_path: Path | None = None,
) -> None:
    print("Resolved targets:")
    for target in resolved_targets:
        print(f"- {target}")
    print(f"Output Markdown: {markdown_path}")
    print(f"Output HTML: {interactive_path}")
    if poster_prompt_path:
        print(f"Poster Prompt: {poster_prompt_path}")


def main() -> int:
    args = parse_args()
    output_root = (SKILL_DIR / "outputs").resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    resolved_targets = resolve_pipeline_targets(args.inputs)

    with tempfile.TemporaryDirectory(prefix="ka_work_", dir=str(output_root)) as work_dir:
        work_path = Path(work_dir)
        raw_content_path = work_path / "raw_content.txt"
        audit_report_path = work_path / "raw_content.audit.json"
        verification_report_path = work_path / "verification_report.json"

        run_command(
            [
                sys.executable,
                str(SCRIPT_DIR / "content_ingester.py"),
                "--output",
                str(raw_content_path),
                "--no-reports",
                *resolved_targets,
            ],
            debug=False,
        )
        if not raw_content_path.exists():
            raise FileNotFoundError(f"Expected raw content was not generated: {raw_content_path}")

        audit_report = build_audit_report(read_raw_text(raw_content_path))
        audit_report_path.write_text(json.dumps(audit_report, ensure_ascii=False, indent=2), encoding="utf-8")
        verification_report = build_verification_report(audit_report)
        verification_report_path.write_text(json.dumps(verification_report, ensure_ascii=False, indent=2), encoding="utf-8")

        # [LCS-MOD] Try Model Generation First (User Request: No Local Rules)
        card_data_path = work_path / "knowledge_card.data.json"
        
        # Check if we have a key before trying, to avoid the error inside the function (though we patched it to return)
        # Actually, the function now returns None if no key.
        # We need to know if it succeeded.
        
        try:
            generate_card_data_with_model(
                raw_content_path=raw_content_path,
                audit_report_path=audit_report_path,
                verification_report_path=verification_report_path,
                output_path=card_data_path
            )
        except Exception as e:
            print(f"Model generation failed: {e}. Falling back to rules.", file=sys.stderr)
        
        mode = "model" if card_data_path.exists() else "rule"
        final_card_path = card_data_path if card_data_path.exists() else None

        artifacts = generate_outputs(
            raw_path=raw_content_path,
            output_root=output_root,
            audit_report_path=audit_report_path,
            verification_report_path=verification_report_path,
            card_generation_mode=mode, 
            card_data_path=final_card_path,
        )

        validate_source_stage(artifacts.data_path, artifacts.source_html_path, verification_report_path, audit_report_path)

        interactive_path = artifacts.source_html_path.with_name("knowledge_card.interactive.html")
        run_command(
            [
                sys.executable,
                str(SCRIPT_DIR / "package_interactive_html.py"),
                "--input-html",
                str(artifacts.source_html_path),
                "--raw-content",
                str(raw_content_path),
                "--output",
                str(interactive_path),
                "--mode",
                "manual",
            ],
            debug=False,
        )

        validate_interactive_stage(
            artifacts.data_path,
            artifacts.source_html_path,
            interactive_path,
            verification_report_path,
            audit_report_path,
        )

        # Generate poster prompt if requested
        poster_prompt_path = None
        if args.poster:
            try:
                poster_output_dir = output_root / "wan_prompt.txt"
                poster_command = [
                    sys.executable,
                    str(SCRIPT_DIR / "build_knowledge_poster_assets.py"),
                    "--input", str(artifacts.markdown_path),
                    "--prompt-output", str(poster_output_dir),
                    "--audience", args.audience,
                    "--style", args.style,
                    "--size", args.size,
                    "--ratio", args.ratio,
                ]
                run_command(poster_command, debug=False)
                if poster_output_dir.exists():
                    poster_prompt_path = poster_output_dir
                    print(f"\n🎨 海报 Prompt 已生成: {poster_output_dir}")
                    print("💡 回复'确认生图'后调用 Wan 2.7 生成海报")
            except Exception as e:
                print(f"海报 Prompt 生成失败: {e}", file=sys.stderr)

        keep_names = {artifacts.markdown_path.name, interactive_path.name}
        if poster_prompt_path:
            keep_names.add(poster_prompt_path.name)
        cleanup_output_dir(artifacts.output_dir, keep_names)

        print_success_summary(
            resolved_targets=resolved_targets,
            markdown_path=artifacts.markdown_path,
            interactive_path=interactive_path,
            poster_prompt_path=poster_prompt_path,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
