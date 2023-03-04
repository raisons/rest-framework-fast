#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author  : chengshuang
# @Contact : chengshuang@qudoor.cn
# @File    : fields.py
# @Software: PyCharm
# @Time    : 2023/2/16 09:48

import base64
import uuid
import json
from django.core.files.base import ContentFile
from rest_framework import fields


class Base64FieldMixin:

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:'):
            # base64 encoded file - decode
            format, datastr = data.split(';base64,')  # format ~= data:image/X,
            ext = format.split('/')[-1]  # guess file extension
            if ext[:3] == 'svg':
                ext = 'svg'

            data = ContentFile(
                base64.b64decode(datastr),
                name='{}.{}'.format(uuid.uuid4(), ext)
            )

        elif isinstance(data, str) and data.startswith('http'):
            raise fields.SkipField()

        return super().to_internal_value(data)  # noqa


class ImageField(Base64FieldMixin, fields.ImageField):
    pass


class FileField(Base64FieldMixin, fields.FileField):
    pass


class JSONField(fields.JSONField):
    """
    支持序列化的时候传入string参数，如果为True则序列化为字符串
    """

    def __init__(self, **kwargs):
        self.string = kwargs.pop('string', False)
        super().__init__(**kwargs)

    def to_representation(self, value):
        if self.string:
            return json.dumps(value, cls=self.encoder)
        return super().to_representation(value)
