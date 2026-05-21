import os

from typing import Any

from cache3 import Cache
from redis.asyncio import Redis
from redis.exceptions import AuthenticationError, TimeoutError

from config.settings import settings
from core.exceptions import RmsFrameworkError
from utils.logger import log


class AsyncCacheManager:
    """cache3 或 Redis"""

    def __init__(self, prefix: str = 'rms') -> None:
        self.prefix = prefix
        # 核心开关：由环境变量决定走哪个引擎，默认 local
        self.cache_type = os.getenv('CACHE_TYPE', 'local').lower()

        if self.cache_type == 'redis':
            self._redis = Redis(
                host=settings.redis.host,
                port=settings.redis.port,
                password=settings.redis.password,
                db=settings.redis.db,
                socket_timeout=settings.redis.timeout,
                decode_responses=True,
            )
            self._local_cache = None
            log.info(f'初始化缓存管理器: [Redis] -> {settings.redis.host}')
        else:
            self._redis = None
            self._local_cache = Cache('rms_local_cache')
            log.info('初始化缓存管理器: [Local Cache3]')

    def _build_key(self, key: str) -> str:
        return f'{self.prefix}:{key}'

    async def init_check(self) -> None:
        """启动时检查连接。只适用于Redis。"""
        if self.cache_type == 'redis':
            try:
                await self._redis.ping()
                log.info('Redis 异步缓存连接成功')
            except TimeoutError as exc:
                raise RmsFrameworkError('Redis 缓存连接超时') from exc
            except AuthenticationError as exc:
                raise RmsFrameworkError('Redis 缓存认证失败') from exc
            except Exception as exc:
                raise RmsFrameworkError(f'Redis 缓存连接失败: {exc}') from exc

    async def get(self, key: str, logging: bool = True) -> Any:
        full_key = self._build_key(key)

        if self.cache_type == 'redis':
            data = await self._redis.get(full_key)
        else:
            data = self._local_cache.get(full_key)

        if logging:
            if data is not None:
                log.info(f'获取缓存变量成功: {full_key}')
            else:
                log.warning(f'获取缓存变量失败，未找到密钥: {full_key}')
        return data

    async def set(self, key: str, value: Any, timeout: int | None = None) -> bool:
        full_key = self._build_key(key)

        if self.cache_type == 'redis':
            result = await self._redis.set(full_key, value, ex=timeout)
        else:
            result = self._local_cache.set(full_key, value, timeout=timeout)

        if result:
            log.info(f'设置缓存变量: {full_key}={value} (TTL: {timeout}s) via {self.cache_type}')
        return bool(result)

    async def delete(self, key: str) -> bool:
        full_key = self._build_key(key)

        if self.cache_type == 'redis':
            result = await self._redis.delete(full_key)
        else:
            result = self._local_cache.delete(full_key)

        if result:
            log.info(f'已删除缓存变量: {full_key} via {self.cache_type}')
        return bool(result)

    async def clear_all(self) -> None:
        """安全地只清除与项目前缀相符的密钥。"""
        if self.cache_type == 'redis':
            count = 0
            async for key in self._redis.scan_iter(match=f'{self.prefix}:*'):
                await self._redis.delete(key)
                count += 1
            log.info(f'清除 {count} 带有前缀的 Redis 缓存变量: {self.prefix}')
        else:
            self._local_cache.clear()
            log.info('清除了所有本地缓存3变量')


# 暴露全局唯一单例
cache = AsyncCacheManager()
