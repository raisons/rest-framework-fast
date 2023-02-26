#!/usr/bin/env python

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.serializers import Serializer
from rest_framework import fields

from rest_framework_fast.token import JsonWebToken, InvalidToken


class JwtSerializer(Serializer):
    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass

    username_field = 'username'
    password_field = 'password'
    username_field_class = fields.CharField
    password_field_class = fields.CharField

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.fields.get(self.username_field, None):
            self.fields[self.username_field] = self.username_field_class()
        if not self.fields.get(self.password_field, None):
            self.fields[self.password_field] = self.password_field_class()

    def handle_user_not_found(self):
        raise InvalidToken(detail='User not found.')

    def handle_user_not_authenticated(self, user):
        raise InvalidToken()

    def handle_user_not_active(self, user):
        raise InvalidToken(detail='User inactive.')

    def check_user(self, user):
        pass

    def get_user(self, attrs):
        username = attrs[self.username_field]

        query = {self.username_field: username}
        user_model = get_user_model()
        try:
            user = user_model.objects.get(**query)
        except user_model.DoesNotExist:
            user = self.handle_user_not_found()

        return user

    def validate(self, attrs):
        user = self.get_user(attrs)
        password = attrs[self.password_field]

        if not user.check_password(password):
            self.handle_user_not_authenticated(user)

        if not user.is_active:
            self.handle_user_not_active(user)

        self.check_user(user)

        token = self.get_token(user)

        return {
            'token': token.access_token,
            'username': user.username,
            'user_id': user.id,
        }

    @classmethod
    def get_token(cls, user):
        return JsonWebToken.for_user(user, settings.SECRET_KEY)
