#!/usr/bin/env python3
"""Stop: enforce the video editing file contract when a run has started."""
from __future__ import annotations

import json
import hashlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hook_common import read_stdin_json, project_dir, plugin_root, sanitize_scope, strike, clear_strike, block_stop, allow, state_dir  # noqa: E402

RULE = "video_closeout"


def asr_provider_available() -> bool:
    """True when cloud ASR is usable; the contract then treats
    out/transcript.json as a required artifact."""
    try:
        sys.path.insert(0, str(plugin_root() / "mcp"))
        from ve_tools.speech_service import cloud_asr_available

        return cloud_asr_available()
    except Exception:
        return False


def read_status(path: Path) -> str:
    data = read_json(path)
    return str(data.get("status") or "") if data else ""


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def read_json_list(path: Path) -> list:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return value if isinstance(value, list) else []


def _sha_cache_path() -> Path:
    return state_dir() / "sha_cache.json"


def _load_sha_cache() -> dict:
    try:
        return json.loads(_sha_cache_path().read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_sha_cache(cache: dict) -> None:
    try:
        _sha_cache_path().write_text(json.dumps(cache), encoding="utf-8")
    except Exception:
        pass


def file_sha256(path: Path) -> str | None:
    """SHA-256 of a file, disk-cached by (size, mtime_ns).

    The Stop hook runs on every turn end; without caching it re-hashes every
    multi-GB output (preview/final/condensed) each time, blowing the 15s hook
    timeout on network mounts so the closeout contract silently stops being
    enforced. The cache key includes size+mtime, so any real change (re-render)
    invalidates it and forces a recompute. Returns None on any read failure so
    the caller never crashes on a TOCTOU delete or permission error."""
    try:
        st = path.stat()
    except OSError:
        return None
    key = str(path)
    cache = _load_sha_cache()
    entry = cache.get(key)
    if isinstance(entry, dict) and entry.get("size") == st.st_size and entry.get("mtime") == st.st_mtime_ns:
        sha = entry.get("sha")
        if isinstance(sha, str):
            return sha
    h = hashlib.sha256()
    try:
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
    except OSError:
        return None
    digest = h.hexdigest()
    cache[key] = {"size": st.st_size, "mtime": st.st_mtime_ns, "sha": digest}
    _save_sha_cache(cache)
    return digest


def source_media_probe_exists(out: Path) -> bool:
    """out/ 下是否有对源素材的 inspect_media 探针。qc_preview 和 finish_tts
    自己也会写 *_media.json 副产物 (preview_media.json / *_preview_media.json /
    tts_*_media.json) — 不排除它们的话, 跑过一次 QC 这条门禁就恒真。"""
    for p in out.glob("*media.json"):
        name = p.name
        if name == "preview_media.json" or name.endswith("_preview_media.json"):
            continue
        if name.startswith("tts_") and name.endswith("_media.json"):
            continue
        return True
    return False


def report_mentions_transcript(report: Path) -> bool:
    """gap 文案承诺的逃生门: report.md 里解释过转录缺失即放行。宽判 —
    提到 transcript/转录 即视为已记录 (自动化场景不做语义判断)。"""
    try:
        text = report.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return "transcript" in text.lower() or "转录" in text


def transcript_artifact_exists(out: Path) -> bool:
    return any(path.is_file() for path in out.rglob("*transcript*.json"))


def source_video_ingest_exists(out: Path) -> bool:
    """Accept multi-source observation packages, not only out/video_ingest.json.

    Preview self-review packages intentionally do not satisfy the source
    material contract.
    """
    if (out / "video_ingest.json").is_file():
        return True
    candidates = [
        *out.glob("video_ingest_*.json"),
        *out.glob("ingest/*.json"),
        *out.glob("video_ingest/*.json"),
    ]
    for path in candidates:
        name = path.name.lower()
        rel = path.relative_to(out).as_posix().lower()
        if "preview" in name or "preview" in rel:
            continue
        if path.is_file():
            return True
    return False


def nonempty_file(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def base_media_transcript_gaps(out: Path, report: Path) -> list[str]:
    gaps: list[str] = []
    media = out / "media.json"
    transcript = out / "transcript.json"
    if not media.is_file() and not source_media_probe_exists(out):
        gaps.append("out/media.json missing; run inspect_media on the source media.")
    if (
        not transcript.is_file()
        and not transcript_artifact_exists(out)
        and asr_provider_available()
        and not report_mentions_transcript(report)
    ):
        gaps.append(
            "out/transcript.json missing while an ASR provider is available; "
            "run transcribe on the source media (standard flow), or record in out/report.md why it is impossible."
        )
    return gaps


def subtitle_pipeline_started(out: Path) -> bool:
    names = [
        "transcript_edits.md",
        "subtitle_scout.json",
        "subtitle_plan.md",
        "subtitles.json",
        "subtitled.mp4",
        "subtitle_qc_report.json",
        "subtitle_verify.md",
    ]
    return any((out / name).exists() for name in names)


def subtitle_visual_evidence_exists(out: Path) -> bool:
    return (out / "subtitle_scout.json").is_file() or source_video_ingest_exists(out)


def subtitle_gaps(out: Path, report: Path) -> list[str]:
    gaps = base_media_transcript_gaps(out, report)
    if not transcript_artifact_exists(out) and not any("transcript" in gap.lower() or "转录" in gap for gap in gaps):
        gaps.append("out/transcript.json missing; subtitle workflows require a timed transcript.")
    transcript_edits = out / "transcript_edits.md"
    scout = out / "subtitle_scout.json"
    plan = out / "subtitle_plan.md"
    subtitles = out / "subtitles.json"
    subtitled = out / "subtitled.mp4"
    qc = out / "subtitle_qc_report.json"
    verify = out / "subtitle_verify.md"

    if not nonempty_file(transcript_edits):
        gaps.append("out/transcript_edits.md missing or empty; record ASR corrections or explicitly say none were needed.")
    if not subtitle_visual_evidence_exists(out):
        gaps.append("subtitle visual evidence missing; run subtitle_scout or video_ingest before choosing placement/style.")
    elif scout.is_file():
        scout_data = read_json(scout)
        if not scout_data.get("images"):
            gaps.append("out/subtitle_scout.json has no image evidence; rerun subtitle_scout.")
    if not nonempty_file(plan):
        gaps.append("out/subtitle_plan.md missing or empty; record style, safe area, and F/T checkpoints.")
    if not subtitles.is_file():
        gaps.append("out/subtitles.json missing; run subtitle_build.")
    if not nonempty_file(subtitled):
        gaps.append("out/subtitled.mp4 missing or empty; run subtitle_render.")
    if not qc.is_file():
        gaps.append("out/subtitle_qc_report.json missing; run subtitle_qc on the rendered subtitle output.")
    elif read_status(qc) != "pass":
        gaps.append("out/subtitle_qc_report.json status is not pass.")
    else:
        qc_data = read_json(qc)
        if subtitles.is_file() and qc_data.get("subtitles_sha256") != file_sha256(subtitles):
            gaps.append("out/subtitle_qc_report.json is stale; rerun subtitle_qc after the latest subtitles.json edit.")
        if subtitled.is_file() and qc_data.get("video_sha256") != file_sha256(subtitled):
            gaps.append("out/subtitle_qc_report.json is stale; rerun subtitle_qc after the latest subtitled render.")
    if not nonempty_file(verify):
        gaps.append("out/subtitle_verify.md missing or empty; append checkpoint verdicts after reading QC frames/windows.")
    return gaps


def condense_pipeline_started(out: Path) -> bool:
    names = [
        "speech_index.json",
        "speech_index.md",
        "condense_brief.md",
        "condense_plan.json",
        "condense_script.md",
        "condensed_transcript.json",
        "condensed.mp4",
        "condense_qc_report.json",
        "condense_verify.md",
    ]
    return any((out / name).exists() for name in names)


def condense_gaps(out: Path, report: Path) -> list[str]:
    gaps = base_media_transcript_gaps(out, report)
    if not transcript_artifact_exists(out) and not any("transcript" in gap.lower() or "转录" in gap for gap in gaps):
        gaps.append("out/transcript.json missing; speech-condense requires a timed transcript.")
    speech_index = out / "speech_index.json"
    speech_table = out / "speech_index.md"
    brief = out / "condense_brief.md"
    plan = out / "condense_plan.json"
    script = out / "condense_script.md"
    condensed_transcript = out / "condensed_transcript.json"
    condensed = out / "condensed.mp4"
    qc = out / "condense_qc_report.json"
    verify = out / "condense_verify.md"

    if not speech_index.is_file():
        gaps.append("out/speech_index.json missing; run condense_index.")
    else:
        index_data = read_json(speech_index)
        survey = index_data.get("visual_survey")
        if not isinstance(survey, dict) or not survey.get("performed"):
            gaps.append("out/speech_index.json has no performed visual survey; rerun condense_index with visual_survey enabled.")
    if not nonempty_file(speech_table):
        gaps.append("out/speech_index.md missing or empty; condense_index should write the full unit table.")
    if not nonempty_file(brief):
        gaps.append("out/condense_brief.md missing or empty; record target, keep strategy, and checkpoints.")
    if not plan.is_file():
        gaps.append("out/condense_plan.json missing; run condense_plan.")
    else:
        plan_data = read_json(plan)
        if plan_data.get("status") != "ok":
            gaps.append("out/condense_plan.json status is not ok.")
        if speech_index.is_file() and plan_data.get("index_sha256") != file_sha256(speech_index):
            gaps.append("out/condense_plan.json references an older speech index; rerun condense_plan.")
    if not nonempty_file(script):
        gaps.append("out/condense_script.md missing or empty; rerun condense_plan and read the script before render.")
    if not condensed_transcript.is_file():
        gaps.append("out/condensed_transcript.json missing; rerun condense_plan so later subtitle timing can be remapped.")
    if not nonempty_file(condensed):
        gaps.append("out/condensed.mp4 missing or empty; run condense_render.")
    if not qc.is_file():
        gaps.append("out/condense_qc_report.json missing; run condense_qc on out/condensed.mp4.")
    elif read_status(qc) != "pass":
        gaps.append("out/condense_qc_report.json status is not pass.")
    else:
        qc_data = read_json(qc)
        if plan.is_file() and qc_data.get("plan_sha256") != file_sha256(plan):
            gaps.append("out/condense_qc_report.json is stale; rerun condense_qc after the latest condense_plan.json.")
        if condensed.is_file() and qc_data.get("video_sha256") != file_sha256(condensed):
            gaps.append("out/condense_qc_report.json is stale; rerun condense_qc after the latest condensed render.")
    if not nonempty_file(verify):
        gaps.append("out/condense_verify.md missing or empty; append checkpoint verdicts after reading QC evidence.")
    return gaps


def recap_pipeline_started(out: Path) -> bool:
    names = [
        "reel.json",
        "edl.json",
        "edl_qc.json",
        "final.mp4",
        "qc.json",
        "placement.json",
        "coverage_report.txt",
    ]
    return any((out / name).exists() for name in names)


def qc_passed(path: Path) -> bool:
    data = read_json(path)
    status = str(data.get("status") or "").lower()
    if status in {"pass", "passed", "ok"}:
        return True
    return data.get("pass") is True


def final_qc_reports(out: Path) -> list[Path]:
    paths = [out / "final_qc_report.json", *out.glob("final*_qc_report.json")]
    unique: dict[str, Path] = {}
    for path in paths:
        if path.is_file():
            unique[str(path)] = path
    return sorted(unique.values(), key=lambda p: p.stat().st_mtime)


def report_mentions_spot_review(report: Path) -> bool:
    try:
        text = report.read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return False
    return "spot_review" in text or "spot review" in text or "抽查" in text


def recap_gaps(out: Path, report: Path) -> list[str]:
    gaps: list[str] = []
    movie_like = any(
        (out / name).exists()
        for name in ("edl.json", "edl_qc.json", "narration_script.json", "graph.json", "dialogue_axis.txt")
    )
    sports_like = any(
        (out / name).exists()
        for name in ("match.json", "commentary_axis.txt", "qc.json", "placement.json", "coverage_report.txt")
    )

    if movie_like:
        gaps.extend(base_media_transcript_gaps(out, report))
        for name in ("shots.json", "dialogue_axis.txt", "dialogue_index.json", "outline.json", "reel.json", "writer_script.json", "narration_script.json", "script_tts.json", "edl.json"):
            if not nonempty_file(out / name):
                gaps.append(f"out/{name} missing or empty; finish the movie-recap pipeline before stopping.")
        edl_qc = out / "edl_qc.json"
        if not edl_qc.is_file():
            gaps.append("out/edl_qc.json missing; run bind_narration and keep its QC report.")
        elif read_status(edl_qc) not in {"pass", "passed"}:
            gaps.append("out/edl_qc.json status is not passed.")
        script_tts = read_json_list(out / "script_tts.json")
        failed = [
            str(item.get("seg_id") or "?")
            for item in script_tts
            if isinstance(item, dict) and (item.get("verify") or {}).get("status") == "fail"
        ]
        if failed:
            gaps.append(
                "out/script_tts.json has verify=fail segments ("
                + ", ".join(failed[:6])
                + "); rewrite those sentences and rerun TTS before rendering."
            )

    if sports_like:
        for name in ("match.json", "outline.json", "writer_script.json", "script_tts.json", "reel.json"):
            if not nonempty_file(out / name):
                gaps.append(f"out/{name} missing or empty; finish the sports recap pipeline before stopping.")
        if not transcript_artifact_exists(out):
            gaps.append("recap transcript artifacts missing; transcribe the full source game/match before arranging.")
        if not ((out / "commentary_axis.txt").is_file() or (out / "commentary_index.json").is_file()):
            gaps.append("out/commentary_axis.txt or out/commentary_index.json missing; build the commentary axis before writing the recap.")
        qc = out / "qc.json"
        if not qc.is_file():
            gaps.append("out/qc.json missing; run the recap render tool and keep its QC report.")
        elif not qc_passed(qc):
            gaps.append("out/qc.json did not pass.")

    finals = sorted(
        (path for path in out.glob("final*.mp4") if path.is_file() and path.stat().st_size > 0),
        key=lambda p: p.stat().st_mtime,
    )
    if not finals:
        gaps.append("out/final*.mp4 missing or empty; render the recap final video.")
    elif movie_like:
        newest = finals[-1]
        reports = [path for path in final_qc_reports(out) if qc_passed(path)]
        if not reports:
            gaps.append(f"no passing final*_qc_report.json; run qc_preview on {newest.name}.")
        elif not any(read_json(path).get("video_sha256") == file_sha256(newest) for path in reports):
            gaps.append(f"final QC report is stale; rerun qc_preview on {newest.name}.")

    if not nonempty_file(out / "spot_review.json") and not report_mentions_spot_review(report):
        gaps.append("out/spot_review.json missing; spot-check recap sentence/video alignment or record the spot-review results in out/report.md.")
    return gaps


def main() -> None:
    data = read_stdin_json()
    session = sanitize_scope(str(data.get("session_id") or "default"))
    # Escape hatch: an environment that cannot satisfy the contract (missing
    # cv2/ffmpeg, read-only project, CI) can opt out rather than eat two blocked
    # stops per three attempts on gates it can never clear.
    if os.environ.get("VE_CLOSEOUT_DISABLE") or (project_dir() / ".video_agent" / "closeout_off").is_file():
        allow()
    out = project_dir() / "out"
    media = out / "media.json"
    transcript = out / "transcript.json"
    video_ingest = out / "video_ingest.json"
    timeline = out / "timeline.json"
    validation = out / "timeline_validation.json"
    preview = out / "preview.mp4"
    render_report = out / "preview.render_report.json"
    render_plan = out / "preview.render_plan.json"
    edit_decisions = out / "preview.edit_decisions.json"
    qc = out / "preview_qc_report.json"
    report = out / "report.md"

    # Only enforce the full contract once the editing pipeline itself has
    # produced artifacts. Single-step tasks (inspect_media, transcribe,
    # video_ingest-only understanding) must be able to stop freely.
    timeline_started = any(path.exists() for path in (timeline, validation, preview, qc))
    subtitle_started = subtitle_pipeline_started(out)
    condense_started = condense_pipeline_started(out)
    recap_started = recap_pipeline_started(out)
    started = timeline_started or subtitle_started or condense_started or recap_started
    if not started:
        allow()

    gaps: list[str] = []
    if timeline_started:
        gaps.extend(base_media_transcript_gaps(out, report))
        if not source_video_ingest_exists(out):
            gaps.append(
                "source video_ingest observation missing; inspect the source video(s) before editing. "
                "For multi-source tasks, out/ingest/*.json or out/video_ingest_<source>.json is acceptable."
            )
        if not timeline.is_file():
            gaps.append("out/timeline.json missing.")
        if not validation.is_file():
            gaps.append("out/timeline_validation.json missing; run validate_timeline on out/timeline.json.")
        elif read_status(validation) != "pass":
            gaps.append("out/timeline_validation.json status is not pass.")
        else:
            validation_data = read_json(validation)
            project_contract = validation_data.get("project_contract")
            if not isinstance(project_contract, dict) or not project_contract.get("ok"):
                gaps.append(
                    "out/timeline.json is not a project-style timeline; include project, assets[], "
                    "sequence or output_canvas, tracks[], and at least one video/main track, then rerun validate_timeline."
                )
            if timeline.is_file() and validation_data.get("timeline_sha256") != file_sha256(timeline):
                gaps.append("out/timeline_validation.json is stale; rerun validate_timeline after the latest timeline edit.")
        if not preview.is_file() or preview.stat().st_size == 0:
            gaps.append("out/preview.mp4 missing or empty; run render_preview.")
        if not render_report.is_file():
            gaps.append("out/preview.render_report.json missing; rerun render_preview.")
        else:
            render_data = read_json(render_report)
            if preview.is_file() and render_data.get("output_sha256") != file_sha256(preview):
                gaps.append("out/preview.render_report.json is stale; rerun render_preview.")
            if timeline.is_file() and render_data.get("timeline_sha256") != file_sha256(timeline):
                gaps.append("out/preview.render_report.json references an older timeline; rerun render_preview.")
        if not render_plan.is_file():
            gaps.append("out/preview.render_plan.json missing; rerun render_preview.")
        else:
            plan_data = read_json(render_plan)
            if timeline.is_file() and plan_data.get("timeline_sha256") != file_sha256(timeline):
                gaps.append("out/preview.render_plan.json references an older timeline; rerun render_preview.")
        if not edit_decisions.is_file():
            gaps.append("out/preview.edit_decisions.json missing; rerun render_preview.")
        else:
            decisions_data = read_json(edit_decisions)
            if timeline.is_file() and decisions_data.get("timeline_sha256") != file_sha256(timeline):
                gaps.append("out/preview.edit_decisions.json references an older timeline; rerun render_preview.")
        if not qc.is_file():
            gaps.append("out/preview_qc_report.json missing; run qc_preview on out/preview.mp4.")
        elif read_status(qc) != "pass":
            gaps.append("out/preview_qc_report.json status is not pass.")
        else:
            qc_data = read_json(qc)
            if preview.is_file() and qc_data.get("video_sha256") != file_sha256(preview):
                gaps.append("out/preview_qc_report.json is stale; rerun qc_preview after the latest preview render.")
            if timeline.is_file():
                if not qc_data.get("timeline_sha256"):
                    gaps.append("out/preview_qc_report.json does not record the timeline hash; rerun qc_preview with timeline_path.")
                elif qc_data.get("timeline_sha256") != file_sha256(timeline):
                    gaps.append("out/preview_qc_report.json references an older timeline; rerun qc_preview with timeline_path.")
    if subtitle_started:
        gaps.extend(subtitle_gaps(out, report))
    if condense_started:
        gaps.extend(condense_gaps(out, report))
    if recap_started:
        gaps.extend(recap_gaps(out, report))
    if not report.is_file():
        gaps.append("out/report.md missing; write the final assumptions, outputs, QC status, and risks.")
    elif report.stat().st_size == 0:
        gaps.append("out/report.md is empty; write the final assumptions, outputs, QC status, and risks.")

    if not gaps:
        clear_strike(RULE, scope=session)
        allow()

    # Strikes are session-scoped and bound the block loop: after `limit`
    # consecutive blocked stops the hook releases, so ignoring
    # stop_hook_active here cannot loop forever.
    count, released = strike(RULE, scope=session)
    if released:
        allow()
    block_stop(
        "Video editing contract is not closed:\n- "
        + "\n- ".join(gaps)
        + f"\nFinish the missing file-backed steps before stopping. (strike {count}/3)"
    )


if __name__ == "__main__":
    main()
