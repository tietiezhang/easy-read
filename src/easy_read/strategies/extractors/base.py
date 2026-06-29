from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ExtractedSourceItem:
    """提取出的源文件记录。"""

    doc_id: str
    file: str


@dataclass(frozen=True)
class ExtractedMarkdownItem:
    """提取出的 Markdown 文件记录。"""

    doc_id: str
    file: str


@dataclass(frozen=True)
class ExtractedImageItem:
    """提取出的图片文件记录。"""

    image_id: str
    source_name: str
    file: str


@dataclass(frozen=True)
class ExtractResult:
    """书籍提取结果。"""

    source_items: list[ExtractedSourceItem] = field(default_factory=list)
    raw_md_items: list[ExtractedMarkdownItem] = field(default_factory=list)
    image_items: list[ExtractedImageItem] = field(default_factory=list)


class BookExtractor:
    """书籍提取器基类。"""

    def extract(self, book_file: Path, project_dir: Path, stage_dir: Path, config: dict) -> ExtractResult:
        """提取书籍内容。

        Args:
            book_file: 项目内的原书文件路径。
            project_dir: 书籍项目目录。
            stage_dir: 提取阶段目录。
            config: 提取阶段配置。

        Returns:
            ExtractResult: 提取结果。
        """
        raise NotImplementedError
