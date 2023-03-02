#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author  : chengshuang
# @Contact : chengshuang@qudoor.cn
# @File    : routers.py
# @Software: PyCharm
# @Time    : 2022/8/10 17:07

from django.views import View
from django.urls import path, include
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ViewSet
from rest_framework.routers import Route, DynamicRoute, DefaultRouter, BaseRouter, SimpleRouter


def format_prefix(f):
    def wrapper(self, prefix, *args, **kwargs):
        if not prefix == '':
            prefix = prefix.strip('/') + '/'

        return f(self, prefix, *args, **kwargs)

    return wrapper


class _APIRouter:
    pass


class PathMixin:
    """
    替换re_path为path
    """
    routes = [
        # List route.
        Route(url='{prefix}',
              mapping={'get': 'list', 'post': 'create'},
              name='{basename}-list',
              detail=False,
              initkwargs={'suffix': 'List'}),
        # Dynamically generated list routes. Generated using
        # @action(detail=False) decorator on methods of the viewset.
        DynamicRoute(url='{prefix}{url_path}',
                     name='{basename}-{url_name}',
                     detail=False,
                     initkwargs={}),
        # Detail route.
        Route(url='{prefix}{lookup}',
              mapping={'get': 'retrieve',
                       'put': 'update',
                       'patch': 'partial_update',
                       'delete': 'destroy'},
              name='{basename}-detail',
              detail=True,
              initkwargs={'suffix': 'Instance'}),
        # Dynamically generated detail routes. Generated using
        # @action(detail=True) decorator on methods of the viewset.
        DynamicRoute(url='{prefix}{lookup}/{url_path}',
                     name='{basename}-{url_name}',
                     detail=True,
                     initkwargs={}),
    ]

    def get_lookup(self, viewset, lookup_prefix=''):
        base = '<{lookup_type}:{lookup_prefix}{lookup_url_kwarg}>'
        lookup_field = getattr(viewset, 'lookup_field', 'pk')
        lookup_type = getattr(viewset, 'lookup_type', 'int')
        lookup_url_kwarg = getattr(viewset, 'lookup_url_kwarg', None) or lookup_field
        return base.format(
            lookup_type=lookup_type,
            lookup_prefix=lookup_prefix,
            lookup_url_kwarg=lookup_url_kwarg,
        )

    def format_slash(self, url):
        if url == '':
            return url
        elif url.endswith('/') and self.trailing_slash == '':
            url = url[:-1]
        elif not url.endswith('/') and self.trailing_slash == '/':
            url += '/'
        return url

    def get_urls(self):
        ret = []

        for prefix, viewset, basename in self.registry:
            lookup = self.get_lookup(viewset)
            routes = self.get_routes(viewset)

            for route in routes:

                # Only actions which actually exist on the viewset will be bound
                mapping = self.get_method_map(viewset, route.mapping)
                if not mapping:
                    continue

                _path = route.url.format(
                    prefix=prefix,
                    lookup=lookup,
                )
                _path = self.format_slash(_path)

                initkwargs = route.initkwargs.copy()
                initkwargs.update({
                    'basename': basename,
                    'detail': route.detail,
                })

                view = viewset.as_view(mapping, **initkwargs)
                name = route.name.format(basename=basename)
                ret.append(path(_path, view, name=name))

        return ret


class ViewMatcher:
    matched_classes = (View, APIView)

    def match(self, source):
        return isinstance(source, type) and issubclass(source, self.matched_classes)


class ViewSetMatcher:
    matched_classes = (GenericViewSet, ViewSet)

    def match(self, source):
        return isinstance(source, type) and issubclass(source, self.matched_classes)


class RouterMatcher:
    matched_classes = (_APIRouter,)

    def match(self, source):
        return isinstance(source, self.matched_classes)


class IncludeMatcher:
    matched_classes = (list, str)

    def match(self, source):
        return isinstance(source, self.matched_classes)


class ViewRouter(ViewMatcher, BaseRouter):

    def get_default_basename(self, view_cls):
        return None
        # raise ValueError('ViewRouter must be provided `basename` arg.')

    def get_urls(self):
        ret = []
        for prefix, view_class, basename in self.registry:
            slash = '' if prefix.endswith('/') else '/'
            ret.append(
                path(f'{prefix}', view_class.as_view(), name=basename)
            )
        return ret


class ViewSetRouter(ViewSetMatcher, PathMixin, SimpleRouter):

    def get_default_basename(self, viewset):
        """
        如果ViewSet已有属性basename，直接使用
        不从ViewSet.queryset中获取
        用来解决和model无关的ViewSet没有设置queryset而导致报错
        """
        if hasattr(viewset, 'basename') and viewset.basename:
            return viewset.basename
        return super().get_default_basename(viewset)


class IncludeRouter(IncludeMatcher, BaseRouter):

    def get_default_basename(self, viewset):
        pass

    def get_urls(self):
        ret = []
        for prefix, source, basename in self.registry:
            ret.append(
                path(f'{prefix}', include(source))
            )

        return ret


class Router(RouterMatcher, BaseRouter):
    def get_default_basename(self, router):
        pass

    def get_urls(self):
        ret = []
        for prefix, router, basename in self.registry:
            ret.append(
                path(f'{prefix}', include(router.urls))
            )

        return ret


class NestedRegistryItem:
    def __init__(self, router: ViewSetRouter, parent_prefix, parent_item=None, parent_viewset=None):
        self.router = router
        self.parent_prefix = parent_prefix
        self.parent_item = parent_item
        self.parent_viewset = parent_viewset
        self.parent_lookup = None

    @format_prefix
    def register(self, prefix, viewset, basename=None):
        self.parent_lookup = getattr(self.parent_viewset, 'lookup_url_kwarg', None)

        assert self.parent_lookup and self.parent_lookup != 'pk', (
                'In nested registration, '
                'the parent viewset `%s` must set the `.lookup_url_kwarg` attribute '
                'and the value cannot be set to `pk`.' %
                self.parent_viewset.__name__
        )
        self.router.register(
            prefix=self.get_prefix(current_prefix=prefix),
            viewset=viewset,
            basename=basename,
        )
        return NestedRegistryItem(
            router=self.router,
            parent_prefix=prefix,
            parent_item=self,
            parent_viewset=viewset
        )

    def get_prefix(self, current_prefix):
        return '{0}/{1}'.format(
            self.get_parent_prefix(),
            current_prefix
        )

    def get_parent_prefix(self):
        prefix = '/'
        current_item = self
        while current_item:
            parent_lookup_type = getattr(current_item.parent_viewset, 'lookup_type', 'int')
            prefix = '{parent_prefix}/<{parent_lookup_type}:{parent_lookup}>/{prefix}'.format(
                parent_prefix=current_item.parent_prefix,
                parent_lookup_type=parent_lookup_type,
                parent_lookup=current_item.parent_lookup,
                prefix=prefix
            )
            current_item = current_item.parent_item
        return prefix.strip('/')


class APIRouter(_APIRouter):
    router_classes = (ViewSetRouter, ViewRouter, IncludeRouter, Router)

    def __init__(self, name=None):
        self._routers = None

    def get_routers(self):
        if not self._routers:
            self._routers = [router() for router in self.router_classes]
        return self._routers

    def select(self, source):
        for router in self.get_routers():
            if router.match(source):
                return router

        raise ValueError(f'Not supported the view class: {source}')

    def clear(self):
        if hasattr(self, '_urls'):
            del self._urls

    @format_prefix
    def register(self, prefix, source, basename=None):
        self.clear()
        router = self.select(source)
        router.register(prefix, source, basename=basename)
        if isinstance(router, ViewSetRouter):
            # 只有viewset类型可以嵌套注册
            return NestedRegistryItem(
                router=router,
                parent_prefix=router.registry[-1][0],
                parent_viewset=router.registry[-1][1]
            )
        return None

    # def include(self, prefix=None, source=None, basename=None):
    #     self._register(prefix, source, basename)
    #     return self

    def get_urls(self):
        ret = []
        for router in self.get_routers():
            ret += router.urls
        return ret

    @property
    def urls(self):
        if not hasattr(self, '_urls'):
            self._urls = self.get_urls()
        return self._urls


ApiRouter = APIRouter

# Todo 增加一个类装饰器，用来注册路由
