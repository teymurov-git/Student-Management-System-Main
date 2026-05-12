from rest_framework.routers import DefaultRouter

from .views import MonthlyPaymentViewSet

router = DefaultRouter()
router.register(r"payments", MonthlyPaymentViewSet, basename="payment")

urlpatterns = router.urls
