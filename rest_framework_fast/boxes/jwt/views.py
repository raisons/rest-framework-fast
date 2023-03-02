#!/usr/bin/env python

from rest_framework.generics import GenericAPIView
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from .serializer import JwtSerializer


class LoginView(GenericAPIView):
    """
    login view
    """
    permission_classes = ()
    authentication_classes = ()
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)
    www_authenticate_realm = "api"

    serializer_class = JwtSerializer

    def get_authenticate_header(self, request):
        return 'JWT realm="{}"'.format(
            self.www_authenticate_realm,
        )

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)
