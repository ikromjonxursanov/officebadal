from rest_framework import viewsets

from apps.users.models import User
from apps.users.serializers import UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    search_fields = ('username', 'first_name', 'last_name', 'phone')
    ordering_fields = ('username', 'first_name')
