#!/usr/bin/env python
from typing import Union, Dict, Any
from datetime import datetime, timedelta
from authlib.jose import JsonWebToken
from authlib.jose import BaseClaims, JWTClaims
from authlib.jose.errors import JoseError as TokenError  # noqa
from authlib.jose.errors import ExpiredTokenError  # noqa

from rest_framework_fast.conf import settings


class TokenFactory:

    def __init__(self, secret_key: str = None, lifetime: Union[int, timedelta] = None):
        self.secret_key = self.get_secret_key(secret_key)
        self.lifetime = self.get_lifetime(lifetime)
        self.header = {
            'alg': settings.jwt_default_algo
        }
        self._jwt = JsonWebToken(settings.jwt_allowed_algo)

    def get_secret_key(self, secret_key: str = None) -> str:
        if not secret_key:
            from django.conf import settings
            return settings.SECRET_KEY

        return secret_key

    def get_lifetime(self, seconds: Union[int, timedelta] = None) -> timedelta:
        if not seconds:
            seconds = settings.jwt_lifetime

        if isinstance(seconds, int):
            seconds = timedelta(seconds=seconds)

        return seconds

    def encode(self, payload: Dict[str, Any]) -> str:
        if not payload.get("exp", None):
            payload["exp"] = self.get_expired_time()

        token = self._jwt.encode(self.header, payload, self.secret_key)
        if isinstance(token, bytes):
            token = token.decode('utf-8')

        return token

    def decode(self, token: str):
        payload: Union[BaseClaims, JWTClaims] = self._jwt.decode(token, self.secret_key)
        payload.validate(leeway=settings.jwt_leeway_seconds)
        exp = payload.get("exp", None)
        if exp and isinstance(exp, int):
            payload["exp"] = datetime.fromtimestamp(exp)

        return payload

    def get_expired_time(self, value: Union[int, datetime] = None) -> datetime:
        if value:
            if isinstance(value, int):
                return datetime.fromtimestamp(value)
            if isinstance(value, datetime):
                return value

        return datetime.now() + self.lifetime


jwt_token = TokenFactory()
