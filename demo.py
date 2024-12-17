import asyncio
from pathlib import Path

from core.checked import CheckMixin, Checked, filed_validator
from core.extract_helper import not_contains_chinese
from core.task_config import TaskConfig
from core.task import build_task


class UserInfo(CheckMixin, Checked):
    """'hobby' summarized from what he often does"""
    user_name: str
    age: int
    hobby: list[str]

    @filed_validator("user_name")
    def check_user_name(self, v: str):
        """我只想要大写的用户名"""
        return v.upper()


task_config = TaskConfig(
    input_file_type="txt",  # 输入类型 可以为pdf或txt
    dataset_dir_path=Path("./data"),  # 数据集文件夹所在的文件夹路径
    dataset_name="user_info",  # 数据集文件夹名称
    dataset_theme="user information",  # 数据集的主题
    one_article_to_many_instance=True,  # 一篇文章可能有多个实例
    post_check_func=not_contains_chinese  # 针对大模型的回复的检查函数 只有通过才进行下一步解析
)

if __name__ == '__main__':
    asyncio.run(build_task(task_config, UserInfo))
