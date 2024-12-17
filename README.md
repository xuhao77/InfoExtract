# InfoExtract

![Static Badge](https://img.shields.io/badge/python-3.11-blue)
![Static Badge](https://img.shields.io/badge/sqlite-green)
![Static Badge](https://img.shields.io/badge/Qwen-blue)
![Static Badge](https://img.shields.io/badge/GLM-blue)
![GitHub License](https://img.shields.io/github/license/mashape/apistatus)

# 基于大模型的信息提取框架

支持以Qwen和GLM作为大模型后端，完成信息提取任务。

## 特色

1. 支持异步，可从每分钟并发数、每分钟消耗的Token数、瞬时并发数三个维度控制并发
2. 支持SQL数据库，自动创建表并添加数据
3. 强大的JSON解析功能，通过定制元类，支持类型自动转换，支持添加自定义字段验证逻辑
4. 完善的日志系统
5. 支持PDF与TXT格式解析，对于PDF论文，自动从正文中剔除References

## 安装
```shell
pip install -r requirements.txt
```

## 使用
1. 在 core/config.py 中配置数据库与 API_KEY ，申请地址：[DashScope](https://dashscope.aliyun.com/) [GLM](https://open.bigmodel.cn/dev/api/normal-model/glm-4)
2. 定义好待提取信息的类，须继承自`CheckMixin`与`Checked`，须提供类型注解，文档注释（将成为提示词的一部分）以及针对字段的验证函数是可选的，像demo.py那样
3. 配置好`TaskConfig`，运行`build_task`

## Demo效果
SQL数据库截图
![img.png](img.png)

日志截图
![img_1.png](img_1.png)

## 项目的解析器强大在哪里
考虑大模型回复了下面这样糟糕的JSON字符串
```json
[
  {"user_name": "uncleared","age": "20","hobby": "sing,dance,rap"},
  {"user_name": "xu","age": null,"hobby": "sing;dance;rap;basketball"},
  {"user_name": "kun","age": "","hobby": ["sing","dance","rap","basketball"]}
]
```
使用本项目的解析器，demo.py可以解析出如下结果
```shell
UserInfo({'user_name': '', 'age': 20, 'hobby': ['sing', 'dance', 'rap']})
UserInfo({'user_name': 'XU', 'age': 0, 'hobby': ['sing', 'dance', 'rap', 'basketball']})
UserInfo({'user_name': 'KUN', 'age': 0, 'hobby': ['sing', 'dance', 'rap', 'basketball']})
```

`uncleared`的字段自动置空；`str`类型或空值的`age`字段可以自动转换为`int`型；使用`,;`分隔的字符串会自动转换为列表