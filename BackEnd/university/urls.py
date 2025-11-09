from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from django.views.decorators.csrf import csrf_exempt
from .views import (
    StudentViewSet, TeacherViewSet, SubjectViewSet,
    ClassViewSet, EnrollmentViewSet, GradeViewSet, PaymentViewSet, ScheduleViewSet, InvoiceViewSet,
    AssessmentViewSet, FinalGradeViewSet,
    login_view, register_view, logout_view, profile_view,
    password_reset_request_view, password_reset_confirm_view,
    enable_2fa_view, verify_2fa_view, disable_2fa_view,
    permissions_view, roles_view, assign_role_view, audit_logs_view, teachers_list_view
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

urlpatterns = [
    # Template-based views (put these first to avoid API conflicts)
    path('teachers/', teachers_list_view, name='teachers_list'),

    path('', include(router.urls)),
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
    path('auth/permissions/', permissions_view, name='permissions'),
    path('auth/roles/', roles_view, name='roles'),
    path('auth/assign-role/', assign_role_view, name='assign_role'),
    path('auth/audit-logs/', audit_logs_view, name='audit_logs'),
]