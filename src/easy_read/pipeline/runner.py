from dataclasses import dataclass
from pathlib import Path

from easy_read.project import load_manifest
from easy_read.stages.base import StageRunResult
from easy_read.stages.registry import create_stage, get_stage_index, get_stage_names
from easy_read.utils.paths import resolve_project_dir


@dataclass(frozen=True)
class PipelineStageStatus:
    """流水线阶段状态。"""

    stage_name: str
    stage_dir: Path | None
    done_file: Path | None
    status: str


class PipelineRunner:
    """流水线执行器。

    负责按阶段顺序执行项目流程。
    """

    def __init__(self, project_name: str) -> None:
        """初始化流水线执行器。

        Args:
            project_name: 项目名称。
        """
        self.project_name = project_name
        self.project_dir = resolve_project_dir(project_name)

    def validate_project(self) -> None:
        """校验项目是否具备运行流水线的基础文件。

        Raises:
            FileNotFoundError: 项目目录、manifest.json、原书文件或 config.yml 不存在时抛出。
        """
        if not self.project_dir.exists():
            raise FileNotFoundError(f"项目不存在: {self.project_dir}")

        manifest = load_manifest(self.project_dir)

        manifest_file = self.project_dir / "manifest.json"
        book_file = self.project_dir / manifest.book_file
        config_file = self.project_dir / "config.yml"

        if not manifest_file.exists():
            raise FileNotFoundError(f"manifest.json 不存在: {manifest_file}")

        if not book_file.exists():
            raise FileNotFoundError(f"原书文件不存在: {book_file}")

        if not config_file.exists():
            raise FileNotFoundError(f"config.yml 不存在: {config_file}")

    def get_status(self) -> list[PipelineStageStatus]:
        """获取流水线阶段状态。

        Returns:
            list[PipelineStageStatus]: 阶段状态列表。
        """
        self.validate_project()

        statuses: list[PipelineStageStatus] = []

        for stage_name in get_stage_names():
            if stage_name == "01 import":
                statuses.append(
                    PipelineStageStatus(
                        stage_name=stage_name,
                        stage_dir=self.project_dir,
                        done_file=None,
                        status="done",
                    )
                )
                continue

            stage_dir = self.project_dir / stage_name
            done_file = stage_dir / ".done"
            status = "done" if done_file.exists() else "pending"

            statuses.append(
                PipelineStageStatus(
                    stage_name=stage_name,
                    stage_dir=stage_dir,
                    done_file=done_file,
                    status=status,
                )
            )

        return statuses

    def run_stage(self, stage_name: str) -> StageRunResult:
        """执行单个阶段。

        Args:
            stage_name: 阶段名称。

        Returns:
            StageRunResult: 阶段执行结果。
        """
        self.validate_project()

        stage = create_stage(stage_name=stage_name, project_dir=self.project_dir)
        return stage.run()

    def run_from(self, stage_name: str) -> list[StageRunResult]:
        """从指定阶段开始执行到最后一个阶段。

        已完成阶段会自动跳过。

        Args:
            stage_name: 起始阶段名称。

        Returns:
            list[StageRunResult]: 阶段执行结果列表。
        """
        self.validate_project()

        start_index = get_stage_index(stage_name)
        stage_names = get_stage_names()[start_index:]

        results: list[StageRunResult] = []

        for current_stage_name in stage_names:
            if current_stage_name == "01 import":
                continue

            results.append(self.run_stage(current_stage_name))

        return results

    def run_all(self) -> list[StageRunResult]:
        """执行完整流水线。

        01 import 由项目创建完成，因此完整流水线从 02 extract 开始。

        Returns:
            list[StageRunResult]: 阶段执行结果列表。
        """
        return self.run_from("02 extract")
