import asyncio
from functools import partial
from pathlib import Path

from core import CheckMixin, Checked, filed_validator, DATABASE_URI, not_contains_chinese, save_to_excel, SQLAdapter, \
    TaskConfig, build_task


# 待提取信息的类 你可以在类下方的文档中添加更多的字段说明 这将成为提示词的一部分
class UserInfo(CheckMixin, Checked):
    """'hobby' summarized from what he often does"""
    user_name: str
    age: int
    hobby: list[str]

    @filed_validator("user_name")
    def check_user_name(self, v: str):
        """我只想要大写的用户名"""
        return v.upper()


def my_filter(file_name: str):
    # file_name 为全路径的字符串
    return Path(file_name).stem in ["1", "3"]


task_config = TaskConfig(
    input_file_type="txt",  # 输入类型 可以为pdf或txt
    dataset_dir_path=Path("./data"),  # 数据集文件夹所在的文件夹路径
    dataset_name="user_info",  # 数据集文件夹名称
    dataset_theme="user",  # 数据集的主题
    one_article_to_many_instance=True,  # 一篇文章可能有多个实例
    table_primary_key="user_name",  # 指定用户名为主键
    filter_by_file_path=True,  # 根据file_path过滤存在的数据
    filter_hooks=[my_filter],
    post_check_func=not_contains_chinese,  # 针对大模型的回复的检查函数: 不包含中文
    post_processing_hook=partial(save_to_excel,  # 针对提取结果的处理函数: 保存到excel
                                 ignore_fields=[],
                                 output_name="output.xlsx",
                                 output_dir=Path("./output"))
)

# TaskConfig中还可以指定数据库主键
# 但要注意 一篇文章对应多个实例时 不可以将file_path作为主键 这会导致冲突

if __name__ == '__main__':
    # 提取
    asyncio.run(build_task(task_config, UserInfo))
    ## 读取
    # user_adapter = SQLAdapter(UserInfo, DATABASE_URI)
    # for file_path, item in user_adapter.fetch_all():
    #     print(file_path, item)
