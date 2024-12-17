from dataclasses import dataclass
from types import MappingProxyType
import re
import json
from typing import Generator


def filed_validator(field_name):
    def wrapper(func):
        func.__name__ = field_name + "_validator"
        return classmethod(func)

    return wrapper


class Field:
    def __init__(self, constructor, name, check_func=None):
        if not callable(constructor):  # constructor 必须可调用
            raise TypeError('constructor must be callable')
        self.constructor = constructor
        # 下面的Checked类中使用__slots__来阻止用户新增属性
        # 这里属性描述符的名字不能和__slots__中的一致
        # 如果一致会报错　xxx in __slots__ conflicts with class variable
        self.name = '_' + name
        self.check_func = check_func
        self.generic_type = None
        self.generic_param_type = None

        # 暂不支持dict类型
        if self.generic_type is dict:
            raise ValueError('dict type is not supported')

        if hasattr(self.constructor, '__args__'):
            if len(self.constructor.__args__) != 1:
                raise TypeError(f'Parameterized generics only support list[str] type,but got {self.constructor}')
            ori_type = self.constructor.__origin__
            par_type = self.constructor.__args__[0]
            if not (ori_type is list and par_type is str):
                raise TypeError(f'Parameterized generics only support list[str] type,but got {self.constructor}')
            self.generic_type = ori_type
            self.generic_param_type = par_type

    def __set__(self, instance, value):
        if value is ... or value is None:
            value = self.constructor()
        try:
            if self.generic_type is list and self.generic_param_type is str:
                if isinstance(value, str):
                    value = [t for e in re.split(r'[,;]+', value) if (t := e.strip()) != '']
                else:
                    value = [str(i) for i in value]
            else:
                if (self.constructor is int or self.constructor is float) and isinstance(value, str):
                    value = self.constructor('0'+value)
                else:
                    value = self.constructor(value)
        except (TypeError, ValueError) as e:
            raise ValueError(f'{value!r} is not compatible with {self.name[1:]!r}:{self.constructor}') from e
        # !r使得字符串可以带引号显示、使得其他对象的输出也更规范
        # from e 使得异常可以回溯

        # 如果设置了数据检查函数 这里进行检查
        if self.check_func is not None:
            try:
                value = self.check_func(value)
            except ValueError as e:
                raise ValueError(f'{self.name[1:]}={value!r} cannot pass the check!') from e
        setattr(instance, self.name, value)

    # 必须提供__get__方法
    # 否则obj.attr拿到的是属性描述符
    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return getattr(instance, self.name)


class CheckedMeta(type):
    def __new__(cls, cls_name, bases, cls_dict):
        if '__slots__' not in cls_dict:
            # 为实例属性创建类属性“属性描述符”
            slots = []
            _fields = []
            _field_types = []
            _field_defaults = {}
            _field_check_funcs = {}

            # 通过遍历基类元组bases处理了继承问题
            for base in bases:
                if hasattr(base, '_fields'):
                    _fields.extend(base._fields)
                    _field_types.extend(base._field_types)
                    _field_defaults.update(base._field_defaults)
                    _field_check_funcs.update(base._filed_check_funcs)

            check_func_names = []
            for k, v in cls_dict.items():
                if isinstance(v, classmethod) and v.__name__.endswith("_validator"):
                    check_func_names.append((k, v.__name__))

            for old_name, new_name in check_func_names:
                _field_check_funcs[new_name[:-10]] = cls_dict.pop(old_name).__get__(cls)

            for name, constructor in cls_dict['__annotations__'].items():
                if name == 'fields':
                    raise ValueError('fields is reserved')

                _fields.append(name)
                v = constructor()
                _field_types.append(type(v))
                _field_defaults[name] = v

                field = Field(constructor, name, _field_check_funcs.get(name, None))
                cls_dict[name] = field
                slots.append(field.name)

            if t := _field_check_funcs.keys() - set(_fields):
                plural = 'them' if len(t) > 1 else 'it'
                extra = ','.join(f'{name!r}' for name in t)
                raise ValueError(f'{extra} not in _fields, but set a check function for {plural}')

            cls_dict['__slots__'] = tuple(slots)
            cls_dict['_fields'] = tuple(_fields)
            cls_dict['_field_types'] = tuple(_field_types)
            cls_dict['_field_defaults'] = MappingProxyType(_field_defaults)
            cls_dict['_filed_check_funcs'] = MappingProxyType(_field_check_funcs)
        return super().__new__(cls, cls_name, bases, cls_dict)


class Checked(metaclass=CheckedMeta):
    __slots__ = ()  # 为该类跳过__new__方法

    # 继承树中对下面方法的引用都会来到这个类中
    def __init__(self, **kwargs):
        # 为实例属性赋值
        for e in self._fields:
            setattr(self, e, kwargs.pop(e, ...))
        if kwargs:
            self._flag_unknown_attrs(*kwargs)

    def __repr__(self):
        return f'{self.__class__.__name__}({self._asdict()})'

    def __iter__(self):
        return (getattr(self, e) for e in self._fields)

    def _asdict(self):
        return {e: getattr(self, e) for e in self.__class__._fields}

    def _flag_unknown_attrs(self, *names):
        plural = 's' if len(names) > 1 else ''
        extra = ', '.join(f'{name!r}' for name in names)
        raise AttributeError(f'{self.__class__.__name__!r} object has no attribute{plural} {extra}')

    @classmethod
    def empty(cls):
        return cls.__new__(cls)


class CheckMixin:
    __slots__ = ()
    NOT_SPECIFIED = [re.compile(r'not specified', re.IGNORECASE),
                     re.compile(r'unclear', re.IGNORECASE),
                     re.compile(r'not explicitly', re.IGNORECASE),
                     re.compile(r"unspecified", re.IGNORECASE)]

    @classmethod
    def generate_format_str(cls):
        # 双花括号用于在f字符串中转义{}
        return ('{' + str(cls._field_defaults) + '}').replace("'", '"') + cls.__doc__

    @classmethod
    def check_fields(cls):
        """
        返回需要确保存在的字段
        默认是全部的字段都需要确保存在
        """
        return set(cls._fields)

    @classmethod
    def parse_json(cls, json_str: str, one_to_many: bool = False) -> Generator[tuple[dict, list, list], None, None]:
        """
        解析json
        :param one_to_many: 是否一个文章对应多个实例
        :param json_str: 必须是一个形如'{"name":"value"}'或'[{"name":"value"}]'的json字符串
        :return: 生成一个元组 (json_dict, missing_keys, extra_keys)
        """
        if not isinstance(json_str, str) or len(json_str) == 0:
            raise ValueError("json_str must be a non-empty string")
        if one_to_many:
            begin_index = json_str.index('[')
            end_index = json_str.rindex(']')
            json_str = json_str[begin_index:end_index + 1]
            json_dict: list[dict] = json.loads(json_str)
        else:
            begin_index = json_str.index('{')
            end_index = json_str.rindex('}')
            json_str = json_str[begin_index:end_index + 1]
            # json_str = re.sub(r'(?<!https:)//.*', '', json_str)  # 去除json字符串中可能出现的注释
            json_dict: list[dict] = [json.loads(json_str)]

        check_fields = cls.check_fields()

        if one_to_many and not isinstance(json_dict, list):
            raise ValueError("json_str must be a list")

        for item in json_dict:
            missing_keys = []

            for attr in check_fields:
                if attr not in item:
                    missing_keys.append(attr)
                v = item.get(attr, ...)
                if isinstance(v, str):
                    for p in cls.NOT_SPECIFIED: # 确保该字段不是无意义的字符串
                        if p.search(v):
                            del item[attr]
                            missing_keys.append(attr)
                            break
            extra_keys = list(set(item.keys()) - set(check_fields))
            for attr in extra_keys:
                del item[attr]
            yield cls(**item), missing_keys, extra_keys

    def sql_adapter(self):
        """
        返回一个迭代器
        根据类型注解
        将类的各个字段转为sql支持的类型
        """
        for field_name, field_type in zip(self._fields, self._field_types):
            if field_type is int or field_type is float or field_type is str:
                yield getattr(self, field_name)
            elif field_type is list or field_type is dict or field_type is tuple or field_type is set:
                yield json.dumps(getattr(self, field_name))
            else:
                raise ValueError(f"{field_type} of {field_name!r} is not supported")

    @classmethod
    def sql_converter(cls, *args):
        """
        返回子类的实例
        根据类型注解，将sql表中的类型转为数据类的各个字段，并返回数据类的实例
        """
        if len(args) != len(cls._fields):
            raise ValueError(f"Expected {len(cls._fields)} arguments, got {len(args)}:{args!r}")
        ret = cls.empty()
        for field_name, field_type, field_value in zip(cls._fields, cls._field_types, args):
            if field_type is int or field_type is float or field_type is str:
                setattr(ret, field_name, field_value)
            elif field_type is list or field_type is dict or field_type is tuple or field_type is set:
                setattr(ret, field_name, json.loads(field_value))
            else:
                raise ValueError(f"{field_type} of {field_name!r} is not supported")
        return ret
