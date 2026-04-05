from pathlib import Path
import yaml


ASSETS_DIR = "assets"
VIDEO_DEFAULT_STYLE_HINT = "cinematic, high coherence, stable subject consistency, smooth motion"


def load_scene_template(scene: str, base_dir: Path):
    path = base_dir / ASSETS_DIR / "templates" / f"{scene}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_style_prompt(style: str, base_dir: Path):
    if not style:
        return ""
    path = base_dir / ASSETS_DIR / "prompts" / f"{style}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _join_highlights(skill_input):
    return "；".join(skill_input.highlights) if skill_input.highlights else "无"


def _join_brand_colors(skill_input):
    return ", ".join(skill_input.brand_colors) if skill_input.brand_colors else "auto"


def _reference_summary(skill_input):
    image_refs = skill_input.reference_images or []
    video_refs = skill_input.reference_videos or []
    return {
        "image_refs": image_refs,
        "video_refs": video_refs,
        "image_text": ", ".join(image_refs) if image_refs else "无",
        "video_text": ", ".join(video_refs) if video_refs else "无",
    }


def build_image_prompt(skill_input, parsed, base_dir: Path) -> str:
    scene_cfg = load_scene_template(skill_input.scene, base_dir)
    style_prompt = load_style_prompt(skill_input.style, base_dir)
    highlights = _join_highlights(skill_input)
    brand_colors = _join_brand_colors(skill_input)

    return f"""
{style_prompt}

Scene: {scene_cfg['scene']}
Aspect Ratio: {scene_cfg['aspect_ratio']}
Composition: {scene_cfg['composition']}
Text Layout: {scene_cfg['text_layout']}
Style Hint: {scene_cfg['style_hint']}

Title: {skill_input.title}
Subtitle: {skill_input.subtitle or ''}
Highlights: {highlights}
Main Subject: {parsed['main_subject']}
Key Message: {parsed['key_message']}
Visual Keywords: {', '.join(parsed['visual_keywords'])}
Brand Colors: {brand_colors}
Need Text Layout: {skill_input.need_text_layout}
Edit Instruction: {skill_input.edit_instruction or ''}

Please generate a polished visual asset suitable for this content scenario.
No watermark, no unrelated brand logo, no messy text artifacts.
""".strip()


def build_text_to_video_prompt(skill_input, parsed, base_dir: Path) -> str:
    style_prompt = load_style_prompt(skill_input.style, base_dir)
    highlights = _join_highlights(skill_input)
    brand_colors = _join_brand_colors(skill_input)

    return f"""
{style_prompt}

Task: text to video
Style Hint: {VIDEO_DEFAULT_STYLE_HINT}
Main Subject: {parsed['main_subject']}
Key Message: {parsed['key_message']}
Title: {skill_input.title or ''}
Prompt Override: {skill_input.prompt or ''}
Highlights: {highlights}
Visual Keywords: {', '.join(parsed['visual_keywords'])}
Brand Colors: {brand_colors}
Camera Instruction: {skill_input.camera_instruction or 'Use stable cinematic framing with natural movement.'}
Motion Instruction: {skill_input.motion_instruction or 'Animate the scene with smooth, believable motion and clear focal subject continuity.'}
Negative Prompt: {skill_input.negative_prompt or ''}

Please create a smooth, coherent video clip with stable subject identity, clean motion, and no visual glitches.
Avoid flicker, distorted limbs, warped text, broken geometry, extra subjects, and sudden style drift.
""".strip()


def build_i2v_prompt(skill_input, parsed, base_dir: Path) -> str:
    style_prompt = load_style_prompt(skill_input.style, base_dir)
    highlights = _join_highlights(skill_input)
    brand_colors = _join_brand_colors(skill_input)
    refs = _reference_summary(skill_input)

    return f"""
{style_prompt}

Task: image to video
Style Hint: {VIDEO_DEFAULT_STYLE_HINT}
Main Subject: {parsed['main_subject']}
Key Message: {parsed['key_message']}
Title: {skill_input.title or ''}
Prompt Override: {skill_input.prompt or ''}
Highlights: {highlights}
Reference Images: {refs['image_text']}
Brand Colors: {brand_colors}
Camera Instruction: {skill_input.camera_instruction or 'Preserve the original composition while adding subtle cinematic motion.'}
Motion Instruction: {skill_input.motion_instruction or 'Keep the main subject consistent with the reference image and animate it smoothly.'}
Negative Prompt: {skill_input.negative_prompt or ''}

Please animate the reference image into a smooth short video.
Preserve subject identity, silhouette, key colors, and scene composition while adding believable motion.
Avoid flicker, face drift, geometry collapse, extra limbs, and abrupt scene changes.
""".strip()


def build_r2v_prompt(skill_input, parsed, base_dir: Path) -> str:
    style_prompt = load_style_prompt(skill_input.style, base_dir)
    highlights = _join_highlights(skill_input)
    brand_colors = _join_brand_colors(skill_input)
    refs = _reference_summary(skill_input)

    return f"""
{style_prompt}

Task: reference to video
Style Hint: {VIDEO_DEFAULT_STYLE_HINT}
Main Subject: {parsed['main_subject']}
Key Message: {parsed['key_message']}
Title: {skill_input.title or ''}
Prompt Override: {skill_input.prompt or ''}
Highlights: {highlights}
Reference Images: {refs['image_text']}
Reference Videos: {refs['video_text']}
Brand Colors: {brand_colors}
Camera Instruction: {skill_input.camera_instruction or 'Use coherent cinematic framing and preserve the core subject identity from the references.'}
Motion Instruction: {skill_input.motion_instruction or 'Use the reference assets to keep character consistency while producing smooth, natural motion.'}
Negative Prompt: {skill_input.negative_prompt or ''}

Please generate a smooth reference-guided video.
If both image and video references are present, use video references for motion rhythm and image references for appearance details.
Avoid identity drift, extra characters, temporal flicker, geometry distortions, and unstable backgrounds.
""".strip()


def build_prompt(skill_input, parsed, base_dir: Path) -> str:
    task_type = getattr(skill_input, "task_type", "image") or "image"
    if task_type == "text_to_video":
        return build_text_to_video_prompt(skill_input, parsed, base_dir)
    if task_type == "image_to_video":
        return build_i2v_prompt(skill_input, parsed, base_dir)
    if task_type == "reference_to_video":
        return build_r2v_prompt(skill_input, parsed, base_dir)
    return build_image_prompt(skill_input, parsed, base_dir)
