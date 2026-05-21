from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from enums import AssertType
from enums.request import MethodType


# 基础组件模型 (公用)
class RequestModel(BaseModel):
    """HTTP 请求参数模型"""

    method: MethodType  # 强制校验必须是 GET/POST/PUT/DELETE 等
    url: str  # 接口路径，如 /api/v1/login
    params: dict[str, Any] | None = None
    headers: dict[str, str] | None = None
    json_data: dict[str, Any] | list | None = Field(None, alias='json')  # 兼容 YAML 中的 json 关键字
    data: dict[str, Any] | str | None = None


class ExtractModel(BaseModel):
    """变量提取模型"""

    var_name: str  # 提取后的变量名，如 order_id
    jsonpath: str  # 提取规则，如 $.data.id


class ValidatorModel(BaseModel):
    """断言校验模型"""

    assert_type: AssertType  # 断言类型，如 eq, contains (自动校验枚举)
    jsonpath: str  # 实际结果的提取路径，如 $.code
    expect_value: Any  # 预期结果
    message: str | None = None  # 自定义报错信息


# 【API 定义层】模型 (针对 api/ 目录下的 yaml)
class ApiDefinitionModel(BaseModel):
    """单个 API 接口的积木块定义"""

    # 严格模式：严禁在 YAML 中乱写多余字段
    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    name: str
    request: RequestModel
    extract: list[ExtractModel] | None = None
    validators: list[ValidatorModel] | None = Field(None, alias='validate')


# 【业务场景层】模型 (针对 testcases/ 目录下的 yaml)
class StepModel(BaseModel):
    """业务场景中的单个步骤"""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    name: str
    api: str  # 引用的 api 积木路径，如 "api/wms/login.yaml"
    variables: dict[str, Any] | None = None  # 本次请求注入的动态变量
    extract: list[ExtractModel] | None = None  # 场景级特定的额外提取
    validators: list[ValidatorModel] | None = Field(None, alias='validate')  # 场景级特定的额外断言
    setup_hooks: list[str] | None = None  # 前置钩子函数名
    teardown_hooks: list[str] | None = None  # 后置钩子函数名


class ScenarioModel(BaseModel):
    """完整的业务场景测试用例"""

    model_config = ConfigDict(extra='forbid')

    name: str
    config: dict[str, Any] | None = None  # 场景级配置 (预留扩展)
    teststeps: list[StepModel]
