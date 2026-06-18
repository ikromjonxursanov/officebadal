from rest_framework import viewsets

from apps.duties.models import DutyAssignment
from apps.duties.serializers import DutyAssignmentSerializer


class DutyAssignmentViewSet(viewsets.ModelViewSet):
    queryset = DutyAssignment.objects.select_related(
        'user', 'duty_cycle').all()
    serializer_class = DutyAssignmentSerializer
    ordering = ('month',)
