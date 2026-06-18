from rest_framework import serializers

from apps.duties.models import DutyAssignment


class DutyAssignmentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    duty_cycle = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = DutyAssignment
        fields = ('id', 'duty_cycle', 'user', 'month')
        read_only_fields = ('id',)
