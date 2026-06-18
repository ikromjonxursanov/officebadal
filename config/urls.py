
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.contributions.views import MonthlyContributionViewSet, PaymentViewSet
from apps.duties.views import DutyAssignmentViewSet
from apps.expenses.views import ExpenseViewSet
from apps.users.views import UserViewSet


def api_root(request):
    return JsonResponse(
        {
            'message': 'OfficeBadal API is running',
            'admin': '/admin/',
            'api': '/api/',
        }
    )


router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'contributions', MonthlyContributionViewSet,
                basename='contribution')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'duties', DutyAssignmentViewSet, basename='duty')
router.register(r'expenses', ExpenseViewSet, basename='expense')

urlpatterns = [
    path('', api_root, name='api-root'),
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
]
