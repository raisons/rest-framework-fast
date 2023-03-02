#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author  : chengshuang
@Contact : chengshuang@qudoor.cn
@File    : db_perfix.py
@Software: PyCharm
@Time    : 2023/3/2 09:25
"""

from django.db.models import options
from django.db.models.signals import class_prepared, pre_init

DB_PREFIX_KEYWORD = "db_prefix"
options.DEFAULT_NAMES = options.DEFAULT_NAMES + (DB_PREFIX_KEYWORD,)


# usage:
# from importlib import import_module
# import_module("rest_framework_fast.hooks.db_prefix")
def model_prefix(sender, **kwargs):
    meta = sender._meta  # noqa
    prefix = getattr(meta, DB_PREFIX_KEYWORD, None)
    db_table = getattr(meta, "db_table")

    if prefix and not db_table.startswith(prefix):
        sender._meta.db_table = prefix + db_table


pre_init.connect(model_prefix)
class_prepared.connect(model_prefix)
