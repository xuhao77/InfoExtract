import sqlite3
from itertools import chain
from typing import Union

from .checked import CheckMixin, Checked

SQL_TYPES_MAPPING = {
    int: 'INTEGER',
    float: 'FLOAT',
    str: 'TEXT',
    list: 'TEXT',
    dict: 'TEXT',
    tuple: 'TEXT',
    set: 'TEXT'}


class SQLAdapter:
    def __init__(self, cls, uri, auto_create=False, primary_key=None):
        self.uri = uri
        self.table_name = cls.__name__
        self.fields = cls._fields
        self.field_types = cls._field_types
        assert len(self.fields) == len(self.field_types)
        self.conn = sqlite3.connect(uri)
        self.cls = cls
        if auto_create:
            self.create_table(primary_key)

    def create_table(self, primary_key: str | None):
        # 检查表是否存在
        cur = self.conn.cursor()
        cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{self.table_name}'")
        if cur.fetchone() is not None:
            return

        field_type_list = ', '.join(
            f'{field} {SQL_TYPES_MAPPING[type_]}' for field, type_ in chain(zip(self.fields, self.field_types),
                                                                            [("file_path", str)]))
        if primary_key is not None:
            create_command = f'CREATE TABLE {self.table_name}({field_type_list}, PRIMARY KEY({primary_key}))'
        else:
            create_command = f'CREATE TABLE {self.table_name}(id INTEGER PRIMARY KEY AUTOINCREMENT, {field_type_list})'

        cur.execute(create_command)
        self.conn.commit()

    def add_item(self, file_path, item: Union[CheckMixin, Checked]):
        if not isinstance(item, self.cls):
            raise ValueError(f"item must be an instance of {self.cls.__name__}")
        cur = self.conn.cursor()
        cur.execute(f'INSERT INTO {self.table_name}({",".join(self.fields)}, file_path) VALUES ({",".join("?" for _ in range(len(self.fields) + 1))})',
                    (*item.sql_adapter(), file_path))

    def commit(self):
        self.conn.commit()

    def fetch_all(self):
        # 返回一个产生cls实例的生成器
        cur = self.conn.cursor()
        cur.execute(f'SELECT {",".join(self.fields)}, file_path FROM {self.table_name}')
        query_result = cur.fetchall()
        for e in query_result:
            yield e[-1], self.cls.sql_converter(*e[:-1])

    def check_exist(self, file_path_value):
        cur = self.conn.cursor()
        cur.execute(f"SELECT * FROM {self.table_name} WHERE file_path=?", (file_path_value,))
        return cur.fetchone() is not None

    def __del__(self):
        self.conn.commit()
        self.conn.close()
