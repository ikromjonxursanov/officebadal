from rest_framework import serializers

from apps.contributions.models import MonthlyContribution, Payment


class MonthlyContributionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlyContribution
        fields = (
            'id',
            'month',
            'amount',
            'due_date',
            'is_active',
            'created_at'
        )
        read_only_fields = ('id', 'created_at')


class PaymentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    contribution = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Payment
        fields = (
            'id',
            'user',
            'contribution',
            'amount',
            'status',
            'payment_method',
            'submitted_at',
            'paid_at',
            'approved_by',
            'note'
        )
        read_only_fields = (
            'id',
            'submitted_at',
            'paid_at',
            'approved_by'
        )
