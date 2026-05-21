import re
from typing import Any

from jsonschema import validate
from jsonschema.exceptions import ValidationError as SchemaValidationError

from core.exceptions import RmsTestFailure
from utils.logger import log

__all__ = ['asserter']


class Asserter:
    """
    核心断言中心
    放弃 eval()，使用纯 Python 原生语法与模式匹配
    """

    @classmethod
    def execute(
        cls, assert_type: str, actual_value: Any, expect_value: Any, message: str = '', jsonpath: str = ''
    ) -> None:
        """
        分发执行断言

        :param assert_type: 断言类型枚举值 (如 eq, contains, jsonschema)
        :param actual_value: 实际提取到的值
        :param expect_value: 期望值 (或正则pattern、jsonschema字典)
        :param message: 自定义错误信息
        :param jsonpath: 用于日志打印的路径来源
        """
        try:
            # 使用 match-case 匹配
            match assert_type:
                # 1. 基础等值断言
                case 'eq':
                    assert actual_value == expect_value
                case 'not_eq':
                    assert actual_value != expect_value
                case 'str_eq':
                    assert str(actual_value) == str(expect_value)

                # 2. 数值大小断言
                case 'gt':
                    assert actual_value > expect_value
                case 'ge':
                    assert actual_value >= expect_value
                case 'lt':
                    assert actual_value < expect_value
                case 'le':
                    assert actual_value <= expect_value

                # 3. 包含关系断言
                case 'contains':
                    assert expect_value in actual_value
                case 'not_contains':
                    assert expect_value not in actual_value
                case 'startswith':
                    assert str(actual_value).startswith(str(expect_value))
                case 'endswith':
                    assert str(actual_value).endswith(str(expect_value))

                # 4. 长度断言
                case 'len_eq':
                    assert len(actual_value) == int(expect_value)
                case 'len_gt':
                    assert len(actual_value) > int(expect_value)
                case 'len_lt':
                    assert len(actual_value) < int(expect_value)

                # 5. 高阶断言: 正则匹配
                case 'regex':
                    # expect_value 此时应当是一个正则表达式字符串
                    assert re.search(str(expect_value), str(actual_value)) is not None

                # 6. 高阶断言: JSON Schema 校验
                case 'jsonschema':
                    # expect_value 此时应当是一个 JSON Schema 字典
                    if not isinstance(expect_value, dict):
                        raise RmsTestFailure('JSONSchema 断言失败: 期望值必须是有效的 Schema 字典')
                    try:
                        validate(instance=actual_value, schema=expect_value)
                    except SchemaValidationError as e:
                        raise AssertionError(f'Schema校验不通过: {e.message}')

                case _:
                    raise ValueError(f'不受支持的断言类型: {assert_type}')

            log.info(f'✅ 断言通过: [{jsonpath}] ({actual_value}) {assert_type} {expect_value}')

        except AssertionError as e:
            err_msg = f'❌ 断言失败! 路径: [{jsonpath}]\n   实际值: {actual_value} (type: {type(actual_value).__name__})\n   预期值: {expect_value} (type: {type(expect_value).__name__})\n   规则: {assert_type}'

            # 拼接自定义 message 或 原生 AssertionError 的内容 (如 jsonschema 的错误)
            extra_msg = message or str(e)
            if extra_msg:
                err_msg += f'\n   详情: {extra_msg}'

            log.error(err_msg)
            raise RmsTestFailure(err_msg)

        except TypeError as e:
            err_msg = f'⚠️ 断言类型冲突! 路径: [{jsonpath}]\n   无法使用 [{assert_type}] 比较 实际值({type(actual_value).__name__}) 和 期望值({type(expect_value).__name__})'
            log.error(err_msg)
            raise RmsTestFailure(err_msg) from e


asserter = Asserter()