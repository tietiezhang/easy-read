from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StageRunResult:
    """阶段执行结果。"""

    stage_name: str
    stage_dir: Path
    done_file: Path | None
    status: str
    message: str


class BaseStage:
    """阶段基类。

    每个阶段负责管理自己的阶段目录、完成标记和阶段内部执行逻辑。
    """

    stage_name: str
    creates_done: bool = True

    def __init__(self, project_dir: Path) -> None:
        """初始化阶段对象。

        Args:
            project_dir: 书籍项目目录。
        """
        self.project_dir = project_dir

    @property
    def stage_dir(self) -> Path:
        """获取阶段目录。

        Returns:
            Path: 阶段目录路径。
        """
        return self.project_dir / self.stage_name

    @property
    def done_file(self) -> Path:
        """获取阶段完成标记文件路径。

        Returns:
            Path: .done 文件路径。
        """
        return self.stage_dir / ".done"

    def is_done(self) -> bool:
        """判断阶段是否已完成。

        Returns:
            bool: `.done` 存在时返回 True。
        """
        return self.creates_done and self.done_file.exists()

    def ensure_stage_dir(self) -> None:
        """确保阶段目录存在。"""
        self.stage_dir.mkdir(parents=True, exist_ok=True)

    def mark_done(self) -> None:
        """写入阶段完成标记。"""
        self.ensure_stage_dir()
        self.done_file.write_text("", encoding="utf-8", newline="\n")

    def execute(self) -> None:
        """执行阶段业务逻辑。

        基类只维护阶段目录。具体业务由阶段子类实现。
        """
        self.ensure_stage_dir()

    def run(self) -> StageRunResult:
        """执行阶段。

        Returns:
            StageRunResult: 阶段执行结果。
        """
        if self.is_done():
            return StageRunResult(
                stage_name=self.stage_name,
                stage_dir=self.stage_dir,
                done_file=self.done_file,
                status="skipped",
                message="阶段已完成，跳过执行。",
            )

        self.execute()

        if self.creates_done:
            self.mark_done()

        return StageRunResult(
            stage_name=self.stage_name,
            stage_dir=self.stage_dir,
            done_file=self.done_file if self.creates_done else None,
            status="done",
            message="阶段执行完成。",
        )
