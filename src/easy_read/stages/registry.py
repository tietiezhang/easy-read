from dataclasses import dataclass
from pathlib import Path
from easy_read.stages.extract_stage import ExtractStage

from easy_read.stages.base import BaseStage


@dataclass(frozen=True)
class StageDefinition:
    """阶段定义。"""

    name: str
    creates_done: bool


class BasicStage(BaseStage):
    """基础阶段实现。

    用于维护阶段目录和完成标记。
    """


STAGE_DEFINITIONS: tuple[StageDefinition, ...] = (
    StageDefinition(name="01 import", creates_done=False),
    StageDefinition(name="02 extract", creates_done=True),
    StageDefinition(name="03 select", creates_done=True),
    StageDefinition(name="04 chunk", creates_done=True),
    StageDefinition(name="05 terms", creates_done=True),
    StageDefinition(name="06 translate", creates_done=True),
    StageDefinition(name="07 qa", creates_done=True),
    StageDefinition(name="08 polish", creates_done=True),
    StageDefinition(name="09 assemble", creates_done=True),
    StageDefinition(name="10 export", creates_done=True),
)


def get_stage_names() -> list[str]:
    """获取完整阶段名称列表。

    Returns:
        list[str]: 按执行顺序排列的阶段名称。
    """
    return [stage.name for stage in STAGE_DEFINITIONS]


def get_stage_definition(stage_name: str) -> StageDefinition:
    """根据阶段名获取阶段定义。

    Args:
        stage_name: 阶段名称。

    Returns:
        StageDefinition: 阶段定义。

    Raises:
        ValueError: 阶段不存在时抛出。
    """
    for definition in STAGE_DEFINITIONS:
        if definition.name == stage_name:
            return definition

    raise ValueError(f"未知阶段: {stage_name}")


def get_stage_index(stage_name: str) -> int:
    """获取阶段顺序索引。

    Args:
        stage_name: 阶段名称。

    Returns:
        int: 阶段索引。

    Raises:
        ValueError: 阶段不存在时抛出。
    """
    return get_stage_names().index(stage_name)


def create_stage(stage_name: str, project_dir: Path) -> BaseStage:
    """创建阶段对象。

    Args:
        stage_name: 阶段名称。
        project_dir: 书籍项目目录。

    Returns:
        BaseStage: 阶段对象。

    Raises:
        ValueError: 01 import 不允许作为普通阶段执行。
    """
    definition = get_stage_definition(stage_name)

    if definition.name == "01 import":
        raise ValueError("01 import 通过 project create 完成，不能作为普通阶段执行。")

    if definition.name == "02 extract":
        return ExtractStage(project_dir=project_dir)

    stage = BasicStage(project_dir=project_dir)
    stage.stage_name = definition.name
    stage.creates_done = definition.creates_done
    return stage
