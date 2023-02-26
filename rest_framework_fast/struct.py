#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    @author  : chengshuang
    @contact : chengshuang@qudoor.cn
    @File    : class.py
    @Software: PyCharm
    @Time    : 2023/2/20 09:50
"""
import inspect


class Dict:

    @classmethod
    def __serialize__(cls) -> dict:
        """
        序列化类属性为dict，可嵌套使用
        :return:
        """
        if not hasattr(cls, "__cache"):
            ret = dict()
            for attr_name in dir(cls):
                if attr_name.startswith("_") or attr_name in ["to_dict"]:
                    continue
                attr = getattr(cls, attr_name)
                if inspect.ismethod(attr) or inspect.isfunction(attr):
                    continue
                elif inspect.isclass(attr) and issubclass(attr, Dict):
                    ret[cls.__render_key__(attr_name)] = attr.__serialize__()
                else:
                    ret[cls.__render_key__(attr_name)] = cls.__render_value__(attr)
            setattr(cls, "__cache", ret)
        return getattr(cls, "__cache")

    @classmethod
    def __render_key__(cls, key: str) -> str:
        return key

    @classmethod
    def __render_value__(cls, value):
        return value


class UpperDict(Dict):

    @classmethod
    def __render_key__(cls, key: str) -> str:
        return key.upper()


UDict = UpperDict
