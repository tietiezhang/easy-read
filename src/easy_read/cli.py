import platform
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from easy_read.pipeline import PipelineRunner
from easy_read.config.loader import load_api_config
from easy_read.core.version import get_app_version
from easy_read.project import ProjectManager
from easy_read.utils.paths import (
    configs_dir,
    projects_dir,
    prompts_dir,
    repo_root,
    resources_dir,
    templates_dir,
)

app = typer.Typer(help="easy-read 书籍与文档翻译流水线")
project_app = typer.Typer(help="项目管理")
pipeline_app = typer.Typer(help="流水线管理")

app.add_typer(project_app, name="project")
app.add_typer(pipeline_app, name="pipeline")

console = Console()


@app.command()
def doctor() -> None:
    """检查项目基础路径和运行环境。"""
    path_table = Table(title="easy-read 路径检查")
    path_table.add_column("名称", style="cyan")
    path_table.add_column("路径")
    path_table.add_column("是否存在", style="green")

    paths = {
        "repo_root": repo_root(),
        "configs": configs_dir(),
        "resources": resources_dir(),
        "prompts": prompts_dir(),
        "templates": templates_dir(),
        "project_config_template": templates_dir() / "project_config.yml",
        "projects": projects_dir(),
    }

    for name, path in paths.items():
        path_table.add_row(name, str(path), "是" if path.exists() else "否")

    env_table = Table(title="easy-read 运行环境")
    env_table.add_column("项目", style="cyan")
    env_table.add_column("值")

    env_table.add_row("easy-read", get_app_version())
    env_table.add_row("Python", sys.version.split()[0])
    env_table.add_row("Python 路径", sys.executable)
    env_table.add_row("系统", platform.platform())

    console.print(path_table)
    console.print(env_table)


@app.command(name="config-check")
def config_check(
        use_example: bool = typer.Option(
            False,
            "--use-example",
            help="检查 configs/api.example.yml，而不是 configs/api.yml。",
        ),
) -> None:
    """检查 API 配置文件是否可以读取和校验。"""
    try:
        api_config, api_file = load_api_config(use_example=use_example)
    except Exception as error:
        console.print(f"[red]API 配置检查失败：{error}[/red]")
        raise typer.Exit(code=1) from error

    table = Table(title="API 配置检查")
    table.add_column("项目", style="cyan")
    table.add_column("数量 / 内容")

    table.add_row("配置文件", str(api_file))
    table.add_row("providers", str(len(api_config.providers)))
    table.add_row("model_profiles", str(len(api_config.model_profiles)))

    console.print(table)

    profile_table = Table(title="模型配置档案")
    profile_table.add_column("profile", style="cyan")
    profile_table.add_column("provider")
    profile_table.add_column("model")
    profile_table.add_column("endpoint")

    for profile_name, profile in api_config.model_profiles.items():
        profile_table.add_row(
            profile_name,
            profile.provider,
            profile.model,
            profile.endpoint,
        )

    console.print(profile_table)
    console.print("[green]API 配置检查通过。[/green]")


@project_app.command(name="create")
def create_project(
        name: str = typer.Option(..., "--name", help="项目名称，例如 test-book。"),
        book: Path = typer.Option(..., "--book", help="原书文件路径，支持 EPUB / PDF。"),
        title: str | None = typer.Option(None, "--title", help="书名。未填写时使用文件名。"),
) -> None:
    """通过导入原书创建项目。"""
    manager = ProjectManager()

    try:
        result = manager.create_project(project_name=name, source_book_file=book, book_title=title)
    except Exception as error:
        console.print(f"[red]创建项目失败：{error}[/red]")
        raise typer.Exit(code=1) from error

    table = Table(title="项目创建完成")
    table.add_column("项目", style="cyan")
    table.add_column("路径 / 内容")

    table.add_row("项目名称", result.project_name)
    table.add_row("项目目录", result.project_dir)
    table.add_row("manifest.json", result.manifest_file)
    table.add_row("原书文件", result.book_file)
    table.add_row("config.yml", result.config_file)

    console.print(table)


@project_app.command(name="clear")
def clear_project(
        name: str = typer.Option(..., "--name", help="项目名称，例如 test-book。"),
        force: bool = typer.Option(False, "--force", help="直接清空，不弹出确认。"),
) -> None:
    """清空项目生成产物。"""
    if not force:
        confirmed = typer.confirm(
            f"确认清空项目 {name} 的阶段产物吗？book、manifest.json、config.yml 会保留。"
        )
        if not confirmed:
            console.print("[yellow]已取消。[/yellow]")
            raise typer.Exit(code=0)

    manager = ProjectManager()

    try:
        result = manager.clear_project(project_name=name)
    except Exception as error:
        console.print(f"[red]清空项目失败：{error}[/red]")
        raise typer.Exit(code=1) from error

    table = Table(title="项目清理完成")
    table.add_column("项目", style="cyan")
    table.add_column("内容")

    table.add_row("项目名称", result.project_name)
    table.add_row("项目目录", result.project_dir)
    table.add_row("删除数量", str(len(result.removed_paths)))

    console.print(table)

    if result.removed_paths:
        removed_table = Table(title="已删除路径")
        removed_table.add_column("路径")

        for removed_path in result.removed_paths:
            removed_table.add_row(removed_path)

        console.print(removed_table)


@pipeline_app.command(name="status")
def pipeline_status(
        project: str = typer.Option(..., "--project", help="项目名称，例如 test-book。"),
) -> None:
    """查看项目流水线阶段状态。"""
    runner = PipelineRunner(project_name=project)

    try:
        statuses = runner.get_status()
    except Exception as error:
        console.print(f"[red]读取流水线状态失败：{error}[/red]")
        raise typer.Exit(code=1) from error

    table = Table(title=f"流水线状态：{project}")
    table.add_column("阶段", style="cyan")
    table.add_column("状态")
    table.add_column("阶段目录")
    table.add_column(".done")

    for item in statuses:
        table.add_row(
            item.stage_name,
            item.status,
            str(item.stage_dir) if item.stage_dir else "",
            str(item.done_file) if item.done_file else "",
        )

    console.print(table)


@pipeline_app.command(name="run-stage")
def pipeline_run_stage(
        project: str = typer.Option(..., "--project", help="项目名称，例如 test-book。"),
        stage: str = typer.Option(..., "--stage", help='阶段名称，例如 "02 extract"。'),
) -> None:
    """执行单个流水线阶段。"""
    runner = PipelineRunner(project_name=project)

    try:
        result = runner.run_stage(stage_name=stage)
    except Exception as error:
        console.print(f"[red]阶段执行失败：{error}[/red]")
        raise typer.Exit(code=1) from error

    table = Table(title=f"阶段执行结果：{project}")
    table.add_column("项目", style="cyan")
    table.add_column("内容")

    table.add_row("阶段", result.stage_name)
    table.add_row("状态", result.status)
    table.add_row("阶段目录", str(result.stage_dir))
    table.add_row(".done", str(result.done_file) if result.done_file else "")
    table.add_row("说明", result.message)

    console.print(table)


@pipeline_app.command(name="run-from")
def pipeline_run_from(
        project: str = typer.Option(..., "--project", help="项目名称，例如 test-book。"),
        stage: str = typer.Option(..., "--stage", help='起始阶段名称，例如 "02 extract"。'),
) -> None:
    """从指定阶段开始执行到最后一个阶段。"""
    runner = PipelineRunner(project_name=project)

    try:
        results = runner.run_from(stage_name=stage)
    except Exception as error:
        console.print(f"[red]流水线执行失败：{error}[/red]")
        raise typer.Exit(code=1) from error

    table = Table(title=f"流水线执行结果：{project}")
    table.add_column("阶段", style="cyan")
    table.add_column("状态")
    table.add_column("说明")

    for result in results:
        table.add_row(result.stage_name, result.status, result.message)

    console.print(table)


@pipeline_app.command(name="run-all")
def pipeline_run_all(
        project: str = typer.Option(..., "--project", help="项目名称，例如 test-book。"),
) -> None:
    """执行完整流水线。"""
    runner = PipelineRunner(project_name=project)

    try:
        results = runner.run_all()
    except Exception as error:
        console.print(f"[red]流水线执行失败：{error}[/red]")
        raise typer.Exit(code=1) from error

    table = Table(title=f"完整流水线执行结果：{project}")
    table.add_column("阶段", style="cyan")
    table.add_column("状态")
    table.add_column("说明")

    for result in results:
        table.add_row(result.stage_name, result.status, result.message)

    console.print(table)


@app.command(name="version")
def show_version() -> None:
    """显示 easy-read 安装包版本号。"""
    console.print(get_app_version())


if __name__ == "__main__":
    app()
