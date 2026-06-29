from pathlib import Path


def find_parent_with_marker(start: Path, marker: str) -> Path | None:
    """从指定路径向上查找包含目标标记的父目录。

    Args:
        start: 起始路径。
        marker: 用于识别目录的文件名或文件夹名。

    Returns:
        Path | None: 找到的目录；如果没有找到，则返回 None。
    """
    resolved_start = start.resolve()

    for parent in [resolved_start, *resolved_start.parents]:
        if (parent / marker).exists():
            return parent

    return None


def repo_root() -> Path:
    """获取项目根目录。

    优先通过 pyproject.toml 定位项目根目录，避免写死操作系统路径。

    Returns:
        Path: 项目根目录。
    """
    current_file = Path(__file__).resolve()
    found_root = find_parent_with_marker(current_file, "pyproject.toml")

    if found_root is not None:
        return found_root

    return Path.cwd().resolve()


def configs_dir() -> Path:
    """获取全局配置目录。

    Returns:
        Path: configs 目录路径。
    """
    return repo_root() / "configs"


def resources_dir() -> Path:
    """获取资源目录。

    Returns:
        Path: resources 目录路径。
    """
    return repo_root() / "resources"


def prompts_dir() -> Path:
    """获取全局 Prompt 目录。

    Returns:
        Path: resources/prompts 目录路径。
    """
    return resources_dir() / "prompts"


def templates_dir() -> Path:
    """获取模板目录。

    Returns:
        Path: resources/templates 目录路径。
    """
    return resources_dir() / "templates"


def projects_dir() -> Path:
    """获取项目数据目录。

    Returns:
        Path: projects 目录路径。
    """
    return repo_root() / "projects"


def resolve_project_dir(project_name: str) -> Path:
    """根据项目名获取项目目录。

    Args:
        project_name: 项目名称。

    Returns:
        Path: projects 下对应项目目录。
    """
    return projects_dir() / project_name
