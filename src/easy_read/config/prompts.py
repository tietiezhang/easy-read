from dataclasses import dataclass
from pathlib import Path

from easy_read.utils.paths import prompts_dir, repo_root


@dataclass(frozen=True)
class PromptFile:
    """Prompt 文件读取结果。"""

    path: Path
    text: str


def resolve_prompt_path(prompt_ref: str, project_dir: Path | None = None) -> Path:
    """解析 Prompt 文件路径。

    查找顺序：
    1. 绝对路径；
    2. 项目目录下的相对路径；
    3. 项目 prompts 目录下的同名文件；
    4. 仓库根目录下的相对路径；
    5. 全局 prompts 目录下的同名文件。

    Args:
        prompt_ref: Prompt 文件引用路径。
        project_dir: 项目目录。

    Returns:
        Path: Prompt 文件路径。

    Raises:
        FileNotFoundError: 找不到 Prompt 文件时抛出。
    """
    ref_path = Path(prompt_ref)

    candidates: list[Path] = []

    if ref_path.is_absolute():
        candidates.append(ref_path)
    else:
        if project_dir is not None:
            candidates.append(project_dir / ref_path)
            candidates.append(project_dir / "prompts" / ref_path.name)

        candidates.append(repo_root() / ref_path)
        candidates.append(prompts_dir() / ref_path.name)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(f"Prompt 文件不存在: {prompt_ref}")


def load_prompt_file(prompt_ref: str, project_dir: Path | None = None) -> PromptFile:
    """读取 Prompt 文件。

    Args:
        prompt_ref: Prompt 文件引用路径。
        project_dir: 项目目录。

    Returns:
        PromptFile: Prompt 文件路径和文本内容。
    """
    prompt_path = resolve_prompt_path(prompt_ref=prompt_ref, project_dir=project_dir)
    text = prompt_path.read_text(encoding="utf-8")
    return PromptFile(path=prompt_path, text=text)


def load_prompt_text(prompt_ref: str, project_dir: Path | None = None) -> str:
    """读取 Prompt 文本。

    Args:
        prompt_ref: Prompt 文件引用路径。
        project_dir: 项目目录。

    Returns:
        str: Prompt 文本内容。
    """
    return load_prompt_file(prompt_ref=prompt_ref, project_dir=project_dir).text
