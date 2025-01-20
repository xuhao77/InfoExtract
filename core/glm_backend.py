import asyncio

from zhipuai import ZhipuAI
from .config import ZHIPUAI_API_KEY
from .custom_semaphore import TimedReqsSemaphore
from .extract_helper import _is_got_json_str, ExtractResult

client = ZhipuAI(api_key=ZHIPUAI_API_KEY)


async def glm_extraction(file_name,
                         file_content,
                         timed_reqs_sem: TimedReqsSemaphore,
                         instant_sem: TimedReqsSemaphore,
                         extract_model: str,
                         extract_prompt: str,
                         post_check_func: callable  # 后处理函数
                         ) -> ExtractResult:
    async with (timed_reqs_sem, instant_sem):  # GLM只从并发请求数量上做限制
        try:
            response = client.chat.asyncCompletions.create(
                model=extract_model,  # 填写需要调用的模型名称
                messages=[
                    {
                        "role": "user",
                        "content": extract_prompt.format(article=file_content)
                    }
                ],
            )
            task_id = response.id
            task_status = ''
            get_cnt = 0

            while task_status != 'SUCCESS' and task_status != 'FAILED' and get_cnt <= 40:
                response = client.chat.asyncCompletions.retrieve_completion_result(id=task_id)
                task_status = response.task_status
                await asyncio.sleep(2)
                get_cnt += 1

            if task_status == 'SUCCESS':
                if _is_got_json_str(response.choices[0].message.content) and post_check_func(
                        response.choices[0].message.content):
                    return ExtractResult(file_name=file_name, json_str=response.choices[0].message.content)
                else:
                    return ExtractResult(request_success=False, file_name=file_name, file_content=file_content,
                                         fail_message="Not got a json str or post check failed")
            else:
                # 姑且认为这里出现的异常不会影响其他请求
                return ExtractResult(request_success=False, file_name=file_name, file_content=file_content,
                                     fail_message=repr(response))
        except Exception as e:
            # 得记录下是哪个文件发生了不可继续的异常
            raise RuntimeError(file_name, repr(e))
