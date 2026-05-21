import re

from typing import Any

import jsonpath

from core.exceptions import ContextVariableError, RmsFrameworkError
from utils.logger import log

__all__ = ['extract_by_jsonpath', 'var_extractor']


def extract_by_jsonpath(data: dict | list, expr: str) -> Any:
    """
    根据 JSONPath 表达式从数据字典/列表中提取值

    :param data: 目标数据 (通常是 HTTP Response 的 json())
    :param expr: JSONPath 表达式，如 '$.data.order_id'
    :return: 提取到的真实值
    """
    # jsonpath 库查找失败会返回 False，查找成功返回列表
    result = jsonpath.jsonpath(data, expr)

    if result is False:
        log.error(f'提取失败: JSONPath [{expr}] 在响应数据中未匹配到任何内容。')
        raise RmsFrameworkError(f'JSONPath 取值失败: {expr}')

    # 通常接口提取都是提取单一明确的值，默认取匹配到的第一个
    extracted_value = result[0]
    log.debug(f'成功提取变量: [{expr}] -> {extracted_value}')

    return extracted_value


class VarExtractor:
    """上下文变量替换引擎。"""

    def __init__(self) -> None:
        self.full_var_re = re.compile(r'^\$([a-zA-Z_]\w*)$')
        self.inline_var_re = re.compile(r'\$([a-zA-Z_]\w*)')

    def vars_replace(self, target: Any, context_vars: dict[str, Any]) -> Any:
        """递归替换目标数据中的上下文变量。"""
        if isinstance(target, dict):
            return {k: self.vars_replace(v, context_vars) for k, v in target.items()}

        if isinstance(target, list):
            return [self.vars_replace(i, context_vars) for i in target]

        if isinstance(target, str):
            match = self.full_var_re.fullmatch(target)
            if match:
                return self._get_var_value(match.group(1), context_vars)

            if '$' in target:
                return self.inline_var_re.sub(lambda m: str(self._get_var_value(m.group(1), context_vars)), target)

        return target

    def _get_var_value(self, var_name: str, context_vars: dict[str, Any]) -> Any:
        if var_name not in context_vars:
            raise ContextVariableError(f'上下文变量不存在: ${var_name}')
        return context_vars[var_name]


var_extractor = VarExtractor()
