from functools import partial
from typing import Union, Type

from core.chat_bot_limit import CHAT_MODEL_LIMIT
from core.checked import Checked, CheckMixin
from core.custom_semaphore import TimedReqsSemaphore, FlowSemaphore
from core.logger import init_logging
from core.sql_helper import SQLAdapter
from core.task_config import TaskConfig
from core.config import DATABASE_URI
from core.async_extract import parse_for_any_type


def get_extract_prompt_template(config: TaskConfig, cls):
    with open(config.extract_prompt_template_path, 'r', encoding='utf-8') as file:
        prompt_template = file.read()
    prompt_template = prompt_template.format(
        dataset_theme=config.dataset_theme,
        fields=cls.generate_format_str(),
        article_mapping_to_instance='Note that an article may contain multiple instances, so you should return a list of object.' if config.one_article_to_many_instance else '',
        article='{article}')
    return prompt_template


def load_dir_txt(config: TaskConfig) -> list[tuple[str, str]]:
    """
    读取目录下的所有txt文件
    :param config: 任务配置
    :return: 无后缀文件名 与 文件内容
    """
    return [(e.as_posix(), e.read_text(encoding='utf-8')) for e in config.dataset_input_path.glob("*.txt")]


async def build_task(config: TaskConfig, cls: Union[Type[Checked], Type[CheckMixin]]):
    if config.one_article_to_many_instance and config.table_primary_key == "file_path":
        raise ValueError("When one_article_to_many_instance is True, "
                         "file_path should not be the primary key of the table")
    if config.one_article_to_many_instance and config.filter_by_file_path:
        print("Warning: one_article_to_many_instance and filter_by_file_path are both True, "
              "this may cause some data to be lost")

    logger = init_logging(config.log_dir_path / f'{config.dataset_name}.log')

    logger.info(f"extract {cls.__name__} data")
    logger.debug(f"config is {config}")

    prompt_template = get_extract_prompt_template(config, cls)
    logger.debug(f"prompt_template is {prompt_template}")

    timed_reqs_sem = TimedReqsSemaphore(CHAT_MODEL_LIMIT[config.model].max_reqs_per_min)
    flow_sem = FlowSemaphore(CHAT_MODEL_LIMIT[config.model].max_tokens_consumed_per_min, 12000)
    instant_req_sem = TimedReqsSemaphore(CHAT_MODEL_LIMIT[config.model].max_concurrent_requests, 15)  # 限制瞬时请求的数量

    logger.debug(f"timed_reqs_sem={timed_reqs_sem}")
    logger.debug(f"flow_sem={flow_sem}")
    logger.debug(f"instant_req_sem={instant_req_sem}")

    match config.input_file_type:
        case "pdf":
            from core.pdf2txt import parse_pdf
            input_data = [(e.path, e.txt) for e in parse_pdf(config)]
        case "txt":
            input_data = load_dir_txt(config)
        case _:
            raise ValueError(f"unsupported input file type {config.input_file_type}")

    if config.model.startswith("qwen"):
        from core.qwen_backend import qwen_extraction
        extract_func = partial(qwen_extraction,
                               timed_reqs_sem=timed_reqs_sem, flow_sem=flow_sem, instant_sem=instant_req_sem,
                               extract_model=config.model, extract_prompt=prompt_template,
                               post_check_func=config.post_check_func)
    elif config.model.startswith("glm"):
        from core.glm_backend import glm_extraction
        extract_func = partial(glm_extraction,
                               timed_reqs_sem=timed_reqs_sem, instant_sem=instant_req_sem,
                               extract_model=config.model, extract_prompt=prompt_template,
                               post_check_func=config.post_check_func)
    else:
        raise ValueError(f"unsupported model {config.model}")

    cls_adapter = SQLAdapter(cls, DATABASE_URI, auto_create=True, primary_key=config.table_primary_key)

    if config.filter_by_file_path:
        tmp_input_data = [(file_name, content) for file_name, content in input_data
                          if not cls_adapter.check_exist(file_name)]
        if len(tmp_input_data) != len(input_data):
            logger.info(f"filter out {len(input_data) - len(tmp_input_data)} existing data")
        input_data = tmp_input_data

    logger.info(f"start extract, total count = {len(input_data)}")

    result = await parse_for_any_type(input_data, cls, extract_func, cls_adapter, config.one_article_to_many_instance)

    timed_reqs_sem.cancel()
    flow_sem.cancel()
    instant_req_sem.cancel()

    if config.post_processing_hooks:
        config.post_processing_hooks(result)
