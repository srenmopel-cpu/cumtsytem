from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from django.views.decorators.csrf import csrf_exempt
from .views import (
    StudentViewSet, TeacherViewSet, SubjectViewSet,
    ClassViewSet, EnrollmentViewSet, GradeViewSet, PaymentViewSet, ScheduleViewSet, InvoiceViewSet,
    AssessmentViewSet, FinalGradeViewSet, UserViewSet,
    login_view, register_view, logout_view, profile_view,
    password_reset_request_view, password_reset_confirm_view,
    enable_2fa_view, verify_2fa_view, disable_2fa_view,
    teachers_list_view,
    system_stats_view, system_backup_view, system_settings_view, update_system_settings_view,
    send_notification_view, system_health_view
)

router = DefaultRouter()
router.register(r'students', StudentViewSet)
router.register(r'teachers', TeacherViewSet)
router.register(r'subjects', SubjectViewSet)
router.register(r'classes', ClassViewSet)
router.register(r'enrollments', EnrollmentViewSet)
router.register(r'grades', GradeViewSet)
router.register(r'payments', PaymentViewSet)
router.register(r'invoices', InvoiceViewSet)
router.register(r'schedules', ScheduleViewSet)
router.register(r'assessments', AssessmentViewSet)
router.register(r'final-grades', FinalGradeViewSet)
router.register(r'users', UserViewSet)

urlpatterns = [
    path('', include(router.urls)),

    # Template-based views (put after API routes to avoid conflicts)
    path('teachers/', teachers_list_view, name='teachers_list'),
    path('auth/login/', login_view, name='login'),
    path('auth/register/', register_view, name='register'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/profile/', profile_view, name='profile'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/password-reset/', password_reset_request_view, name='password_reset_request'),
    path('auth/password-reset-confirm/', password_reset_confirm_view, name='password_reset_confirm'),
    path('auth/2fa/enable/', enable_2fa_view, name='enable_2fa'),
    path('auth/2fa/verify/', verify_2fa_view, name='verify_2fa'),
    path('auth/2fa/disable/', disable_2fa_view, name='disable_2fa'),
    path('admin/system-stats/', system_stats_view, name='system_stats'),
    path('admin/backup/', system_backup_view, name='system_backup'),
    path('admin/settings/', system_settings_view, name='system_settings'),
    path('admin/settings/update/', update_system_settings_view, name='update_system_settings'),
    path('admin/notifications/send/', send_notification_view, name='send_notification'),
    path('admin/health/', system_health_view, name='system_health'),
]