import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from .checked import Checked, CheckMixin

CHINESE_PATTERN = re.compile(r'[\u4e00-\u9fff]')


@dataclass
class ExtractResult:
    request_success: bool = True
    file_name: str = ''
    file_content: str = ''
    json_str: str = ''
    fail_message: str = ''
    tokens_consumed: int = 0

    parse_success: bool = True
    parse_objects: Optional[list[Union[Checked, CheckMixin]]] = None


def _is_got_json_str(json_str: str):
    return json_str.find("{") != -1 and json_str.find("}") != -1


def not_contains_chinese(text):
    # 使用正则表达式判断字符串中是否包含中文字符
    match = CHINESE_PATTERN.search(text)
    return match is None

def format_excel(path):
    from openpyxl import load_workbook

    # 打开现有的Excel文件
    file_path = path
    workbook = load_workbook(filename=file_path)

    # 选择要调整列宽的工作表
    sheet = workbook.active  # 或者使用 workbook[sheet_name] 来选择特定工作表

    for column in sheet.columns:
        total_length = 0
        cnt = 0
        column_letter = column[0].column_letter  # 获取列字母
        for cell in column:
            # noinspection PyBroadException
            try:
                if cell.value:
                    cell_length = len(str(cell.value))
                    total_length += cell_length
                    cnt += 1
            except Exception:
                pass
        sheet.column_dimensions[column_letter].width = int(total_length / cnt) + 2

    # 保存更改
    workbook.save(filename=file_path)

def save_to_excel(result: list[ExtractResult], ignore_fields: list[str], output_name: str, output_dir: Path):
    import pandas as pd
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
    output_path = output_dir / output_name
    data = []
    for e in result:
        if e.parse_objects:
            for item in e.parse_objects:
                data.append(dict(**item._asdict(), file_path=e.file_name))
    df = pd.DataFrame(data)
    df = df.drop(columns=ignore_fields, axis=1)
    df.to_excel(output_path, index=False)
    format_excel(output_path)
