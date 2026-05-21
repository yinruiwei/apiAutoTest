"""
测试：Hub 模块接口契约导入（RMS 对外接口）。

数据源：
  - RMS对外接口.postman.json
  - RMS对外接口.apifox.json

生成目录：api/hub/（按 Apifox/Postman 分组子目录）
"""

from __future__ import annotations

from pathlib import Path

from utils.data_manage.apifox import import_apifox_file
from utils.data_manage.postman import import_postman_file
from utils.file_manage.path_manager import path_mgr
from utils.logger import log

__all__ = [
    'HUB_APIFOX_SOURCE',
    'HUB_MODULE',
    'HUB_POSTMAN_SOURCE',
    'import_hub_from_apifox',
    'import_hub_from_postman',
]

HUB_MODULE = 'hub'
_DATA_DIR = path_mgr.docs_dir / 'api'
HUB_POSTMAN_SOURCE = _DATA_DIR / 'RMS对外接口.postman.json'
HUB_APIFOX_SOURCE = _DATA_DIR / 'RMS对外接口.apifox.json'


def import_hub_from_postman(
    *,
    source: str | Path | None = None,
    clear_target: bool = False,
) -> int:
    """
    从 Postman 集合导入 Hub 对外接口到 api/hub/。

    Postman 导出通常不含请求体 JSON，生成契约以 method/url 为主；
    需要完整请求体模板时建议使用 import_hub_from_apifox()。

    :param source: 自定义 Postman JSON 路径，默认 RMS对外接口.postman.json
    :param clear_target: 导入前是否清空 api/hub 目录
    :return: 生成的 YAML 数量
    """
    json_path = Path(source) if source else HUB_POSTMAN_SOURCE
    if clear_target:
        _clear_hub_api_dir()
    return import_postman_file(json_path, HUB_MODULE)


def import_hub_from_apifox(
    *,
    source: str | Path | None = None,
    clear_target: bool = False,
) -> int:
    """
    从 Apifox 项目导出导入 Hub 对外接口到 api/hub/。

    会根据 schemaCollection 解析 requestBody，生成带字段占位符（$字段名）的 JSON 模板。

    :param source: 自定义 Apifox JSON 路径，默认 RMS对外接口.apifox.json
    :param clear_target: 导入前是否清空 api/hub 目录
    :return: 生成的 YAML 数量
    """
    json_path = Path(source) if source else HUB_APIFOX_SOURCE
    if clear_target:
        _clear_hub_api_dir()
    return import_apifox_file(json_path, HUB_MODULE)


def _clear_hub_api_dir() -> None:
    hub_dir = path_mgr.api_dir / HUB_MODULE
    if not hub_dir.exists():
        return
    for path in sorted(hub_dir.rglob('*.yaml'), reverse=True):
        path.unlink()
    for path in sorted(hub_dir.rglob('*'), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    log.info(f'已清空目录: {hub_dir}')


if __name__ == '__main__':
    # 默认以 Apifox 为准（含请求体 Schema 模板）；需 Postman 版可改为 import_hub_from_postman(clear_target=True)
    import_hub_from_apifox(clear_target=True)
