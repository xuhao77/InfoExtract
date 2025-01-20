import logging
import pickle
from pathlib import Path
from concurrent import futures
from typing import NamedTuple, List
import re

import PyPDF2
from .logger import init_logging
from .task_config import TaskConfig


class PDF2TXTResult(NamedTuple):
    path: str  # 文件名
    first_page_txt: str  # PDF的第一页通常可以分析出标题 作者等信息 单独拎出来
    txt: str  # 正文 对于论文 此部分不含References后的内容
    ref_txt: str  # 对于论文 此部分为References后的内容


def split_ref(text: str) -> tuple[str, str]:
    # 从txt中文本中不区分大小写地搜索References 找到最后一个出现的位置
    pattern = re.compile(r'references', re.IGNORECASE)
    matches = list(pattern.finditer(text))
    if not matches:
        pattern = re.compile(r"\[1]")
        matches = list(pattern.finditer(text))
    if matches:
        start_index = matches[-1].start()
    else:
        return text, ""
    return text[:start_index], text[start_index:]


def worker(pdf_file_path: Path):
    # noinspection PyBroadException
    try:
        with open(pdf_file_path, 'rb') as read_file:
            pdf_reader = PyPDF2.PdfReader(read_file)
            text = ''
            first_page_txt = ''
            for page_num in range(len(pdf_reader.pages)):
                text += pdf_reader.pages[page_num].extract_text()
                if page_num == 0:
                    first_page_txt = text

            # 存储提取到的正文与参考文献页
            txt_without_ref, ref_txt = split_ref(text)
            return PDF2TXTResult(pdf_file_path.as_posix(), first_page_txt, txt_without_ref, ref_txt)
    except Exception as e:
        raise RuntimeError(pdf_file_path.as_posix(), repr(e))


def parse_pdf(config: TaskConfig) -> list[PDF2TXTResult]:
    logger = logging.getLogger("InfoExtract")

    task_list = []
    result = []
    with futures.ProcessPoolExecutor(max_workers=8) as executor:
        for e in config.dataset_input_path.glob("*.pdf"):
            task_list.append(executor.submit(worker, e))

    if len(task_list) == 0:
        logger.warning(f"{config.dataset_input_path} is empty dataset!")
    for e in task_list:
        if e.exception() is None:
            ret: PDF2TXTResult = e.result()
            result.append(ret)
            logger.info(f"file_path={ret.path},txt_len={len(ret.txt)},ref_len={len(ret.ref_txt)}")
        else:
            logger.error(f"file_path={e.exception().args[0]},message={e.exception().args[1]}")

    if not config.dataset_output_path.exists():
        config.dataset_output_path.mkdir(parents=True, exist_ok=True)

    with open(config.dataset_output_path / "pdf2txt.pkl", 'wb') as file:
        pickle.dump(result, file)

    return result
