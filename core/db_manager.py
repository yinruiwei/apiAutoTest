import contextlib
import datetime
import decimal
import json

from typing import Any

import aiomysql

from config.settings import settings
from core.exceptions import DBConnectionError
from enums import QueryFetchType, SqlType
from utils.logger import log


class AsyncDBManager:
    def __init__(self):
        # 存放所有数据库连接池的字典: {"wms_db": pool_wms, "rms_db": pool_rms}
        self._pools: dict[str, aiomysql.Pool] = {}

    async def init_pools(self) -> None:
        """
        [连接层] 初始化所有数据库的异步连接池
        建议在框架启动的 hook (如 pytest_sessionstart) 中调用
        """
        for db_name, db_config in settings.databases.items():
            try:
                pool = await aiomysql.create_pool(
                    host=db_config.host,
                    port=db_config.port,
                    user=db_config.user,
                    password=db_config.password,
                    db=db_config.db_name,
                    charset='utf8mb4',
                    # 查询结果直接返回字典
                    cursorclass=aiomysql.DictCursor,
                    # 最小空闲连接数
                    minsize=1,
                    # 最大连接数（并发高时自动扩展）
                    maxsize=15,
                    autocommit=True,
                )
                self._pools[db_name] = pool
                log.info(f'数据库连接池初始化成功: [{db_name}] -> {db_config.host}:{db_config.port}')
            except Exception as e:
                log.error(f'数据库连接池初始化失败 [{db_name}]: {e}')
                raise DBConnectionError(f'无法连接数据库 {db_name}: {e}') from e

    async def close_pools(self) -> None:
        """[连接层] 销毁所有连接池"""
        for db_name, pool in self._pools.items():
            pool.close()
            await pool.wait_closed()
            log.info(f'数据库连接池已关闭: [{db_name}]')
        self._pools.clear()

    def _get_pool(self, db_name: str) -> aiomysql.Pool:
        """安全获取指定数据库的连接池"""
        pool = self._pools.get(db_name)
        if not pool:
            raise DBConnectionError(f"未找到名为 '{db_name}' 的数据库配置，请检查 env.yaml")
        return pool

    @staticmethod
    def _format_row(row: dict[str, Any]) -> None:
        """
        [数据处理] 将数据库中无法被 JSON 序列化的特殊类型进行转码
        """
        for k, v in row.items():
            if isinstance(v, decimal.Decimal):
                row[k] = float(v) if v % 1 else int(v)
            elif isinstance(v, datetime.datetime):
                row[k] = v.strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(v, datetime.date):
                row[k] = v.strftime('%Y-%m-%d')
            elif isinstance(v, str):
                # 尝试解析 JSON 格式的字符串
                with contextlib.suppress(ValueError):
                    row[k] = json.loads(v)

    async def query(self, db_name: str, sql: str, fetch: QueryFetchType = QueryFetchType.ALL) -> dict | list | None:
        """
        [执行层] DQL 查询操作 (SELECT)

        :param db_name: 目标数据库标识 (如 'rms_db')
        :param sql: SQL 语句
        :param fetch: 查询一条 (one) 还是全部 (all)
        """
        pool = self._get_pool(db_name)

        # async with 语法自动从池中借用连接，执行完毕后自动归还
        async with pool.acquire() as conn, conn.cursor() as cursor:
            try:
                await cursor.execute(sql)
                if fetch == QueryFetchType.ONE:
                    query_data = await cursor.fetchone()
                else:
                    query_data = await cursor.fetchall()
            except Exception as e:
                log.error(f'[{db_name}] 执行 SQL 失败: {sql} | 错误: {e}')
                raise DBConnectionError(f'SQL 查询异常: {e}') from e

        result_count = len(query_data) if isinstance(query_data, list) else 1 if query_data else 0
        log.info(f'[{db_name}] SQL 查询成功: {sql} | 结果数: {result_count}')

        if not query_data:
            return None

        # 格式化特殊类型数据
        if isinstance(query_data, dict):
            self._format_row(query_data)
            return query_data
        elif isinstance(query_data, list):
            for item in query_data:
                self._format_row(item)
            return query_data

    async def execute(self, db_name: str, sql: str) -> int:
        """
        [执行层] DML 执行操作 (INSERT/UPDATE/DELETE)

        :return: 影响的行数 (rowcount)
        """
        pool = self._get_pool(db_name)
        async with pool.acquire() as conn, conn.cursor() as cursor:
            try:
                rowcount = await cursor.execute(sql)
                await conn.commit()
                log.info(f'[{db_name}] 执行 SQL 成功: {sql} | 影响行数: {rowcount}')
                return rowcount
            except Exception as e:
                await conn.rollback()
                log.error(f'[{db_name}] 执行 SQL 失败回滚: {sql} | 错误: {e}')
                raise DBConnectionError(f'SQL 执行异常: {e}') from e

    async def run_sql(self, db_name: str, sql: str, fetch: QueryFetchType = QueryFetchType.ALL) -> Any:
        """
        [统一入口] 根据 SQL 的前缀自动路由到查询或执行逻辑
        """
        sql_upper = sql.strip().upper()
        if sql_upper.startswith(SqlType.select):
            return await self.query(db_name, sql, fetch)
        elif sql_upper.startswith((SqlType.insert, SqlType.update, SqlType.delete)):
            return await self.execute(db_name, sql)
        else:
            raise DBConnectionError(f'不支持的 SQL 命令类型: {sql}')


# 全局单例对象
db_mgr = AsyncDBManager()
