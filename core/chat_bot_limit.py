from typing import NamedTuple


class RequestLimit(NamedTuple):
    max_reqs_per_min: int  # 每分钟请求数 RPM
    max_tokens_consumed_per_min: int  # 每分钟消耗的最大token数 TPM
    max_len_context: int  # 请求的最大上下文长度
    max_concurrent_requests: int  # 短时间内并发请求数


CHAT_MODEL_LIMIT = {
    "qwen-long": RequestLimit(100, 10 ** 8, 10 ** 6, 40),
    "qwen-turbo": RequestLimit(500, 500000, 6000, 40),
    "qwen-plus": RequestLimit(500, 1300000, 30000, 20),
    "qwen-max": RequestLimit(60, 100000, 6000, 40),

    "glm-4": RequestLimit(10, 10 ** 8, 30000, 5),

    "ernie-speed-128k": RequestLimit(60, 300000, 128000, 1)
}
