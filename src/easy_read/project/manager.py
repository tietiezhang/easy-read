import shutil
from datetime import datetime, timezone
from pathlib import Path

from easy_read.project.schemas import ClearProjectResult, CreateProjectResult, InputType, Manifest
from easy_read.utils.json_io import read_json_file, write_json_file
from easy_read.utils.names import validate_project_name
from easy_read.utils.paths import resolve_project_dir, templates_dir

SUPPORTED_INPUT_TYPES: dict[str, InputType] = {
    ".epub": "epub",
    ".pdf": "pdf",
}

GENERATED_DIR_NAMES = [
    "02 extract",
    "03 select",
    "04 chunk",
    "05 terms",
    "06 translate",
    "07 qa",
    "08 polish",
    "09 assemble",
    "10 export",
    "images",
]


def utc_now_text() -> str:
    """生成 UTC 时间文本。

    Returns:
        str: ISO 8601 格式时间文本。
    """
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def detect_input_type(book_file: Path) -> InputType:
    """根据原书文件后缀判断输入类型。

    Args:
        book_file: 原书文件路径。

    Returns:
        InputType: 输入类型。

    Raises:
        ValueError: 文件类型不受支持时抛出。
    """
    suffix = book_file.suffix.lower()

    if suffix not in SUPPORTED_INPUT_TYPES:
        supported = ", ".join(sorted(SUPPORTED_INPUT_TYPES.keys()))
        raise ValueError(f"不支持的书籍类型: {suffix}。支持类型: {supported}")

    return SUPPORTED_INPUT_TYPES[suffix]


def load_manifest(project_dir: Path) -> Manifest:
    """读取项目 manifest.json。

    Args:
        project_dir: 项目目录。

    Returns:
        Manifest: 项目描述对象。
    """
    data = read_json_file(project_dir / "manifest.json")
    return Manifest.model_validate(data)


def write_manifest(project_dir: Path, manifest: Manifest) -> None:
    """写入项目 manifest.json。

    Args:
        project_dir: 项目目录。
        manifest: 项目描述对象。
    """
    write_json_file(project_dir / "manifest.json", manifest.model_dump())


def create_project_config_from_template(project_dir: Path) -> Path:
    """根据模板创建项目配置文件。

    Args:
        project_dir: 项目目录。

    Returns:
        Path: 生成的 config.yml 路径。

    Raises:
        FileNotFoundError: 项目配置模板不存在时抛出。
    """
    template_file = templates_dir() / "project_config.yml"

    if not template_file.exists():
        raise FileNotFoundError(f"项目配置模板不存在: {template_file}")

    target_file = project_dir / "config.yml"

    if target_file.exists():
        return target_file

    shutil.copy2(template_file, target_file)
    return target_file


class ProjectManager:
    """项目管理器。

    负责创建项目、读取项目描述和清理阶段产物。
    """

    def create_project(
            self,
            project_name: str,
            source_book_file: Path,
            book_title: str | None = None,
    ) -> CreateProjectResult:
        """通过导入原书创建项目。

        Args:
            project_name: 项目名称。
            source_book_file: 外部原书文件路径。
            book_title: 书名。未传入时使用文件名主体。

        Returns:
            CreateProjectResult: 创建结果。

        Raises:
            ValueError: 项目名称非法、项目已存在、文件类型不支持时抛出。
            FileNotFoundError: 原书文件或项目配置模板不存在时抛出。
        """
        validate_project_name(project_name)

        source_book_file = source_book_file.expanduser().resolve()

        if not source_book_file.exists():
            raise FileNotFoundError(f"原书文件不存在: {source_book_file}")

        if not source_book_file.is_file():
            raise ValueError(f"原书路径不是文件: {source_book_file}")

        input_type = detect_input_type(source_book_file)
        project_dir = resolve_project_dir(project_name)

        if project_dir.exists():
            raise ValueError(f"项目已存在: {project_dir}")

        book_dir = project_dir / "book"
        book_dir.mkdir(parents=True, exist_ok=False)

        target_book_file = book_dir / source_book_file.name
        shutil.copy2(source_book_file, target_book_file)

        created_at = utc_now_text()
        manifest = Manifest(
            project_name=project_name,
            book_file=target_book_file.relative_to(project_dir).as_posix(),
            book_title=book_title or source_book_file.stem,
            input_type=input_type,
            created_at=created_at,
            updated_at=created_at,
        )
        write_manifest(project_dir, manifest)

        config_file = create_project_config_from_template(project_dir)

        return CreateProjectResult(
            project_name=project_name,
            project_dir=str(project_dir),
            manifest_file=str(project_dir / "manifest.json"),
            book_file=str(target_book_file),
            config_file=str(config_file),
        )

    def clear_project(self, project_name: str) -> ClearProjectResult:
        """清空项目生成产物。

        保留 book、manifest.json 和 config.yml，只删除阶段目录与图片目录。

        Args:
            project_name: 项目名称。

        Returns:
            ClearProjectResult: 清理结果。

        Raises:
            FileNotFoundError: 项目目录不存在时抛出。
        """
        validate_project_name(project_name)

        project_dir = resolve_project_dir(project_name)

        if not project_dir.exists():
            raise FileNotFoundError(f"项目不存在: {project_dir}")

        removed_paths: list[str] = []

        for dir_name in GENERATED_DIR_NAMES:
            target_path = project_dir / dir_name

            if target_path.exists():
                shutil.rmtree(target_path)
                removed_paths.append(str(target_path))

        return ClearProjectResult(
            project_name=project_name,
            project_dir=str(project_dir),
            removed_paths=removed_paths,
        )
