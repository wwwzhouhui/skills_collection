import json
from pathlib import Path
import argparse

from validator import validate_input
from parser import parse_content
from router import route_scene, route_task_type
from prompt_builder import build_prompt
from wan_client import (
    load_config,
    call_wan_image_api,
    call_wan_text_to_video_api,
    call_wan_i2v_api,
    call_wan_r2v_api,
)
from postprocess import format_result, should_postprocess_video, run_video_postprocess


def _output_suffix(task_type: str) -> str:
    return ".png" if task_type == "image" else ".mp4"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to input json")
    args = ap.parse_args()

    skill_dir = Path(__file__).resolve().parent.parent
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    skill_input = validate_input(data)
    parsed = parse_content(skill_input)
    scene = route_scene(skill_input)
    task_type = route_task_type(skill_input)
    prompt = build_prompt(skill_input, parsed, skill_dir)
    config = load_config(skill_dir)

    output_name = f"{task_type if task_type != 'image' else scene}-result{_output_suffix(task_type)}"
    output_path = skill_dir / config.get("defaults", {}).get("output_dir", "output") / output_name

    if task_type == "image":
        api_result = call_wan_image_api(prompt, str(output_path), config, scene=scene, model=skill_input.model)
    elif task_type == "text_to_video":
        api_result = call_wan_text_to_video_api(prompt, str(output_path), config, skill_input)
    elif task_type == "image_to_video":
        api_result = call_wan_i2v_api(prompt, str(output_path), config, skill_input)
    elif task_type == "reference_to_video":
        api_result = call_wan_r2v_api(prompt, str(output_path), config, skill_input)
    else:
        raise ValueError(f"Unsupported task_type: {task_type}")

    if api_result.get("media_type") == "video" and should_postprocess_video(skill_input):
        api_result = run_video_postprocess(api_result, skill_input, config)

    result = format_result(task_type, scene, prompt, api_result, skill_input)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
