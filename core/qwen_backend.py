from http import HTTPStatus
from typing import Awaitable

import dashscope
from dashscope.aigc.generation import AioGeneration

from .custom_semaphore import TimedReqsSemaphore, FlowSemaphore
from .extract_helper import ExtractResult, _is_got_json_str
from .config import DASHSCOPE_API_KEY

dashscope.api_key = DASHSCOPE_API_KEY


async def qwen_extraction(file_name: str,
                          file_content: str,
                          timed_reqs_sem: TimedReqsSemaphore,  # 每分钟请求数上限
                          flow_sem: FlowSemaphore,  # 每分钟消耗的token上限
                          instant_sem: TimedReqsSemaphore,  # 瞬时并发数上限
                          extract_model: str,
                          extract_prompt: str,
                          post_check_func: callable  # 后处理函数
                          ) -> ExtractResult:
    async with (timed_reqs_sem, flow_sem, instant_sem):
        try:
            response = await AioGeneration.call(extract_model,
                                                prompt=extract_prompt.format(article=file_content))
            if response.status_code == HTTPStatus.OK:
                tokens_consumed = response.usage.total_tokens
                await flow_sem.flow(tokens_consumed)

                if _is_got_json_str(response.output.text) and post_check_func(response.output.text):
                    return ExtractResult(file_name=file_name,
                                         json_str=response.output.text,
                                         tokens_consumed=tokens_consumed)
                else:
                    return ExtractResult(request_success=False,
                                         file_name=file_name,
                                         file_content=file_content,
                                         fail_message="Not got a json str or post check failed")

            elif response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                raise RuntimeError("Too many requests! Check the concurrency limit setting!")
            else:
                if response.code == 'InvalidParameter' or response.code == 'DataInspectionFailed':
                    # 参数不合法 数据审查错误
                    return ExtractResult(request_success=False,
                                         file_name=file_name,
                                         file_content=file_content,
                                         fail_message="InvalidParameter or DataInspectionFailed")
                else:
                    # response.code == 'Arrearage' or response.code == 'RequestTimeOut':
                    # 账户欠费 网络不通导致超时 触发限流等异常意味着其他并发任务都应该取消
                    raise RuntimeError(response.code, response.message)
        except Exception as e:  # 对于键盘中断 Exception捕获不到 会向外抛出
            # 得记录下是哪个文件发生了不可继续的异常
            raise RuntimeError(file_name, *e.args)
