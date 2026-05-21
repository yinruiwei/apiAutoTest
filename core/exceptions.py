class RmsBaseException(Exception):
    """基类"""
    pass


class RmsTestFailure(AssertionError):
    """
    [Failure] 业务断言失败类
    ⚠️ 注意：必须继承自 AssertionError！
    这样在 Pytest 和 Allure 报告中，才会被正确渲染为红色的 'Failed' (用例失败/发现Bug)，
    而不是黄色的 'Broken' (环境异常/代码报错)。
    """
    pass


class RmsFrameworkError(RmsBaseException):
    """
    [Error] 框架运行错误类
    代表环境、数据、配置或脚本本身出错，导致用例无法继续执行。
    在报告中会渲染为黄色的 'Broken'。
    """
    pass


# 具体的 Error 细分 (全部继承自 RmsFrameworkError)
class YamlFormatError(RmsFrameworkError):
    """YAML 文件格式或语法解析错误"""
    pass


class EnvConfigError(RmsFrameworkError):
    """环境配置 (.env 或 env.test.yaml) 缺失或错误"""
    pass


class DBConnectionError(RmsFrameworkError):
    """数据库连接或查询异常"""
    pass


class ContextVariableError(RmsFrameworkError):
    """上下文变量提取、替换或传递失败"""
    pass


class SystemAuthError(RmsFrameworkError):
    """系统鉴权失败 (如：Token 获取失败或已过期)"""
    pass


class RequestConfigError(RmsFrameworkError):
    """请求参数组装错误 (如 URL 不合法、Method 不受支持)"""
    pass