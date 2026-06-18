from rest_framework import viewsets

from apps.expenses.models import Expense
from apps.expenses.serializers import ExpenseSerializer


class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.select_related('added_by').all()
    serializer_class = ExpenseSerializer
    ordering = ('-date',)
