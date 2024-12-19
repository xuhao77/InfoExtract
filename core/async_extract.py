import asyncio
import logging
import platform
from typing import Callable, Awaitable, Union, Type

from core.checked import CheckMixin, Checked
from core.extract_helper import ExtractResult
from core.sql_helper import SQLAdapter

if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

asyncio.set_event_loop(asyncio.new_event_loop())


async def parse_for_any_type(input_list: list[tuple[str, str]],
                             data_type: Union[Type[Checked], Type[CheckMixin]],
                             extract_func: Callable[[str, str], Awaitable[ExtractResult]],
                             sql_adapter: SQLAdapter,
                             one_to_many: bool) -> list[ExtractResult]:
    logger = logging.getLogger("InfoExtract")
    task_list = [extract_func(*e) for e in input_list]
    request_success_cnt = 0
    parse_success_cnt = 0
    token_cnt = 0
    total_task = len(input_list)
    task_cnt = 0
    result = []
    # noinspection PyBroadException
    try:
        for e in asyncio.as_completed(task_list):
            ret: ExtractResult = await e
            task_cnt += 1
            if ret.request_success:
                request_success_cnt += 1
                token_cnt += ret.tokens_consumed
                logger.info(f"{task_cnt}/{total_task} file_name={ret.file_name},tokens_consumed={ret.tokens_consumed}")
                try:
                    ret.parse_objects = []
                    for i, (obj, missing_keys, extra_keys) in enumerate(
                            data_type.parse_json(ret.json_str, one_to_many)):
                        if missing_keys or extra_keys:
                            logger.warning(f"file_name={ret.file_name},obj={i},missing_keys={missing_keys},"
                                           f"extra_keys={extra_keys}")
                        ret.parse_objects.append(obj)
                        parse_success_cnt += 1
                        ret.json_str = ''
                        sql_adapter.add_item(ret.file_name, obj)

                except Exception as e:
                    ret.parse_success = False
                    ret.fail_message = repr(e)
                    logger.error(f"{task_cnt}/{total_task} file_name={ret.file_name},message={ret.fail_message}")
            else:
                logger.error(f"{task_cnt}/{total_task} file_name={ret.file_name},message={ret.fail_message}")
            result.append(ret)
    except KeyboardInterrupt:
        logger.info("end by KeyboardInterrupt")
    except Exception as e:
        logger.info(f"end by {repr(e)}")
    finally:
        sql_adapter.commit()
        if request_success_cnt > 0:
            logger.info(f"end: {request_success_cnt}/{total_task} requests success, "
                        f"the average token consumption is {int(token_cnt / request_success_cnt)}")
            logger.info(f"end: {parse_success_cnt} instances parse success")

    return result
