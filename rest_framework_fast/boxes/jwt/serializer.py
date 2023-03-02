#!/usr/bin/env python

from django.contrib.auth import get_user_model
from rest_framework.serializers import Serializer
from rest_framework import fields
from rest_framework.exceptions import ValidationError
from rest_framework_fast.exceptions import ServerError
from .token import jwt_token, TokenError


class JwtSerializer(Serializer):  # noqa
    username = fields.CharField(required=True)
    password = fields.CharField(required=True)

    @staticmethod
    def get_user(attrs):
        user_model = get_user_model()
        try:
            user = user_model.objects.get(username=attrs["username"])
        except user_model.DoesNotExist:
            raise ValidationError(detail='User not found')

        return user

    @staticmethod
    def get_token(user) -> str:
        try:
            return jwt_token.encode({
                "user_id": user.id,
                "username": user.username,
            })
        except TokenError:
            raise ServerError("Token generated failed")

    def validate(self, attrs) -> dict:
        user = self.get_user(attrs)

        if not user.check_password(attrs["password"]):
            raise ValidationError(detail='Password incorrect')

        if not user.is_active:
            raise ValidationError(detail='User inactive')

        return {
            'token': self.get_token(user),
            'username': user.username,
            'user_id': user.id,
        }
