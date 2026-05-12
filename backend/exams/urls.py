from rest_framework.routers import DefaultRouter

from .views import ExamResultViewSet

router = DefaultRouter()
router.register(r"exams", ExamResultViewSet, basename="exam")

urlpatterns = router.urls
