"""Apifox 项目导出 JSON → 框架 API 积木 YAML。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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

__all__ = ['import_apifox_file']


def _build_schema_index(apifox_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """schemaCollection 中 id → jsonSchema 根对象。"""
    index: dict[str, dict[str, Any]] = {}
    for collection in apifox_data.get('schemaCollection', []):
        for item in collection.get('items', []):
            schema_id = item.get('id')
            root = (item.get('schema') or {}).get('jsonSchema')
            if schema_id and isinstance(root, dict):
                index[schema_id] = root
    return index


def _resolve_schema(schema_ref: Any, schema_index: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    if not isinstance(schema_ref, dict):
        return None
    ref = schema_ref.get('$ref')
    if ref and ref in schema_index:
        return _deref_schema(schema_index[ref], schema_index)
    if schema_ref.get('type') or schema_ref.get('properties'):
        return _deref_schema(schema_ref, schema_index)
    return None


def _deref_schema(schema: dict[str, Any], schema_index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """展开 Schema 中的 $ref（含 properties / items 嵌套引用）。"""
    ref = schema.get('$ref')
    if ref and ref in schema_index:
        return _deref_schema(schema_index[ref], schema_index)

    result = dict(schema)
    props = result.get('properties')
    if isinstance(props, dict):
        result['properties'] = {k: _deref_schema(v, schema_index) if isinstance(v, dict) else v for k, v in props.items()}
    items = result.get('items')
    if isinstance(items, dict):
        result['items'] = _deref_schema(items, schema_index)
    return result


def _schema_to_request_template(schema: dict[str, Any] | None) -> dict[str, Any] | list[Any] | None:
    """
    将 JSON Schema 转为可编辑的请求体模板。
    叶子字符串字段使用 $字段名，便于场景 variables 注入。
    """
    if not schema or not isinstance(schema, dict):
        return None

    schema_type = schema.get('type')
    if schema_type == 'object':
        props = schema.get('properties') or {}
        result: dict[str, Any] = {}
        for key, sub in props.items():
            if isinstance(sub, dict) and sub.get('type') in ('object', 'array'):
                nested = _schema_to_request_template(sub)
                result[key] = nested if nested is not None else {}
            elif isinstance(sub, dict) and sub.get('type') in ('integer', 'number'):
                result[key] = 0
            elif isinstance(sub, dict) and sub.get('type') == 'boolean':
                result[key] = False
            else:
                result[key] = f'${key}'
        return result

    if schema_type == 'array':
        items = schema.get('items') or {}
        if isinstance(items, dict) and items.get('type') == 'string':
            return ['$item']
        child = _schema_to_request_template(items if isinstance(items, dict) else None)
        if child is not None:
            return [child]
        return []

    return None


def _parse_apifox_headers(parameters: dict[str, Any] | None) -> dict[str, str]:
    headers: dict[str, str] = {}
    if not parameters:
        return headers
    for h in parameters.get('header', []):
        if h.get('disabled'):
            continue
        key = h.get('name') or h.get('key')
        value = h.get('value') or h.get('example') or ''
        if key:
            headers[str(key)] = replace_template_vars_in_str(str(value))
    content_type = 'application/json'
    if content_type.lower() not in {k.lower() for k in headers}:
        headers.setdefault('Content-Type', content_type)
    return headers


def _parse_apifox_query(parameters: dict[str, Any] | None) -> dict[str, str] | None:
    if not parameters:
        return None
    query: dict[str, str] = {}
    for q in parameters.get('query', []):
        if q.get('disabled'):
            continue
        key = q.get('name') or q.get('key')
        value = q.get('value') or q.get('example') or ''
        if key:
            query[str(key)] = replace_template_vars_in_str(str(value))
    return query or None


def _process_apifox_items(
    items: list[dict[str, Any]],
    target_base: Path,
    schema_index: dict[str, dict[str, Any]],
    folder_parts: tuple[str, ...] = (),
) -> int:
    count = 0
    for item in items:
        nested = item.get('items')
        if nested:
            sub_parts = folder_parts
            folder_name = item.get('name')
            if folder_name and folder_name not in ('根目录',):
                sub_parts = folder_parts + (folder_name,)
            count += _process_apifox_items(nested, target_base, schema_index, sub_parts)
            continue

        api = item.get('api')
        if not api or api.get('type') != 'http':
            continue

        api_name = item.get('name') or api.get('operationId') or '未命名接口'
        method = str(api.get('method', 'GET')).upper()
        url_path = str(api.get('path') or '/')
        if not url_path.startswith('/'):
            url_path = '/' + url_path

        parameters = api.get('parameters') or {}
        headers = _parse_apifox_headers(parameters)
        params = _parse_apifox_query(parameters)

        json_data = None
        request_body = api.get('requestBody') or {}
        if request_body.get('type', '').startswith('application/json'):
            body_schema = _resolve_schema(request_body.get('jsonSchema'), schema_index)
            json_data = _schema_to_request_template(body_schema)
            if json_data is not None:
                json_data = replace_template_vars_in_dict(json_data)

        api_definition = build_api_definition(
            name=api_name,
            method=method,
            url_path=url_path,
            headers=headers or None,
            json_data=json_data,
            params=params,
        )

        target_dir = target_base
        for part in folder_parts:
            if part in ('根目录',):
                continue
            target_dir = target_dir / generate_safe_dirname(part)

        filename_base = generate_safe_filename(api_name)
        file_path = resolve_unique_yaml_path(target_dir, filename_base)
        try:
            write_api_definition(api_definition, file_path)
            count += 1
        except Exception as e:
            log.error(f'❌ 生成接口契约失败 [{api_name}]: {e}')

    return count


def import_apifox_file(apifox_json_path: str | Path, target_module: str) -> int:
    """
    导入 Apifox 导出的项目 JSON，生成 api/{target_module}/ 下 YAML 接口契约。

    :param apifox_json_path: Apifox 项目 JSON 路径
    :param target_module: 子系统目录名，如 hub、wms、rms
    :return: 成功生成的 YAML 数量
    """
    json_path = Path(apifox_json_path)
    if not json_path.exists():
        log.error(f'Apifox 文件不存在: {json_path}')
        return 0

    target_dir = path_mgr.api_dir / target_module
    target_dir.mkdir(parents=True, exist_ok=True)

    log.info(f'🔄 开始解析 Apifox 文件: {json_path.name}')
    log.info(f'📂 目标生成目录: {target_dir}')

    try:
        with json_path.open(encoding='utf-8') as f:
            apifox_data = json.load(f)
    except json.JSONDecodeError as e:
        log.error(f'Apifox 文件格式不合法: {e}')
        return 0

    schema_index = _build_schema_index(apifox_data)
    total = 0
    for collection in apifox_data.get('apiCollection', []):
        items = collection.get('items', [])
        if items:
            total += _process_apifox_items(items, target_dir, schema_index)

    log.info(f'🎉 Apifox 导入完成！共生成 {total} 个 YAML 接口契约积木。')
    return total
