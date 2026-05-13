from rest_framework.routers import DefaultRouter

from .views import ExamResultViewSet, MonthlyExamScoreViewSet, MonthlyExamViewSet

router = DefaultRouter()
router.register(r"exams", ExamResultViewSet, basename="exam")
router.register(r"monthly-exams", MonthlyExamViewSet, basename="monthly-exam")
router.register(r"monthly-exam-scores", MonthlyExamScoreViewSet, basename="monthly-exam-score")

urlpatterns = router.urls
