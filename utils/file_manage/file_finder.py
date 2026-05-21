from pathlib import Path

from utils.logger import log


def get_yaml_files(target_path: str | Path) -> list[Path]:
    """
    搜索指定路径下的所有 YAML 文件。

    1. 自动兼容传入的是“单个文件”还是“文件夹”。
    2. 如果是文件夹，会自动递归扫描（包含所有子文件夹）中的 .yaml 和 .yml。

    :param target_path: 目标路径 (文件或目录)
    :return: 包含 Path 对象的列表
    """
    path = Path(target_path)
    if not path.exists():
        err_msg = f'指定的搜索路径不存在: {path.absolute()}'
        log.error(err_msg)
        raise FileNotFoundError(err_msg)

    yaml_files: list[Path] = []

    if path.is_file():
        # 如果直接传入的是个文件，检查后缀即可
        if path.suffix.lower() in ['.yaml', '.yml']:
            yaml_files.append(path)
        else:
            log.warning(f'指定的文件不是 YAML 格式，将被忽略: {path.name}')
    elif path.is_dir():
        # 使用 rglob进行递归扫描
        yaml_files.extend(path.rglob('*.yaml'))
        yaml_files.extend(path.rglob('*.yml'))

    if not yaml_files:
        log.warning(f'在路径 [{path}] 下未找到任何 YAML 用例文件')

    return yaml_files


def get_file_info(filepath: str | Path) -> dict[str, str]:
    """
    获取文件的详细属性
    :param filepath: 文件路径
    :return: 包含文件名、无后缀名、后缀的字典
    """
    file = Path(filepath)
    return {
        'filename': file.name,  # 例如: login.yaml
        'stem': file.stem,  # 例如: login (无后缀)
        'suffix': file.suffix.lower(),  # 例如: .yaml
    }
