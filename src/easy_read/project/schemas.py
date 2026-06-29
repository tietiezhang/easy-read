from typing import Literal

from pydantic import BaseModel, Field

InputType = Literal["epub", "pdf"]


class Manifest(BaseModel):
    """项目描述文件结构。

    manifest.json 只保存项目元数据，不保存阶段状态。
    """

    project_name: str
    book_file: str
    book_title: str
    input_type: InputType
    created_at: str
    updated_at: str


class CreateProjectResult(BaseModel):
    """创建项目的结果。"""

    project_name: str
    project_dir: str
    manifest_file: str
    book_file: str
    config_file: str


class ClearProjectResult(BaseModel):
    """清空项目生成产物的结果。"""

    project_name: str
    project_dir: str
    removed_paths: list[str] = Field(default_factory=list)
