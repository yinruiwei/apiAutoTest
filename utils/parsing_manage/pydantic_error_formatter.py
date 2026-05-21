from pydantic import ValidationError


def format_pydantic_error(err: ValidationError) -> str:
    """
    对 Pydantic 原始报错内容进行处理
    """
    error_msgs = []
    for idx, e in enumerate(err.errors(), 1):
        # loc 是错误发生的层级路径，例如 ('request', 'method')
        # 我们将其转换为点分路径，如 request.method
        field_path = '.'.join([str(x) for x in e.get('loc', [])])

        # 错误原因
        err_msg = e.get('msg', '未知错误')

        # 错误输入的具体值
        err_input = e.get('input', 'N/A')

        error_msgs.append(
            f'  ❌ [错误 {idx}] 字段: <{field_path}>\n     - 报错原因: {err_msg}\n     - 实际输入: {err_input}'
        )

    return '\n' + '\n'.join(error_msgs)
