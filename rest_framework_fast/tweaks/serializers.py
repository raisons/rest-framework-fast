#!/usr/bin/env python

from copy import deepcopy
from functools import partial

from django.db import models
from rest_framework.serializers import ModelSerializer as DrfModelSerializer
from rest_framework.serializers import Serializer as DrfSerializer
from rest_framework.serializers import empty
from rest_framework.utils.field_mapping import get_nested_relation_kwargs

from rest_framework_fast.fields import FileField, ImageField

default_serializer_field_mapping = deepcopy(DrfModelSerializer.serializer_field_mapping)

ext_serializer_field_mapping = {
    **default_serializer_field_mapping,
    models.FileField: FileField,
    models.ImageField: ImageField,
}


class ModelSerializerMixin:
    """
    扩展drf默认ModelSerializer
    """
    serializer_field_mapping = ext_serializer_field_mapping


class NestedDepthMixin:
    """
    扩展：
        自定义related field depth
        默认只能统一定义depth，不能控制不通的field depth

    usage:
        class Meta:
            depth = 1
            nested_depth = {
                'group': 0,
            }
    """

    def get_nested_depth_mapping(self) -> dict:

        _nested_depth_dict = getattr(self.Meta, "nested_depth", None)  # noqa
        if _nested_depth_dict and isinstance(_nested_depth_dict, dict):
            return _nested_depth_dict

        return {}

    def get_nested_depth(self, field_name, default=0) -> int:
        _nested_depth_dict = self.get_nested_depth_mapping()
        if field_name in _nested_depth_dict:
            return _nested_depth_dict[field_name]
        return default

    def build_field(self, field_name, info, model_class, nested_depth):
        if field_name not in info.fields_and_pk and field_name in info.relations:
            nested_depth = self.get_nested_depth(field_name, default=nested_depth)

        return super().build_field(field_name, info, model_class, nested_depth)  # noqa


class SelfRelatedMixin:
    """
    当关联model是自身的时候，调用本身serializer进行序列化
    默认是创建一个新的序列化器，无法控制字段等
    """

    def build_nested_field(self, field_name, relation_info, nested_depth):
        model = getattr(self.Meta, 'model')  # noqa
        # 自关联
        if model == relation_info.related_model:
            # related field 是 parent时，无需关心depth
            if relation_info.to_many:
                field_class = self.__class__
                field_kwargs = get_nested_relation_kwargs(relation_info)
                return field_class, field_kwargs

            return self.build_relational_field(field_name, relation_info)  # noqa

        return super().build_nested_field(field_name, relation_info, nested_depth)  # noqa


class ReverseRelationMixin:
    """
    获取反向关系字段
    usage:
        class Meta:
            fields = "__all__"
            reverse_related_fields = ["children"]
    """

    def get_default_field_names(self, declared_fields, model_info):
        field_names = super().get_default_field_names(declared_fields, model_info)  # noqa
        reverse_related_fields = getattr(self.Meta, "reverse_related_fields", None)  # noqa
        if reverse_related_fields and isinstance(reverse_related_fields, list | tuple):
            field_names += reverse_related_fields

        return field_names


class ModelSerializer(SelfRelatedMixin, NestedDepthMixin, ReverseRelationMixin, DrfModelSerializer):
    """
    扩展DRF中的`ModelSerializer`

    支持：
        - base64文件序列化
        - 关联字段depth控制
        - 自关联字段序列化（使用相同的序列化类进行序列化）
        - 反向关系字段默认可指定（fields = "__all__"时）
    """
    serializer_field_mapping = ext_serializer_field_mapping


ExtModelSerializer = ModelSerializer


class TreeSerializer(DrfSerializer):
    """
    将自关联的queryset转为tree结构

    和`SelfRelatedMixin`自关联所实现的区别在于，SelfRelatedMixin无法控制children数据，
    因为它的children数据是从反向关联字段中获取的，即children返回什么数据无法知道。
    而`TreeSerializer`只会在传入的queryset集合中进行查找，不去查找反向关联字段。

    注意：
    top参数仅支持和many一起使用，主要是用来在list serializer的时候进行筛选

    示例:
    class MenuSerializer(TreeSerializer):
        title = fields.CharField()

        class Meta:
            pk_field_name = "pk"
            parent_field_name = "parent"
            children_field_name = "children"

    MenuSerializer(queryset, many=True, top=None).data
    Todo: Meta字段使用不美丽，待优化
    Todo: 目前不支持反序列化，不支持和`ModelSerializer`搭配使用，待优化
    """

    @classmethod
    def filter(cls, instance: object, name: str, value: int) -> bool:

        field = getattr(instance, name, empty)
        if field is not empty:
            if isinstance(field, models.Model):
                field = getattr(field, "pk")

        return bool(field is not empty and field == value)

    @classmethod
    def metadata(cls, name: str, default: any) -> any:
        meta = getattr(cls, "Meta", None)
        if not meta:
            return default

        return getattr(meta, name, default)

    @classmethod
    def many_init(cls, origin_instance=None, **kwargs):
        top = kwargs.pop("top", None)
        parent_field_name = cls.metadata("parent_field_name", "parent")
        handler = partial(cls.filter, name=parent_field_name, value=top)
        instance = list(filter(handler, origin_instance))

        list_serializer = super().many_init(instance, **kwargs)
        list_serializer.child.origin_instance = origin_instance
        setattr(list_serializer, "top", top)
        return list_serializer

    def get_children_serializer(self, instance):
        pk_field_name = self.metadata("pk_field_name", "id")
        pk = getattr(instance, pk_field_name)

        return self.__class__(
            self.origin_instance,
            many=True,
            top=pk
        )

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        children_field_name = self.metadata("children_field_name", "children")
        parent_field_name = self.metadata("parent_field_name", "parent")

        if children_field_name not in ret:
            children_serializer = self.get_children_serializer(instance)
            ret[children_field_name] = children_serializer.data

        if parent_field_name not in ret:
            ret[parent_field_name] = self.parent.top

        return ret
