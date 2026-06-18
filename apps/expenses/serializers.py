from rest_framework import serializers

from apps.expenses.models import Expense


class ExpenseSerializer(serializers.ModelSerializer):
    added_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Expense
        fields = (
            'id',
            'date',
            'category',
            'amount',
            'description',
            'added_by'
        )
        read_only_fields = ('id', 'date')
