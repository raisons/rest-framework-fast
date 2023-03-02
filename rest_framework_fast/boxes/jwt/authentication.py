#!/usr/bin/env python

from django.contrib.auth import get_user_model
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .token import jwt_token, TokenError, ExpiredTokenError


class JwtAuthentication(TokenAuthentication):
    keyword = "Bearer"

    def authenticate_credentials(self, token: str) -> tuple:
        try:
            payload = jwt_token.decode(token)
        except ExpiredTokenError:
            raise AuthenticationFailed("Token expired")
        except TokenError:
            raise AuthenticationFailed("Invalid token")

        user_model = get_user_model()
        try:
            user_id = payload['user_id']
            user = user_model.objects.get(id=user_id)
        except user_model.DoesNotExist:
            raise AuthenticationFailed("User not found")

        if not user.is_active:
            raise AuthenticationFailed("User inactive")

        return user, payload
