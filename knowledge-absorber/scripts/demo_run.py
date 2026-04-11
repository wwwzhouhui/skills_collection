
import sys
import json
import shutil
from pathlib import Path

# Add scripts dir to path
sys.path.append(str(Path(__file__).parent))

from run_full_pipeline import resolve_pipeline_targets, run_command, SCRIPT_DIR, SKILL_DIR
from build_source_package import build_audit_report, read_text as read_raw_text
from truth_anchor import build_verification_report
from generate_knowledge_card import generate_outputs
from validate_knowledge_card import read_json

def main():
    target = "https://example.com/demo"
    print(f"--- DEMO RUN: Processing {target} ---")
    
    output_root = (SKILL_DIR / "outputs").resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    
    # 1. Ingestion (Skipped for demo)
    print("[1/5] Ingesting content... (Skipped)")
    work_dir = output_root / "demo_work_dir_ink"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir()
    
    raw_content_path = work_dir / "raw_content.txt"
    audit_report_path = work_dir / "raw_content.audit.json"
    verification_report_path = work_dir / "verification_report.json"
    
    raw_content_path.write_text("Mock content for Ink theme demo.", encoding="utf-8")
    
    # 2. Audit & Verification (Mocked)
    print("[2/5] Auditing & Verifying... (Mocked)")
    audit_report = {
        "source_meta": {"url": target, "title": "道德经与现代管理"},
        "topic_signature": ["道德经", "老子", "无为", "道家"] # Added to fix off_topic_truth_anchor
    }
    audit_report_path.write_text(json.dumps(audit_report, ensure_ascii=False, indent=2), encoding="utf-8")
    
    verification_report = {
        "summary": "基于通行本与帛书甲本校对。",
        "claims": [{"text": "道常无为而无不为。", "status": "confirmed"}] # Added to help validation
    }
    verification_report_path.write_text(json.dumps(verification_report, ensure_ascii=False, indent=2), encoding="utf-8")
    
    # 3. Model Generation (SIMULATED for Demo - Ink Theme Content)
    print("[3/5] Generating Card Data (Simulating LLM - Ink Theme)...")
    
    mock_data = {
        "header": {
            "title": "道德经：无为而无不为的智慧",
            "author": "叫我小杨同学的小码酱",
            "tags": ["国学", "道家", "管理哲学", "老子", "修身"],
            "source": "《道德经》通行本 / 帛书甲本",
            "audience_positioning": "面向被现代焦虑裹挟、试图在进退之间寻找平衡点的管理者与终身学习者。"
        },
        "module0": {
            "one_sentence": "“无为”不是躺平，而是顺应事物的自然规律去作为，从而达到“无不为”的高效境界。",
            "analogy": "就像冲浪：你不能强行改变海浪的方向（无为），但你可以顺着浪势站起来，滑得比谁都快（无不为）。",
            "truth_anchor": {
                "text": "道常无为而无不为。",
                "status": "confirmed",
                "note": "出自《道德经》第三十七章。核心在于“顺势”而非“不作为”。"
            }
        },
        "module1": {
            "mnemonic": "道生一，一生二，二生三，三生万物。",
            "story": "相传老子西出函谷关，被关令尹喜强留著书。老子在匆忙中写下五千言，不仅是为了交差，更是为了给乱世留下一颗“清醒的种子”。",
            "ascii_visual": "   道\n  /  \\\n 阴    阳\n  \\  /\n   万物"
        },
        "module2": {
            "core_mechanism": [
                "反者道之动：事物发展到极端必然走向反面（物极必反）。",
                "弱者道之用：柔弱胜刚强，保持低姿态才能汇聚能量。",
                "知足不辱：知道停止才不会陷入危险，这是生存的底线逻辑。",
                "治大国若烹小鲜：管理复杂系统不能随意折腾，要小心火候。"
            ],
            "system_position": [
                "上游：承接易经的阴阳辩证思想。",
                "下游：启发了法家（君人南面之术）与黄老之学，甚至影响了现代量子物理与自由放任经济学。"
            ],
            "evolution": [
                "老子（原始道家） -> 庄子（逍遥游） -> 黄老（汉初治国） -> 魏晋玄学 -> 全真道教",
                "从先秦的政治哲学，演变为汉初的治国工具，再到后世的宗教信仰与修身养性之学。" # Added 2nd item
            ],
            "why_design": [
                "为了在礼崩乐坏的春秋战国，提供一套不同于儒家“有为”的生存与救世方案。",
                "保护个体的生命能量，避免在无休止的争斗中内耗殆尽。"
            ],
            "mermaid": "graph TD\n    A[道：宇宙本源] --> B[德：道的显化]\n    B --> C{修身}\n    B --> D{治国}\n    C --> E[致虚极，守静笃]\n    D --> F[无为而治]\n    E --> G[归根复命]\n    F --> H[百姓自化]"
        },
        "module3": {
            "anti_intuition": "大家都以为“柔弱”是无能，老子却说“柔弱”是生机（草木之生也柔脆，其死也枯槁）。刚强反而离死亡更近。",
            "conflicts_or_version_diff": [
                "“大器晚成” vs “大器免成”：帛书版为“免成”，意为真正的大器不需要刻意雕琢，而是自然天成。",
                "“执大象，天下往”：是手持大象的象牙？还是把握大道的意象？通解为后者。"
            ],
            "search_internalized_tags": ["上善若水", "和光同尘", "少私寡欲", "功成身退"],
            "learner_takeaway": "不要只把《道德经》当玄学，试着把它当成一本“反脆弱”的高阶操作手册。"
        },
        "module4": {
            "getting_started": [
                "每天读一章（约100字），不要贪多，先读原文再看译文。",
                "观察生活中的“物极必反”现象（如过度营销导致反感）。",
                "练习“深呼吸”，体会“虚其心，实其腹”的身体感觉。"
            ],
            "pitfalls": [
                "误把“无为”当成懒惰的借口。",
                "陷入文字训诂的死胡同，忘了去体悟背后的“道”。",
                "强行用现代科学去解释古文，容易不伦不类。"
            ],
            "roi": [
                "投入：每天10分钟的冥想式阅读。",
                "收益：获得一种超然的视角，减少精神内耗，提升决策的从容度。"
            ]
        },
        "module5": {
            "faq": [
                {"question": "《道德经》是宗教经典吗？", "answer": "它是道教的经典，但本质上是一部哲学著作，任何人都可以读。"},
                {"question": "怎么理解“天地不仁”？", "answer": "不是说天地残忍，而是说天地对万物一视同仁，没有偏爱，这才是最大的公平。"},
                {"question": "年轻人读《道德经》会不会太消极？", "answer": "不会。它教你的是“后其身而身先”，通过退让来获得更大的进取空间，是高级的竞争策略。"},
                {"question": "最好的版本是哪个？", "answer": "陈鼓应的《老子今注今译》适合入门，中华书局的通行本适合诵读。"},
                {"question": "“道”到底是什么？", "answer": "道是不可言说的宇宙规律，是万物生成的总源头，也是万物运行的总动力。"},
                {"question": "如何做到“上善若水”？", "answer": "学习水的特性：滋润万物而不争名利，停留在众人不喜欢的低处，所以接近于道。"},
                {"question": "什么是“功成身退”？", "answer": "事情做成了，就要收敛锋芒或退出舞台，不要占着位置不放，否则会招来灾祸。"},
                {"question": "读不懂怎么办？", "answer": "读不懂是正常的。结合你的人生经历去读，当你栽跟头的时候，往往就读懂了。"}
            ],
            "review_entry": "闭上眼睛，想象自己是一滴水，顺流而下，遇到石头就绕开，遇到低洼就填满。这就是道。",
            "resources": [
                f"原始来源：{target}", # Added to match source
                "陈鼓应《老子今注今译》",
                "南怀瑾《老子他说》",
                "帛书老子甲乙本"
            ]
        },
        "coverage_trace": {
            "core_definition_and_value": True,
            "mechanism_and_runtime_logic": True,
            "system_position_and_collaboration": True,
            "history_and_version_changes": True,
            "scenarios_and_roi": True,
            "risks_misuse_and_boundaries": True
        },
        "meta": {
            "generation_mode": "model (simulated - ink)",
            "degraded_mode": False,
            "verification_summary": "国学经典内容模拟。"
        }
    }
    
    card_data_path = work_dir / "knowledge_card.data.json"
    card_data_path.write_text(json.dumps(mock_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Simulated model data saved.")
    
    # 4. Rendering
    print("[4/5] Rendering Outputs...")
    artifacts = generate_outputs(
        raw_path=raw_content_path,
        output_root=output_root,
        audit_report_path=audit_report_path,
        verification_report_path=verification_report_path,
        card_generation_mode="model",
        card_data_path=card_data_path,
    )
    
    print(f"DONE! Output generated at: {artifacts.output_dir}")
    print(f"Markdown: {artifacts.markdown_path}")
    print(f"HTML: {artifacts.source_html_path}")

    # 5. Interactive Packaging (Mentor Mode)
    print("[5/5] Packaging Interactive HTML (Mentor Mode)...")
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
    print(f"Interactive HTML: {interactive_path}")

if __name__ == "__main__":
    main()
