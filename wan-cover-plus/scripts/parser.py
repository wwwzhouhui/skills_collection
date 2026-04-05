def parse_content(skill_input):
    visual_keywords = []
    if skill_input.title:
        visual_keywords.append(skill_input.title)
    visual_keywords.extend((skill_input.highlights or [])[:3])

    main_subject = skill_input.title or skill_input.prompt or ""
    key_message = skill_input.subtitle or skill_input.prompt or ""

    return {
        "main_subject": main_subject,
        "key_message": key_message,
        "supporting_points": skill_input.highlights or [],
        "visual_keywords": visual_keywords,
        "tone": skill_input.style,
    }
