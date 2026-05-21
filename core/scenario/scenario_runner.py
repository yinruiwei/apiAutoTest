import contextlib
import copy
import json
from typing import Any

import allure
import httpx

from config.settings import settings
from core.asserter import asserter
from core.client import api_client
from core.exceptions import RmsFrameworkError
from core.models import ScenarioModel, StepModel
from core.parser import parser
from utils.logger import log
from utils.parsing_manage.variable_extractor import extract_by_jsonpath

__all__ = ['ScenarioRunner']


def _base_url_for_api_reference(api_reference: str) -> str:
    """
    根据 api 积木路径解析宿主 Base URL，例如 api/wms/login.yaml -> settings.base_urls.wms。
    """
    norm = api_reference.replace('\\', '/').strip('/')
    parts = [p for p in norm.split('/') if p]
    if len(parts) >= 2 and parts[0].lower() == 'api':
        system_key = parts[1].lower()
        base_urls = settings.base_urls
        url = getattr(base_urls, system_key, None)
        if isinstance(url, str) and url.strip():
            return url.strip()
    raise RmsFrameworkError(
        f'无法从 API 引用 [{api_reference}] 解析 base_url，'
        '请使用 api/wms/、api/rms/、api/pda/ 或 api/hub/ 前缀，并确保 env 配置里 base_urls 对应项非空。'
    )


def _effective_request_url(rendered_request: dict[str, Any], base_url: str) -> str:
    url = str(rendered_request.get('url') or '')
    if url.startswith(('http://', 'https://')):
        return url
    return f'{base_url.rstrip("/")}/{url.lstrip("/")}'


def _redact_headers(headers: dict[str, Any]) -> dict[str, Any]:
    """附件中脱敏鉴权类 Header，避免 Token 进报告。"""
    out: dict[str, Any] = {}
    for k, v in headers.items():
        lk = k.lower()
        if lk in ('authorization', 'token', 'cookie', 'x-auth-token', 'x-api-key'):
            out[k] = '***'
        else:
            out[k] = v
    return out


def _request_for_attachment(
    rendered_request: dict[str, Any], base_url: str, api_ref: str
) -> dict[str, Any]:
    """构造可 JSON 序列化的请求快照（枚举等用 default=str）。"""
    snap = copy.deepcopy(rendered_request)
    if isinstance(snap.get('headers'), dict):
        snap['headers'] = _redact_headers(snap['headers'])
    snap['_api_ref'] = api_ref
    snap['_url'] = _effective_request_url(rendered_request, base_url)
    return snap


def _json_attachment_payload(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


def _response_for_attachment(response: httpx.Response, res_json: Any) -> dict[str, Any]:
    """Allure 附件用：HTTP 状态 + 解析后的响应体（与 assert 使用同一对象）。"""
    return {
        'status_code': response.status_code,
        'body': res_json,
    }


class ScenarioRunner:
    """
    业务场景执行引擎 (统筹上下文变量、网络请求与断言提取)
    每个场景实例化一个 Runner，保证并发安全，处理 Redis 数据污染。

    每个 flow_yaml 里面的 teststeps 的步骤视为一条「小用例」：在 Allure 的测试步骤内附加本步 HTTP 请求参数与响应体，
    便于与流程拆分后的逐步排查对齐。
    """

    def __init__(self):
        # 用例级别的局部生命周期变量
        self.context_vars: dict[str, Any] = {}

    def apply_scenario_config_variables(self, scenario: ScenarioModel) -> None:
        """每个流程第一步前调用：清空并注入 YAML config.variables。"""
        self.context_vars.clear()
        if scenario.config and 'variables' in scenario.config:
            self.context_vars.update(scenario.config['variables'])

    async def run(self, scenario: ScenarioModel):
        """执行整个业务场景"""
        log.info(f'▶️ 开始执行场景: {scenario.name}')

        self.apply_scenario_config_variables(scenario)

        for step in scenario.teststeps:
            await self._run_step(step, wrap_allure_step=True)

    async def run_single_step(self, scenario: ScenarioModel, step_index: int) -> None:
        """仅执行场景中的某一「步」（与 run 共享同一 Runner 实例时可串联上下文）。"""
        step = scenario.teststeps[step_index]
        log.info(f'▶️ 场景 [{scenario.name}] 第 {step_index + 1} 步: {step.name}')
        await self._run_step(step, wrap_allure_step=False)

    async def _run_step(self, step: StepModel, *, wrap_allure_step: bool) -> None:
        """
        执行单个测试步骤。
        wrap_allure_step=True：整条流程在一个 Pytest 用例内时，再套一层 allure.step。
        wrap_allure_step=False：每步已是独立 Pytest 用例时，附件挂在用例根下，避免重复嵌套。
        """
        step_ctx = contextlib.nullcontext()
        if wrap_allure_step:
            step_ctx = allure.step(step.name)

        with step_ctx:
            log.info(f'👉 步骤: {step.name}')

            # 1. 注入当前步骤特有的变量到上下文中 (覆盖同名旧变量)
            if step.variables:
                rendered_vars = parser.render_request_data(step.variables, self.context_vars)
                self.context_vars.update(rendered_vars)

            # 2. 读取 API 底层积木
            api_def = parser.load_api_block(step.api)

            # 3. 组装并渲染真正的 HTTP 请求参数
            raw_request_dict = api_def.request.model_dump(by_alias=True, exclude_none=True)
            rendered_request = parser.render_request_data(raw_request_dict, self.context_vars)

            # 4. 发送异步 HTTP 请求（按 api 文件路径选择 WMS/RMS/PDA 的 base_url）
            base_url = _base_url_for_api_reference(step.api)
            response = await api_client.send_request(rendered_request, base_url=base_url)

            try:
                res_json = response.json()
            except ValueError:
                res_json = {'_raw_text': response.text}

            # 本步「小用例」：展示请求 / 响应（断言失败时也已生成附件）
            req_snap = _request_for_attachment(rendered_request, base_url, step.api)
            allure.attach(
                _json_attachment_payload(req_snap),
                name='请求参数',
                attachment_type=allure.attachment_type.JSON,
            )
            allure.attach(
                _json_attachment_payload(_response_for_attachment(response, res_json)),
                name='响应结果',
                attachment_type=allure.attachment_type.JSON,
            )

            # 5. 执行业务断言 (Validate)
            validators = (api_def.validators or []) + (step.validators or [])
            if validators:
                self._validate_data(res_json, validators)

            # 6. 执行参数提取 (Extract)
            extractors = (api_def.extract or []) + (step.extract or [])
            if extractors:
                for ext in extractors:
                    value = extract_by_jsonpath(res_json, ext.jsonpath)
                    self.context_vars[ext.var_name] = value
                    log.info(f'📥 提取变量: [{ext.var_name}] = {value}')

    def _validate_data(self, res_json: Any, validators: list):
        """
        断言执行器 (依托于 core.asserter)
        """
        for v in validators:
            # 1. 取实际值
            # 注意：如果是全量 jsonschema 校验，jsonpath 可以写 "$" 表示整个响应体
            actual_value = extract_by_jsonpath(res_json, v.jsonpath)

            # 2. 取期望值并渲染 (支持变量替换)
            expect_value = parser.render_request_data(v.expect_value, self.context_vars)

            # 兼容处理断言类型枚举
            assert_method = v.assert_type.value if hasattr(v.assert_type, 'value') else v.assert_type

            # 3. 断言中心
            asserter.execute(
                assert_type=assert_method,
                actual_value=actual_value,
                expect_value=expect_value,
                message=v.message,
                jsonpath=v.jsonpath,
            )
