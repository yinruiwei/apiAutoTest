"""Postman Collection v2.1 → 框架 API 积木 YAML。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from utils.data_manage.importer_common import (
    build_api_definition,
    generate_safe_dirname,
    generate_safe_filename,
    replace_template_vars_in_dict,
    replace_template_vars_in_str,
    resolve_unique_yaml_path,
    write_api_definition,
)
from utils.file_manage.path_manager import path_mgr
from utils.logger import log

__all__ = ['import_postman_file']


def _clean_url_path(raw_url: str | dict) -> str:
    """剥离 {{baseUrl}} 等变量，只保留路径部分。"""
    if isinstance(raw_url, dict):
        if 'path' in raw_url:
            return '/' + '/'.join(raw_url['path'])
        raw_url = raw_url.get('raw', '')

    url_str = re.sub(r'^\{\{.*?\}\}', '', str(raw_url))
    parsed = urlparse(url_str)
    path = parsed.path if parsed.path else url_str
    if path and not path.startswith('/'):
        path = '/' + path
    return path or '/'


def _parse_headers(postman_headers: list) -> dict[str, str]:
    headers: dict[str, str] = {}
    for h in postman_headers:
        if h.get('disabled', False):
            continue
        key = h.get('key')
        value = h.get('value')
        if key and value is not None:
            headers[key] = replace_template_vars_in_str(str(value))
    return headers


def _parse_body(postman_body: dict) -> tuple[dict | list | None, dict | None]:
    if not postman_body:
        return None, None

    mode = postman_body.get('mode')

    if mode == 'raw':
        raw_content = postman_body.get('raw', '')
        if not raw_content:
            return None, None
        try:
            json_data = json.loads(raw_content)
            return replace_template_vars_in_dict(json_data), None
        except json.JSONDecodeError:
            return None, {'_raw_text': raw_content}

    if mode in ('formdata', 'urlencoded'):
        form_items = postman_body.get(mode, [])
        data: dict[str, Any] = {}
        for item in form_items:
            if item.get('disabled', False):
                continue
            key = item.get('key')
            value = item.get('value', '')
            if key:
                data[key] = replace_template_vars_in_str(str(value))
        return None, data if data else None

    return None, None


def _process_items(
    items: list,
    target_base: Path,
    folder_parts: tuple[str, ...] = (),
) -> int:
    count = 0
    for item in items:
        if 'item' in item:
            sub_name = item.get('name', '')
            sub_parts = folder_parts + (sub_name,) if sub_name else folder_parts
            count += _process_items(item['item'], target_base, sub_parts)
            continue

        request = item.get('request')
        if not request:
            continue

        api_name = item.get('name', '未命名接口')
        method = request.get('method', 'GET').upper()
        url_path = _clean_url_path(request.get('url', ''))
        headers = _parse_headers(request.get('header', []))
        json_data, data = _parse_body(request.get('body', {}))

        api_definition = build_api_definition(
            name=api_name,
            method=method,
            url_path=url_path,
            headers=headers or None,
            json_data=json_data,
            data=data,
        )

        target_dir = target_base
        for part in folder_parts:
            target_dir = target_dir / generate_safe_dirname(part)

        filename_base = generate_safe_filename(api_name)
        file_path = resolve_unique_yaml_path(target_dir, filename_base)
        try:
            write_api_definition(api_definition, file_path)
            count += 1
        except Exception as e:
            log.error(f'❌ 生成接口契约失败 [{api_name}]: {e}')

    return count


def import_postman_file(postman_json_path: str | Path, target_module: str) -> int:
    """
    导入 Postman Collection (v2.1) JSON，生成 api/{target_module}/ 下 YAML 接口契约。

    :param postman_json_path: Postman JSON 路径
    :param target_module: 子系统目录名，如 hub、wms、rms
    :return: 成功生成的 YAML 数量
    """
    json_path = Path(postman_json_path)
    if not json_path.exists():
        log.error(f'Postman 文件不存在: {json_path}')
        return 0

    target_dir = path_mgr.api_dir / target_module
    target_dir.mkdir(parents=True, exist_ok=True)

    log.info(f'🔄 开始解析 Postman 文件: {json_path.name}')
    log.info(f'📂 目标生成目录: {target_dir}')

    try:
        with json_path.open(encoding='utf-8') as f:
            postman_data = json.load(f)
    except json.JSONDecodeError as e:
        log.error(f'Postman 文件格式不合法: {e}')
        return 0

    items = postman_data.get('item', [])
    if not items:
        log.warning('该 Postman 集合中没有找到任何接口。')
        return 0

    total_generated = _process_items(items, target_dir)
    log.info(f'🎉 Postman 导入完成！共生成 {total_generated} 个 YAML 接口契约积木。')
    return total_generated
