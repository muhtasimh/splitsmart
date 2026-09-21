from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from expenses.views import (
    UserViewSet,
    GroupViewSet,
    ExpenseViewSet,
    SettlementViewSet,
    dashboard,
    me,
)
from rest_framework.authtoken.views import obtain_auth_token

router = DefaultRouter()
router.register("users", UserViewSet)
router.register("groups", GroupViewSet)
router.register("expenses", ExpenseViewSet)
router.register("settlements", SettlementViewSet)

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("api/me/", me, name="me"),
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api/token/", obtain_auth_token),
]