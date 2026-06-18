from rest_framework import viewsets

from apps.contributions.models import MonthlyContribution, Payment
from apps.contributions.serializers import MonthlyContributionSerializer, PaymentSerializer


class MonthlyContributionViewSet(viewsets.ModelViewSet):
    queryset = MonthlyContribution.objects.all()
    serializer_class = MonthlyContributionSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    ordering = ('-paid_at',)
