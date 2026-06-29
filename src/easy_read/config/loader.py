from pathlib import Path
from typing import Any

import yaml

from easy_read.config.schemas import ApiConfig, ModelProfileConfig, ProjectConfig
from easy_read.utils.paths import configs_dir


def read_yaml_file(file_path: Path) -> dict[str, Any]:
    """读取 YAML 文件。

    Args:
        file_path: YAML 文件路径。

    Returns:
        dict[str, Any]: YAML 文件内容。

    Raises:
        FileNotFoundError: 文件不存在时抛出。
        ValueError: YAML 顶层不是字典时抛出。
    """
    if not file_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {file_path}")

    with file_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if data is None:
        return {}

    if not isinstance(data, dict):
        raise ValueError(f"YAML 顶层必须是字典: {file_path}")

    return data


def resolve_api_config_path(project_dir: Path | None = None, use_example: bool = False) -> Path:
    """解析 API 配置文件路径。

    Args:
        project_dir: 项目目录。传入后优先查找项目级 api.yml。
        use_example: 是否读取 api.example.yml。

    Returns:
        Path: API 配置文件路径。

    Raises:
        FileNotFoundError: 找不到可用 API 配置文件时抛出。
    """
    if use_example:
        return configs_dir() / "api.example.yml"

    if project_dir is not None:
        project_api_file = project_dir / "api.yml"
        if project_api_file.exists():
            return project_api_file

    global_api_file = configs_dir() / "api.yml"
    if global_api_file.exists():
        return global_api_file

    raise FileNotFoundError("未找到 api.yml。请复制 configs/api.example.yml 为 configs/api.yml 后填写配置。")


def load_api_config(project_dir: Path | None = None, use_example: bool = False) -> tuple[ApiConfig, Path]:
    """加载并校验 API 配置。

    Args:
        project_dir: 项目目录。传入后优先读取项目级 api.yml。
        use_example: 是否读取示例配置。

    Returns:
        tuple[ApiConfig, Path]: API 配置对象和实际读取的文件路径。
    """
    api_file = resolve_api_config_path(project_dir=project_dir, use_example=use_example)
    data = read_yaml_file(api_file)
    return ApiConfig.model_validate(data), api_file


def load_project_config(project_dir: Path) -> tuple[ProjectConfig, Path]:
    """加载项目流程配置。

    Args:
        project_dir: 项目目录。

    Returns:
        tuple[ProjectConfig, Path]: 项目配置对象和实际读取的文件路径。
    """
    config_file = project_dir / "config.yml"
    data = read_yaml_file(config_file)
    return ProjectConfig(raw=data), config_file


def get_model_profile(api_config: ApiConfig, profile_name: str) -> ModelProfileConfig:
    """根据名称获取模型配置档案。

    Args:
        api_config: API 配置对象。
        profile_name: 模型配置档案名称，例如 translate_model。

    Returns:
        ModelProfileConfig: 模型配置档案。

    Raises:
        KeyError: 指定名称不存在时抛出。
    """
    if profile_name not in api_config.model_profiles:
        raise KeyError(f"model_profile 不存在: {profile_name}")

    return api_config.model_profiles[profile_name]
