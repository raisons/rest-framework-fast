#!/usr/bin/env python
import copy
from typing import ClassVar, Type, Any, Dict, List
from pydantic import BaseModel, BaseConfig, Extra


class BaseSettings(BaseModel):
    """
    get user settings from `django.settings`
    """

    def __init__(__pydantic_self__) -> None:  # noqa
        super().__init__(**__pydantic_self__._build_values())

    def _build_values(self) -> Dict[str, Any]:
        from django.conf import settings as django_settings
        user_settings = getattr(django_settings, self.__config__.settings_keyword, None)
        if user_settings and isinstance(user_settings, dict):
            if not self.__config__.case_sensitive:
                return {k.lower(): v for k, v in user_settings.items()}

            return copy.deepcopy(user_settings)

        return {}

    class Config(BaseConfig):
        validate_all: bool = True
        extra: Extra = Extra.ignore
        arbitrary_types_allowed: bool = True
        settings_keyword: str = 'REST_FRAMEWORK_FAST'
        case_sensitive: bool = False

    __config__: ClassVar[Type[Config]] = Config


class Settings(BaseSettings):
    jwt_lifetime: int = 60 * 60 * 24
    jwt_allowed_algo: List[str] = ['HS256']
    jwt_default_algo: str = 'HS256'
    jwt_leeway_seconds: int = 0


settings = Settings()
