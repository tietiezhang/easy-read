import json
from pathlib import Path
from typing import Any


def read_json_file(file_path: Path) -> dict[str, Any]:
    """读取 JSON 文件。

    Args:
        file_path: JSON 文件路径。

    Returns:
        dict[str, Any]: JSON 文件内容。

    Raises:
        FileNotFoundError: 文件不存在时抛出。
        ValueError: JSON 顶层不是字典时抛出。
    """
    if not file_path.exists():
        raise FileNotFoundError(f"JSON 文件不存在: {file_path}")

    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"JSON 顶层必须是字典: {file_path}")

    return data


def write_json_file(file_path: Path, data: dict[str, Any]) -> None:
    """写入 JSON 文件。

    使用临时文件写入后替换目标文件，降低写入中断导致文件损坏的风险。

    Args:
        file_path: JSON 文件路径。
        data: 需要写入的字典数据。
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")

    with temp_path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")

    temp_path.replace(file_path)
