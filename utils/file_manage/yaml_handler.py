from pathlib import Path
from typing import Any

import yaml

from core.exceptions import YamlFormatError
from utils.logger import log


def read_yaml(file_path: str | Path) -> dict[str, Any] | list[Any]:
    """
    读取 YAML 文件内容

    :param file_path: 文件的绝对或相对路径
    :return: 解析后的字典或列表
    """
    path = Path(file_path)
    if not path.exists():
        err_msg = f'YAML 文件不存在: {path.absolute()}'
        log.error(err_msg)
        raise FileNotFoundError(err_msg)

    try:
        with path.open('r', encoding='utf-8') as f:
            # 使用 safe_load 替代 FullLoader，防止 YAML 注入漏洞
            data = yaml.safe_load(f)

        return data or {}

    except yaml.YAMLError as e:
        err_msg = f'YAML 解析错误 [{path.name}]: {e}'
        log.error(err_msg)
        raise YamlFormatError(err_msg) from e
    except Exception as e:
        log.error(f'读取 YAML 文件出现未知异常 [{path.name}]: {e}')
        raise e


def write_yaml(file_path: str | Path, data: Any, mode: str = 'w') -> None:
    """
    将数据写入 YAML 文件

    :param file_path: 写入的文件路径
    :param data: 需要写入的数据 (通常为 dict 或 list)
    :param mode: 写入模式，默认为 'w' (覆盖)，可选 'a' (追加)
    """
    path = Path(file_path)

    # 自动创建父级目录
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with path.open(mode, encoding='utf-8') as f:
            yaml.safe_dump(
                data,
                f,
                allow_unicode=True,  # 保证中文正常写入，不被转码为 \uXXXX
                sort_keys=False,  # 保持原字典的顺序，不自动按字母排序
                default_flow_style=False,  # 采用清晰的块状结构（换行缩进），而不是 JSON 风格的内联 {}
            )
        log.info(f'成功写入 YAML 文件: {path.name}')
    except Exception as e:
        log.error(f'写入 YAML 文件失败 [{path.name}]: {e}')
        raise e


def update_yaml_vars(file_path: str | Path, new_data: dict[str, Any]) -> None:
    """
    更新/追加 YAML 文件中的字典数据 (常用于动态更新全局变量 / Token)

    :param file_path: 目标 YAML 文件路径
    :param new_data: 需要更新的字典数据
    """
    path = Path(file_path)
    existing_data = {}

    # 如果文件存在且有内容，则先读取出来
    if path.exists():
        loaded_data = read_yaml(path)
        if isinstance(loaded_data, dict):
            existing_data = loaded_data
        else:
            log.warning(f'[{path.name}] 内容非字典结构，将被全新覆盖')

    # 将新数据合并到旧数据中
    existing_data.update(new_data)

    # 重新覆盖写入
    write_yaml(path, existing_data)
