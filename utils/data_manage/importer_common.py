"""Postman / Apifox 导入共用的 YAML 契约生成逻辑。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from utils.file_manage.yaml_handler import write_yaml
from utils.logger import log

__all__ = [
    'build_api_definition',
    'generate_safe_dirname',
    'generate_safe_filename',
    'replace_template_vars_in_dict',
    'replace_template_vars_in_str',
    'resolve_unique_yaml_path',
    'write_api_definition',
]

_VAR_PATTERN = re.compile(r'\{\{(.*?)\}\}')


def replace_template_vars_in_str(text: str) -> str:
    """将 Postman/Apifox 的 {{var}} 转为框架变量 $var。"""
    return _VAR_PATTERN.sub(r'$\1', text)


def replace_template_vars_in_dict(data: Any) -> Any:
    """递归替换字典/列表/字符串中的 {{var}}。"""
    if isinstance(data, dict):
        return {k: replace_template_vars_in_dict(v) for k, v in data.items()}
    if isinstance(data, list):
        return [replace_template_vars_in_dict(i) for i in data]
    if isinstance(data, str):
        return replace_template_vars_in_str(data)
    return data


def generate_safe_filename(name: str) -> str:
    """生成可作文件名的安全片段（保留中文）。"""
    safe = re.sub(r'[^\w\u4e00-\u9fa5]+', '_', name).strip('_')
    return safe.lower() if safe else 'unnamed_api'


def generate_safe_dirname(name: str) -> str:
    """生成分组目录名（保留中文，不去强制小写）。"""
    safe = re.sub(r'[^\w\u4e00-\u9fa5]+', '_', name).strip('_')
    return safe or 'default'


def build_api_definition(
    *,
    name: str,
    method: str,
    url_path: str,
    headers: dict[str, str] | None = None,
    json_data: dict | list | None = None,
    data: dict | None = None,
    params: dict | None = None,
    include_default_validate: bool = True,
) -> dict[str, Any]:
    """组装符合 ApiDefinitionModel 的字典。"""
    api_definition: dict[str, Any] = {
        'name': name,
        'request': {
            'method': method.upper(),
            'url': url_path,
        },
    }
    req = api_definition['request']
    if headers:
        req['headers'] = headers
    if params:
        req['params'] = params
    if json_data is not None:
        req['json'] = json_data
    if data:
        req['data'] = data
    if include_default_validate:
        api_definition['validate'] = [
            {
                'assert_type': 'eq',
                'jsonpath': '$.code',
                'expect_value': 200,
                'message': '保底断言：接口业务 code 异常（可按 Hub 实际约定在场景中覆盖）',
            }
        ]
    return api_definition


def resolve_unique_yaml_path(target_dir: Path, base_name: str) -> Path:
    """同名接口写入时自动追加序号，避免覆盖。"""
    target_dir.mkdir(parents=True, exist_ok=True)
    candidate = target_dir / f'{base_name}.yaml'
    if not candidate.exists():
        return candidate
    index = 2
    while True:
        candidate = target_dir / f'{base_name}_{index}.yaml'
        if not candidate.exists():
            return candidate
        index += 1


def write_api_definition(api_definition: dict[str, Any], file_path: Path) -> None:
    write_yaml(file_path, api_definition)
    log.info(f'✅ 生成接口契约: [{api_definition["name"]}] -> {file_path.as_posix()}')
