#!/usr/bin/env python
from django.conf import settings
from datetime import datetime, timedelta
from authlib.jose import JsonWebToken as _JsonWebToken
from authlib.jose.errors import DecodeError

ALLOWED_ALGO = ['HS256']
DEFAULT_LIFETIME = 60 * 60 * 24
jwt = _JsonWebToken(ALLOWED_ALGO)


class InvalidToken(Exception):
    pass


class TokenExpired(InvalidToken):
    pass


class JsonWebToken:

    def __init__(self, token=None, secret_key=None):
        self.payload = {}
        self.token = token
        self.now = datetime.now()
        self.secret_key = secret_key
        self.lifetime = timedelta(seconds=getattr(settings, "TOKEN_LIFETIME", DEFAULT_LIFETIME))

        if token is not None:
            try:
                self.payload = self.decode()
                self.set_exp(self.payload['exp'])
            except DecodeError:
                raise InvalidToken()

            self.verify()
        else:
            # New token.  Skip all the verification steps.
            self.set_exp()

    def set_exp(self, value=None):
        if value:
            if isinstance(value, int):
                self.payload['exp'] = datetime.fromtimestamp(value)
            if isinstance(value, datetime):
                self.payload['exp'] = value
        else:
            self.payload['exp'] = self.now + self.lifetime

    def check_exp(self):
        exp = self.payload['exp']
        if exp <= self.now - self.lifetime:
            raise TokenExpired()

    def verify(self):
        self.check_exp()

    def get(self, key, default=None):
        return self.payload.get(key, default)

    def encode(self):
        header = {
            'alg': 'HS256'
        }
        token_str = jwt.encode(header, self.payload, self.secret_key)
        if isinstance(token_str, bytes):
            token_str = token_str.decode('utf-8')
        return token_str

    def decode(self):
        return jwt.decode(self.token, self.secret_key)

    def __repr__(self):
        return repr(self.payload)

    def __getitem__(self, key):
        return self.payload[key]

    def __setitem__(self, key, value):
        self.payload[key] = value

    def __delitem__(self, key):
        del self.payload[key]

    def __contains__(self, key):
        return key in self.payload

    @property
    def access_token(self):
        return self.encode()

    @classmethod
    def for_user(cls, user, secret_key):
        token = cls(secret_key=secret_key)
        token['username'] = user.username
        token['user_id'] = user.id
        return token
