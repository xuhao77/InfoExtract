from openai import AsyncOpenAI

from .config import OPENAI_DEEPSEEK_API_KEY, OPENAI_DEEPSEEK_BASE_URL
from .custom_semaphore import TimedReqsSemaphore, FlowSemaphore
from .extract_helper import ExtractResult, _is_got_json_str

client = AsyncOpenAI(api_key=OPENAI_DEEPSEEK_API_KEY, base_url=OPENAI_DEEPSEEK_BASE_URL)


async def openai_extraction(file_name: str,
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
            response = await client.chat.completions.create(
                model=extract_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant"},
                    {"role": "user", "content": extract_prompt.format(article=file_content)}
                ],
                stream=False
            )
            tokens_consumed = response.usage.total_tokens
            await flow_sem.flow(tokens_consumed)
            output_text = response.choices[0].message.content
            if _is_got_json_str(output_text) and post_check_func(output_text):
                return ExtractResult(file_name=file_name,
                                     json_str=output_text,
                                     tokens_consumed=tokens_consumed)
            else:
                return ExtractResult(request_success=False,
                                     file_name=file_name,
                                     file_content=file_content,
                                     fail_message="Not got a json str or post check failed")
        except Exception as e:  # 对于键盘中断 Exception捕获不到 会向外抛出
            # 得记录下是哪个文件发生了不可继续的异常
            raise RuntimeError(file_name, *e.args)
