import logging
import sys

from loguru import logger

from utils.file_manage.path_manager import path_mgr

__all__ = ['log']


class InterceptHandler(logging.Handler):
    """
    拦截标准 logging 日志,将其路由到 loguru。
    核心作用:让 requests, pymysql, dbutils 等第三方库的内置日志,也能写入到我们的 rms_test.log 文件中,
    而不是零散地打印在控制台。
    """

    def emit(self, record: logging.LogRecord) -> None:
        # 获取 loguru 对应的日志级别
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 向上追溯,寻找调用者真实的所在文件和行号,而不是全指向 logging 模块
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def init_logger() -> logger.__class__:
    """初始化并配置全局日志系统"""

    # 清除 loguru 默认的配置
    logger.remove()

    # 定义日志格式
    log_format = (
        '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | '
        '<level>{level: <8}</level> | '
        '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - '
        '<level>{message}</level>'
    )

    # 配置控制台输出
    logger.add(
        sys.stdout,
        format=log_format,
        level='DEBUG',
        enqueue=False,
    )

    # 配置全量日志文件输出
    log_file_path = path_mgr.log_dir / 'rms_test_{time:YYYY-MM-DD}.log'
    logger.add(
        log_file_path,
        format=log_format,
        level='DEBUG',
        rotation='00:00',  # 每天零点自动切割生成新文件
        retention='15 days',  # 历史日志保留 15 天
        encoding='utf-8',
        enqueue=False,
        backtrace=True,  # 发生异常时,展示完整的追溯堆栈
        diagnose=True,  # 展示发生异常时的具体变量值
    )

    # ERROR 级别的日志文件
    error_file_path = path_mgr.log_dir / 'rms_error_{time:YYYY-MM-DD}.log'
    logger.add(
        error_file_path,
        format=log_format,
        level='ERROR',
        rotation='00:00',
        retention='30 days',
        encoding='utf-8',
        enqueue=False,
    )

    # 接管 Python 标准 logging 的日志
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # 屏蔽第三方库的 DEBUG 日志
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('faker').setLevel(logging.WARNING)

    return logger


# 全局单例
log = init_logger()
