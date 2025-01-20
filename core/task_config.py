from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal, Any

from .extract_helper import ExtractResult


@dataclass
class TaskConfig:
    input_file_type: Literal['pdf', 'txt']  # 输入类型 可以为pdf或txt
    dataset_dir_path: Path  # 数据集文件夹所在的文件夹路径
    dataset_name: str  # 数据集文件夹名称
    dataset_theme: str  # 数据集的主题
    model: Literal['qwen-plus', 'qwen-turbo','qwen-max','glm-4','deepseek-chat']  = "qwen-plus"  # 模型名称 支持qwen-plus、qwen-turbo、qwen-max、glm-4
    post_check_func: Callable[[str], bool] = lambda _: True  # 针对大模型的回复的检查函数 只有通过才进行下一步解析
    one_article_to_many_instance: bool = False  # 一篇文章是否对应多个实例
    table_primary_key: str | None = None  # 数据库主键 可以为file_path（该值由框架自动提供）
    filter_by_file_path: bool = False  # 是否根据文件路径过滤数据
    filter_hooks: list[Callable[[Any], bool]] = field(default_factory=list)  # 额外的过滤逻辑 有些场景下只需要处理文件夹下的部分文件
    post_processing_hook: Callable[[list[ExtractResult]], Any] | None = None  # 针对提取结果的处理函数
    extract_prompt_template_path: Path = Path(__file__).resolve().parent / "template/extract.txt"  # 提取模板路径
    repair_json_prompt_template_path: Path = Path(__file__).resolve().parent / "template/repair_json.txt"  # 修复json的模板路径
    log_dir_path: Path = Path("./log")  # 日志文件夹路径

    def __post_init__(self):
        if isinstance(self.dataset_dir_path, str):
            self.dataset_dir_path = Path(self.dataset_dir_path)
        if isinstance(self.log_dir_path, str):
            self.log_dir_path = Path(self.log_dir_path)

        self.dataset_input_path = self.dataset_dir_path / self.dataset_name
        self.dataset_output_path = self.dataset_dir_path / (self.dataset_name + "_output")

        if not self.log_dir_path.exists():
            self.log_dir_path.mkdir(parents=True)
