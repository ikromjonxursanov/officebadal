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
            'payment_card_number',
            'payment_card_holder',
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
            'payment_method',
            'status',
            'receipt_file_id',
            'receipt_image',
            'receipt_ocr_text',
            'reject_reason',
            'paid_month',
            'note',
            'paid_at'
        )
        read_only_fields = ('id', 'paid_at')
