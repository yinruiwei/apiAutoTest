import time

from typing import Any

import httpx

from core.exceptions import RmsFrameworkError
from core.models import RequestModel
from utils.logger import log

__all__ = ['api_client']

# 未在 YAML 中指定 User-Agent 时使用（模拟 Edge / Chromium）
# TODO: 后续需要将 User-Agent 提取到配置文件
DEFAULT_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0'
)


class AsyncApiClient:
    """
    异步高并发 HTTP 客户端
    维护全局唯一的 AsyncClient 实例，复用 TCP 连接器 (Connection Pooling)
    """

    def __init__(self):
        # 初始化全局连接池，关闭 SSL 校验以防内部测试环境报证书错误
        self.client = httpx.AsyncClient(
            verify=False,
            # 默认全局 15 秒超时
            timeout=httpx.Timeout(15.0),
            limits=httpx.Limits(max_keepalive_connections=50, max_connections=100),
        )

    async def close(self) -> None:
        """关闭客户端，释放连接池资源 (供 conftest.py 在测试结束时调用)"""
        await self.client.aclose()
        log.info('HTTPX 异步客户端连接池已安全释放')

    async def send_request(self, rendered_request: dict[str, Any], base_url: str = '') -> httpx.Response:
        """
        发送网络请求

        :param rendered_request: 经过 parser.py 渲染过真实变量的请求字典
        :param base_url: 系统的 Base URL (如 http://test-wms.company.com)
        :return: httpx.Response 对象
        """
        # 1. 经过 Parser 处理后，再次用 Pydantic 校验一次，确保传给 httpx 的参数万无一失
        try:
            req_obj = RequestModel(**rendered_request)
        except Exception as e:
            raise RmsFrameworkError(f'请求参数组装后格式异常: {e}') from e

        # 2. URL 拼接 (处理绝对路径与相对路径)
        url = req_obj.url
        if not url.startswith('http'):
            # 去除首尾的斜杠防止拼接出 http://xxx.com//api/v1 这种双斜杠
            url = f'{base_url.rstrip("/")}/{url.lstrip("/")}'
        if not url.startswith(('http://', 'https://')):
            raise RmsFrameworkError(
                f'请求 URL 无效（缺少协议）: {url!r}。相对路径必须在 send_request 中传入非空的 base_url。'
            )

        # 3. 提取 Headers 并设置默认 User-Agent
        headers = dict(req_obj.headers) if req_obj.headers else {}
        if 'user-agent' not in {k.lower() for k in headers}:
            headers['User-Agent'] = DEFAULT_USER_AGENT

        # 4. 组装给 httpx 发送的 kwargs
        # method.value 是因为 RequestModel 中 method 被强制校验为了 enums/request/method.py/MethodType 枚举
        req_kwargs = {
            'method': req_obj.method.value,
            'url': url,
            'headers': headers,
            'params': req_obj.params,
        }

        # 5. 处理 Body 类型
        # 如果 YAML 里写了 json: xxx，Pydantic 会将它映射到 req_obj.json_data，httpx 会自动加上 application/json
        if req_obj.json_data is not None:
            req_kwargs['json'] = req_obj.json_data
        elif req_obj.data is not None:
            req_kwargs['data'] = req_obj.data

        # 清理字典中为 None 的键，防止 httpx 报错
        req_kwargs = {k: v for k, v in req_kwargs.items() if v is not None}

        # 6. 日志录制
        log.info(f'🚀 [Req] {req_kwargs["method"]} {req_kwargs["url"]}')
        log.debug(f'📤 [Headers] {headers}')
        if req_obj.params:
            log.debug(f'📤 [Params] {req_obj.params}')
        if req_obj.json_data or req_obj.data:
            log.debug(f'📤 [Body] {req_obj.json_data or req_obj.data}')

        # 7. 执行真实请求
        start_time = time.time()
        try:
            response = await self.client.request(**req_kwargs)
            elapsed = time.time() - start_time

            # 8. 接收后的日志录制
            log.info(f'📥 [Res] Status: {response.status_code} | Time: {elapsed:.3f}s')

            # 尝试解析响应体用于日志打印 (截断过长的 HTML)
            try:
                log_body = response.json()
            except ValueError:
                log_body = response.text[:500] + ('...' if len(response.text) > 500 else '')

            log.debug(f'📄 [Res Body] {log_body}')

            return response

        except httpx.RequestError as e:
            log.error(f'❌ [Req Failed] 接口请求崩溃: {e}')
            raise RmsFrameworkError(f'HTTPX 请求执行异常: {e}') from e


# 暴露全局单例，供执行层直接调用 api_client.send_request()
api_client = AsyncApiClient()
