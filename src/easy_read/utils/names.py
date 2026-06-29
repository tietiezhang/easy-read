import re

PROJECT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def validate_project_name(project_name: str) -> None:
    """校验项目名称是否合法。

    项目名只允许字母、数字、点、下划线和短横线，并且不能以特殊字符开头。
    这样可以避免路径穿越和跨平台文件名问题。

    Args:
        project_name: 项目名称。

    Raises:
        ValueError: 项目名称不合法时抛出。
    """
    if not project_name:
        raise ValueError("项目名称不能为空")

    if project_name in {".", ".."}:
        raise ValueError("项目名称不能是 . 或 ..")

    if not PROJECT_NAME_PATTERN.match(project_name):
        raise ValueError(
            "项目名称只能包含字母、数字、点、下划线和短横线，并且必须以字母或数字开头"
        )


def safe_filename_part(text: str, max_chars: int = 80) -> str:
    """生成适合文件名使用的文本片段。

    Args:
        text: 原始文本。
        max_chars: 最大字符数。

    Returns:
        str: 清理后的文件名片段。
    """
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1F]', " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:max_chars] if cleaned else "untitled"
