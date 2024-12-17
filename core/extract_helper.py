import re
from dataclasses import dataclass
from typing import Optional, Union

from core.checked import Checked, CheckMixin

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
    parse_obj: Optional[Union[Checked, CheckMixin]] = None


def _is_got_json_str(json_str: str):
    return json_str.find("{") != -1 and json_str.find("}") != -1


def not_contains_chinese(text):
    # 使用正则表达式判断字符串中是否包含中文字符
    match = CHINESE_PATTERN.search(text)
    return match is None

