from django.contrib import admin
from .models import Student, Teacher, Subject, Class, Enrollment, Grade, Payment, Schedule, Invoice

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'full_name', 'gender', 'class_enrolled', 'academic_year')
    list_filter = ('gender', 'class_enrolled', 'academic_year')
    search_fields = ('student_id', 'full_name')

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('teacher_id', 'full_name', 'gender', 'email', 'phone')
    list_filter = ('gender',)
    search_fields = ('teacher_id', 'full_name', 'email')

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('subject_id', 'subject_name', 'credit')
    search_fields = ('subject_id', 'subject_name')

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('class_id', 'class_name', 'department', 'year')
    list_filter = ('department', 'year')
    search_fields = ('class_id', 'class_name')

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('enrollment_id', 'student', 'subject', 'semester', 'year')
    list_filter = ('semester', 'year')
    search_fields = ('enrollment_id', 'student__student_id', 'subject__subject_id')

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('grade_id', 'student', 'subject', 'score', 'grade')
    list_filter = ('grade',)
    search_fields = ('grade_id', 'student__student_id', 'subject__subject_id')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_id', 'student', 'amount', 'due_date', 'status')
    list_filter = ('status', 'due_date')
    search_fields = ('payment_id', 'student__student_id')

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'student', 'total_amount', 'issued_date', 'due_date', 'status')
    list_filter = ('status', 'issued_date', 'due_date')
    search_fields = ('invoice_number', 'student__student_id')

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('schedule_id', 'subject', 'class_enrolled', 'day_of_week', 'start_time', 'end_time', 'room')
    list_filter = ('day_of_week', 'class_enrolled')
    search_fields = ('schedule_id', 'subject__subject_name', 'class_enrolled__class_name')
