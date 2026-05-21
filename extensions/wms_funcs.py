from core.cache_mgr import cache
from core.exceptions import RmsFrameworkError


def call_login_api() -> str:
    """调用 WMS 登录接口获取 token。"""
    raise RmsFrameworkError('WMS token 获取逻辑尚未实现，请在 extensions/wms_funcs.py 中补充登录接口调用')


async def get_wms_token():
    # 1. 尝试从全局 Redis 拿
    token = await cache.get('wms_global_token')
    if token:
        return token

    # 2. 如果没有，再去调用真实登录接口
    new_token = call_login_api()

    # 3. 存入 Redis，供其他并发进程使用
    await cache.set('wms_global_token', new_token, timeout=7200)
    return new_token
