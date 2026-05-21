from typing import Any

from pydantic import ValidationError

from core.exceptions import YamlFormatError
from core.models import ApiDefinitionModel, ScenarioModel

from utils.file_manage.path_manager import path_mgr
from utils.file_manage.yaml_handler import read_yaml
from utils.parsing_manage.hook_executor import hook_executor
from utils.parsing_manage.pydantic_error_formatter import format_pydantic_error
from utils.parsing_manage.variable_extractor import var_extractor


class YamlParser:
    """YAML 加载与数据流水线统筹中心"""

    @classmethod
    def load_scenario(cls, file_path: str) -> ScenarioModel:
        full_path = path_mgr.testcases_dir / file_path
        data = read_yaml(full_path)
        try:
            return ScenarioModel(**data)
        except ValidationError as e:
            raise YamlFormatError(f'场景文件语法校验失败 [{file_path}]: {format_pydantic_error(e)}') from e

    @classmethod
    def load_api_block(cls, api_reference: str) -> ApiDefinitionModel:
        full_path = path_mgr.project_dir / api_reference
        data = read_yaml(full_path)
        try:
            return ApiDefinitionModel(**data)
        except ValidationError as e:
            raise YamlFormatError(f'API 文件语法校验失败 [{api_reference}]: {format_pydantic_error(e)}') from e

    @classmethod
    def render_request_data(cls, raw_data: dict[str, Any], context_vars: dict[str, Any]) -> dict[str, Any]:
        """
        渲染流水线：先执行 Hook 函数，再替换变量
        """
        # 第一步：计算并替换所有的 ${func()}
        hook_rendered = hook_executor.hook_func_value_replace(raw_data)

        # 第二步：将剩余的 $var 替换为上下文真实数据
        final_data = var_extractor.vars_replace(hook_rendered, context_vars)

        return final_data


parser = YamlParser()
