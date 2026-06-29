from importlib.metadata import PackageNotFoundError, version

PACKAGE_NAME = "easy-read"


def get_app_version() -> str:
    """获取 easy-read 安装包版本号。

    版本号从 Python 包元数据读取，避免在业务代码中重复维护版本字符串。

    Returns:
        str: 安装包版本号；如果包元数据不可用，则返回 unknown。
    """
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        return "unknown"
