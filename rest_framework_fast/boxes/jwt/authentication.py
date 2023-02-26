#!/usr/bin/env python

from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework import HTTP_HEADER_ENCODING
from rest_framework.exceptions import NotAuthenticated, AuthenticationFailed

from .token import jwt_token, TokenException


class BaseJwtAuthentication(BaseAuthentication):
    www_authenticate_realm = "api"
    media_type = "application/json"
    header_name = 'HTTP_AUTHORIZATION'
    header_prefix = 'Bearer'

    def authenticate_header(self, request):
        return 'JWT realm="%s"' % self.www_authenticate_realm

    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            raise NotAuthenticated()

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            raise AuthenticationFailed()

        validated_token = self.get_validated_token(raw_token)

        return self.get_user(validated_token), validated_token

    def get_header(self, request):
        header = request.META.get(self.header_name)
        if isinstance(header, str):
            header = header.encode(HTTP_HEADER_ENCODING)

        return header

    def get_raw_token(self, header):
        parts = header.split()

        if len(parts) == 0:
            return None

        if parts[0] != self.header_prefix.encode(HTTP_HEADER_ENCODING):
            return None

        if len(parts) != 2:
            raise AuthenticationFailed('bad header')

        return parts[1]

    def get_validated_token(self, raw_token):
        try:
            token = jwt_token.decode(raw_token)
        except TokenException:
            raise AuthenticationFailed()
        return token

    def get_user(self, validated_token):
        try:
            user_id = validated_token['user_id']
        except KeyError:
            raise AuthenticationFailed("Token contained no recognizable user identification")

        user_model = get_user_model()
        try:
            user = user_model.objects.get(id=user_id)
        except user_model.DoesNotExist:
            raise AuthenticationFailed("User not found", code="user_not_found")

        if not user.is_active:
            raise AuthenticationFailed("User is inactive", code="user_inactive")

        return user


class JwtAuthentication(BaseJwtAuthentication):

    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except (NotAuthenticated, AuthenticationFailed):
            return None, None
