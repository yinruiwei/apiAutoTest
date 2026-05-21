import re

from typing import Any

# 预先导入允许被 YAML 调用的自定义扩展函数库
import extensions.common_funcs
import extensions.pda_funcs
import extensions.rms_funcs
import extensions.wms_funcs

from config.settings import settings
from core.exceptions import ContextVariableError
from utils.logger import log

__all__ = ['hook_executor']


class HookExecutor:
    """独立的 Hook 函数执行引擎"""

    def __init__(self):
        # 匹配完整替换: ${generate_id()}
        self.func_re = re.compile(r'^\$\{([a-zA-Z_]\w*\([^)]*\))\}$')
        # 匹配内联替换: PREFIX_${generate_id()}_SUFFIX
        self.inline_func_re = re.compile(r'\$\{([a-zA-Z_]\w*\([^)]*\))\}')

        # 构建安全沙箱：只允许执行暴露的函数，屏蔽系统级危险函数 (如 os.system)
        self._safe_env = self._build_safe_env()

    def _build_safe_env(self) -> dict[str, Any]:
        """构建安全的函数执行上下文"""
        env = {'__builtins__': None, 'settings': settings}
        # 动态加载 extensions 下所有非私有函数
        for module in [extensions.common_funcs, extensions.pda_funcs, extensions.rms_funcs, extensions.wms_funcs]:
            for name in dir(module):
                if not name.startswith('_') and callable(getattr(module, name)):
                    env[name] = getattr(module, name)
        return env

    def hook_func_value_replace(self, target: Any) -> Any:
        """
        递归遍历目标数据，执行其中的 Hook 函数并替换为返回值，保持原有数据类型不变
        """
        if isinstance(target, dict):
            return {k: self.hook_func_value_replace(v) for k, v in target.items()}

        elif isinstance(target, list):
            return [self.hook_func_value_replace(i) for i in target]

        elif isinstance(target, str):
            # 1. 完整匹配：保留函数返回值的原始类型 (如 int, dict, object)
            match = self.func_re.fullmatch(target)
            if match:
                func_str = match.group(1)
                return self._exec_func(func_str)

            # 2. 内联匹配：用于字符串拼接
            if '${' in target:

                def inline_repl(m: re.Match) -> str:
                    result = self._exec_func(m.group(1))
                    return str(result)

                return self.inline_func_re.sub(inline_repl, target)

        return target

    def _exec_func(self, func_str: str) -> Any:
        """安全地执行单个函数字符串"""
        log.debug(f'⚙️ 执行 Hook 函数: {func_str}')
        try:
            return eval(func_str, self._safe_env)
        except Exception as e:
            log.error(f'Hook 函数执行失败 [{func_str}]: {e}')
            raise ContextVariableError(f'Hook 语法错误或执行异常: {func_str} -> {e}') from e


hook_executor = HookExecutor()
