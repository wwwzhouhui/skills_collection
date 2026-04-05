def route_scene(skill_input):
    return skill_input.scene or "wechat_cover"


def route_task_type(skill_input):
    return getattr(skill_input, "task_type", "image") or "image"
