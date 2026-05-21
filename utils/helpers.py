from enum import Enum
from typing import Any


def get_enum_values(enum_class: type[Enum]) -> list[Any]:
    """
    获取枚举类中的所有 value 列表

    示例:
        values = get_enum_values(MethodType)
        # 返回: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
    """
    return [item.value for item in enum_class]


def get_enum_names(enum_class: type[Enum]) -> list[str]:
    """
    获取枚举类中的所有 key 名称列表 (扩展功能)

    示例:
        names = get_enum_names(MethodType)
        # 返回: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'] (取决于枚举定义的变量名)
    """
    return [item.name for item in enum_class]
