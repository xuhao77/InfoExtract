from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal


@dataclass
class TaskConfig:
    input_file_type: Literal['pdf', 'txt']
    dataset_dir_path: Path
    dataset_name: str
    dataset_theme: str
    model: str = "qwen-plus"
    post_check_func: Callable[[str], bool] = lambda _: True
    one_article_to_many_instance: bool = False,
    table_primary_key: str | None = None
    extract_prompt_template_path: Path = Path(__file__).resolve().parent / "template/extract.txt"
    repair_json_prompt_template_path: Path = Path(__file__).resolve().parent / "template/repair_json.txt"
    log_dir_path: Path = Path("./log")

    def __post_init__(self):
        if isinstance(self.dataset_dir_path, str):
            self.dataset_dir_path = Path(self.dataset_dir_path)
        if isinstance(self.log_dir_path, str):
            self.log_dir_path = Path(self.log_dir_path)

        self.dataset_input_path = self.dataset_dir_path / self.dataset_name
        self.dataset_output_path = self.dataset_dir_path / (self.dataset_name + "_output")

        if not self.log_dir_path.exists():
            self.log_dir_path.mkdir(parents=True)
