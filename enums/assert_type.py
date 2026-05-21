from enum import StrEnum, unique


@unique
class AssertType(StrEnum):
    """YAML 场景里 assert_type 字段与 asserter 的对应关系；值为写入 YAML 的字符串。"""

    #: 实际值 == 期望值
    equal = 'eq'

    #: 实际值 != 期望值
    not_equal = 'not_eq'

    #: 实际值 > 期望值（数值比较）
    greater_than = 'gt'

    #: 实际值 >= 期望值
    greater_than_or_equal = 'ge'

    #: 实际值 < 期望值
    less_than = 'lt'

    #: 实际值 <= 期望值
    less_than_or_equal = 'le'

    #: str(实际) == str(期望)，弱类型统一成字符串再比
    string_equal = 'str_eq'

    #: len(实际) == int(期望)
    length_equal = 'len_eq'

    #: len(实际) != int(期望)
    not_length_equal = 'not_len_eq'

    #: len(实际) < int(期望)
    length_less_than = 'len_lt'

    #: len(实际) <= int(期望)
    length_less_than_or_equal = 'len_le'

    #: len(实际) > int(期望)
    length_greater_than = 'len_gt'

    #: len(实际) >= int(期望)
    length_greater_than_or_equal = 'len_ge'

    #: 期望值 in 实际值（子串 / 元素包含）
    contains = 'contains'

    #: 期望值 not in 实际值
    not_contains = 'not_contains'

    #: str(实际).startswith(str(期望))
    startswith = 'startswith'  # type: ignore

    #: str(实际).endswith(str(期望))
    endswith = 'endswith'  # type: ignore

    #: 正则 expect 匹配 actual（re.search）
    regex = 'regex'

    #: 以 expect 为 JSON Schema 校验 actual 整体结构
    jsonschema = 'jsonschema'
