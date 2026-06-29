from pathlib import Path

from easy_read.config.loader import load_project_config
from easy_read.project import load_manifest
from easy_read.stages.base import BaseStage
from easy_read.strategies.extractors.base import ExtractResult
from easy_read.strategies.extractors.epub_extractor import EpubExtractor
from easy_read.utils.json_io import write_json_file


class ExtractStage(BaseStage):
    """02 extract 阶段。

    负责把原书解析为源文件、原始 Markdown 和图片资源。
    """

    stage_name = "02 extract"
    creates_done = True

    def execute(self) -> None:
        """执行书籍提取。"""
        manifest = load_manifest(self.project_dir)
        project_config, _ = load_project_config(self.project_dir)
        extract_config = project_config.get_stage_config(self.stage_name)

        book_file = self.project_dir / manifest.book_file
        extractor = self.create_extractor(input_type=manifest.input_type)

        result = extractor.extract(
            book_file=book_file,
            project_dir=self.project_dir,
            stage_dir=self.stage_dir,
            config=extract_config,
        )

        self.write_records(result)

    def create_extractor(self, input_type: str):
        """创建书籍提取器。

        Args:
            input_type: 输入类型。

        Returns:
            object: 书籍提取器。

        Raises:
            NotImplementedError: 输入类型暂未支持时抛出。
        """
        if input_type == "epub":
            return EpubExtractor()

        raise NotImplementedError(f"暂不支持该输入类型的提取: {input_type}")

    def write_records(self, result: ExtractResult) -> None:
        """写入提取阶段记录文件。

        Args:
            result: 提取结果。
        """
        source_data = {
            "items": [
                {
                    "doc_id": item.doc_id,
                    "file": item.file,
                }
                for item in result.source_items
            ]
        }

        raw_md_data = {
            "items": [
                {
                    "doc_id": item.doc_id,
                    "file": item.file,
                }
                for item in result.raw_md_items
            ]
        }

        write_json_file(self.stage_dir / "source.json", source_data)
        write_json_file(self.stage_dir / "raw_md.json", raw_md_data)

        if result.image_items:
            image_data = {
                "items": [
                    {
                        "image_id": item.image_id,
                        "source_name": item.source_name,
                        "file": item.file,
                    }
                    for item in result.image_items
                ]
            }
            write_json_file(self.project_dir / "images" / "images.json", image_data)
