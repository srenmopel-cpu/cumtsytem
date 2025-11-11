from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Sum, Avg, Q
from django.contrib.auth.models import Group
from django.contrib.auth import authenticate
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import csv
import openpyxl
import pyotp
import qrcode
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from .models import Student, Teacher, Subject, Class, Enrollment, Grade, Payment, Schedule, User, Permission, Role, AuditLog, Invoice, Assessment, FinalGrade
from .serializers import (
    StudentSerializer, TeacherSerializer, SubjectSerializer,
    ClassSerializer, EnrollmentSerializer, GradeSerializer, PaymentSerializer, ScheduleSerializer, InvoiceSerializer,
    AssessmentSerializer, FinalGradeSerializer
)

def log_audit_action(user, action, model_name, object_id=None, details='', request=None):
    """Helper function to log audit actions"""
    ip_address = request.META.get('REMOTE_ADDR') if request else None
    user_agent = request.META.get('HTTP_USER_AGENT') if request else None

    AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=object_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent
    )

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # RBAC: Students can only see their own data, Teachers see their assigned students, Admins see all
        if user.role == 'Student':
            if user.student_profile:
                queryset = queryset.filter(student_id=user.student_profile.student_id)
            else:
                queryset = queryset.none()
        elif user.role == 'Teacher':
            if user.teacher_profile:
                # Teachers can see students in classes they teach
                teacher_subjects = user.teacher_profile.subjects.all()
                class_ids = Schedule.objects.filter(subject__in=teacher_subjects).values_list('class_enrolled', flat=True).distinct()
                queryset = queryset.filter(class_enrolled__class_id__in=class_ids)
            else:
                queryset = queryset.none()
        # Admins can see all students

        name = self.request.query_params.get('name')
        student_id = self.request.query_params.get('student_id')
        class_id = self.request.query_params.get('class_id')
        sort_by = self.request.query_params.get('sort_by', 'student_id')
        sort_order = self.request.query_params.get('sort_order', 'asc')

        if name:
            queryset = queryset.filter(full_name__icontains=name)
        if student_id:
            queryset = queryset.filter(student_id__icontains=student_id)
        if class_id:
            queryset = queryset.filter(class_enrolled__class_id=class_id)

        if sort_order == 'desc':
            sort_by = f'-{sort_by}'
        queryset = queryset.order_by(sort_by)

        return queryset

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit_action(self.request.user, 'CREATE', 'Student', instance.student_id, f'Created student {instance.full_name}', self.request)

    def perform_update(self, serializer):
        instance = serializer.save()
        log_audit_action(self.request.user, 'UPDATE', 'Student', instance.student_id, f'Updated student {instance.full_name}', self.request)

    def perform_destroy(self, instance):
        log_audit_action(self.request.user, 'DELETE', 'Student', instance.student_id, f'Deleted student {instance.full_name}', self.request)
        instance.delete()

    @action(detail=True, methods=['get'])
    def grades(self, request, pk=None):
        student = self.get_object()
        grades = Grade.objects.filter(student=student)
        serializer = GradeSerializer(grades, many=True)

        # Log view action
        log_audit_action(request.user, 'VIEW', 'Grade', f'student_{student.student_id}', f'Viewed grades for student {student.full_name}', request)

        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def gpa(self, request, pk=None):
        student = self.get_object()
        grades = Grade.objects.filter(student=student)
        if grades:
            avg = grades.aggregate(avg_score=Avg('score'))['avg_score']
            return Response({'gpa': avg})
        return Response({'gpa': None})

    @action(detail=True, methods=['get'])
    def profile(self, request, pk=None):
        student = self.get_object()
        grades = Grade.objects.filter(student=student)
        enrollments = Enrollment.objects.filter(student=student)
        subjects = [enrollment.subject for enrollment in enrollments]

        profile_data = {
            'student': StudentSerializer(student).data,
            'grades': GradeSerializer(grades, many=True).data,
            'subjects': SubjectSerializer(subjects, many=True).data,
            'gpa': grades.aggregate(avg_score=Avg('score'))['avg_score'] if grades else None,
        }
        return Response(profile_data)

    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        students = self.get_queryset()
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="students.csv"'

        writer = csv.writer(response)
        writer.writerow(['Student ID', 'Name', 'Gender', 'Class', 'Academic Year', 'Status'])
        for student in students:
            writer.writerow([
                student.student_id,
                student.full_name,
                student.gender,
                student.class_enrolled.class_name,
                student.academic_year,
                student.study_status,
            ])

        # Log export action
        log_audit_action(request.user, 'EXPORT', 'Student', None, f'Exported {students.count()} students to CSV', request)

        return response

    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        students = self.get_queryset()
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Students"

        ws.append(['Student ID', 'Name', 'Gender', 'Class', 'Academic Year', 'Status'])
        for student in students:
            ws.append([
                student.student_id,
                student.full_name,
                student.gender,
                student.class_enrolled.class_name,
                student.academic_year,
                student.study_status,
            ])

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="students.xlsx"'
        wb.save(response)
        return response

    @action(detail=True, methods=['get'])
    def export_profile_pdf(self, request, pk=None):
        student = self.get_object()
        grades = Grade.objects.filter(student=student)

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{student.student_id}_profile.pdf"'

        doc = SimpleDocTemplate(response, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        # Title
        elements.append(Paragraph(f"Student Profile: {student.full_name}", styles['Title']))

        # Student Info
        student_info = [
            ['Student ID', student.student_id],
            ['Name', student.full_name],
            ['Gender', student.gender],
            ['Class', student.class_enrolled.class_name],
            ['Academic Year', str(student.academic_year)],
            ['Status', student.study_status],
        ]
        student_table = Table(student_info)
        student_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), (0.8, 0.8, 0.8)),
            ('TEXTCOLOR', (0, 0), (-1, 0), (0, 0, 0)),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), (0.9, 0.9, 0.9)),
        ]))
        elements.append(student_table)
        elements.append(Paragraph("<br/>", styles['Normal']))

        # Grades
        if grades:
            elements.append(Paragraph("Academic Results", styles['Heading2']))
            grade_data = [['Subject', 'Score', 'Grade', 'Remark']]
            for grade in grades:
                grade_data.append([
                    grade.subject.subject_name,
                    str(grade.score),
                    grade.grade,
                    grade.remark or '',
                ])
            grade_table = Table(grade_data)
            grade_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), (0.8, 0.8, 0.8)),
                ('TEXTCOLOR', (0, 0), (-1, 0), (0, 0, 0)),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), (0.9, 0.9, 0.9)),
            ]))
            elements.append(grade_table)

            gpa = grades.aggregate(avg_score=Avg('score'))['avg_score']
            elements.append(Paragraph(f"GPA: {gpa:.2f}" if gpa else "GPA: N/A", styles['Normal']))

        doc.build(elements)
        return response

class TeacherViewSet(viewsets.ModelViewSet):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get('name')
        subject = self.request.query_params.get('subject')
        status = self.request.query_params.get('status')
        class_id = self.request.query_params.get('class_id')
        sort_by = self.request.query_params.get('sort_by', 'teacher_id')
        sort_order = self.request.query_params.get('sort_order', 'asc')

        if name:
            queryset = queryset.filter(full_name__icontains=name)
        if subject:
            queryset = queryset.filter(subjects__subject_name__icontains=subject)
        if status:
            queryset = queryset.filter(status=status)
        if class_id:
            queryset = queryset.filter(classes_in_charge__icontains=class_id)

        if sort_order == 'desc':
            sort_by = f'-{sort_by}'
        queryset = queryset.order_by(sort_by).distinct()

        return queryset

    @action(detail=True, methods=['get'])
    def subjects(self, request, pk=None):
        teacher = self.get_object()
        subjects = teacher.subjects.all()
        serializer = SubjectSerializer(subjects, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def schedules(self, request, pk=None):
        teacher = self.get_object()
        schedules = Schedule.objects.filter(subject__in=teacher.subjects.all())
        serializer = ScheduleSerializer(schedules, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def activity_log(self, request, pk=None):
        teacher = self.get_object()
        return Response({
            'created_at': teacher.created_at,
            'updated_at': teacher.updated_at,
            'last_login': teacher.last_login,
        })

class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def assign_teacher(self, request, pk=None):
        subject = self.get_object()
        teacher_id = request.data.get('teacher_id')
        try:
            teacher = Teacher.objects.get(teacher_id=teacher_id)
            subject.assigned_teachers.add(teacher)
            teacher.subjects.add(subject)
            return Response({'message': 'Teacher assigned to subject successfully'})
        except Teacher.DoesNotExist:
            return Response({'error': 'Teacher not found'}, status=404)

    @action(detail=True, methods=['post'])
    def assign_class(self, request, pk=None):
        subject = self.get_object()
        class_id = request.data.get('class_id')
        try:
            class_obj = Class.objects.get(class_id=class_id)
            subject.assigned_classes.add(class_obj)
            class_obj.subjects.add(subject)
            return Response({'message': 'Subject assigned to class successfully'})
        except Class.DoesNotExist:
            return Response({'error': 'Class not found'}, status=404)

class ClassViewSet(viewsets.ModelViewSet):
    queryset = Class.objects.all()
    serializer_class = ClassSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def assign_subject(self, request, pk=None):
        class_obj = self.get_object()
        subject_id = request.data.get('subject_id')
        teacher_id = request.data.get('teacher_id')
        try:
            subject = Subject.objects.get(subject_id=subject_id)
            teacher = Teacher.objects.get(teacher_id=teacher_id)
            class_obj.subjects.add(subject)
            subject.assigned_classes.add(class_obj)
            teacher.subjects.add(subject)
            subject.assigned_teachers.add(teacher)
            teacher.classes.add(class_obj)
            return Response({'message': 'Subject and teacher assigned to class successfully'})
        except Subject.DoesNotExist:
            return Response({'error': 'Subject not found'}, status=404)
        except Teacher.DoesNotExist:
            return Response({'error': 'Teacher not found'}, status=404)

    @action(detail=True, methods=['post'])
    def auto_assign_students(self, request, pk=None):
        class_obj = self.get_object()
        students = Student.objects.filter(class_enrolled=class_obj)
        subjects = class_obj.subjects.all()
        for student in students:
            for subject in subjects:
                Enrollment.objects.get_or_create(
                    student=student,
                    subject=subject,
                    defaults={'semester': 'Fall', 'year': class_obj.year}
                )
        return Response({'message': f'Subjects auto-assigned to {students.count()} students'})

    @action(detail=True, methods=['get'])
    def subjects(self, request, pk=None):
        class_obj = self.get_object()
        schedules = Schedule.objects.filter(class_enrolled=class_obj)
        serializer = ScheduleSerializer(schedules, many=True)
        return Response(serializer.data)

class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]

class AssessmentViewSet(viewsets.ModelViewSet):
    queryset = Assessment.objects.all()
    serializer_class = AssessmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        subject_id = self.request.query_params.get('subject_id')
        class_id = self.request.query_params.get('class_id')

        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        if class_id:
            queryset = queryset.filter(class_enrolled_id=class_id)

        return queryset

class GradeViewSet(viewsets.ModelViewSet):
    queryset = Grade.objects.all()
    serializer_class = GradeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        assessment_id = self.request.query_params.get('assessment_id')
        student_id = self.request.query_params.get('student_id')
        subject_id = self.request.query_params.get('subject_id')

        if assessment_id:
            queryset = queryset.filter(assessment_id=assessment_id)
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if subject_id:
            queryset = queryset.filter(assessment__subject_id=subject_id)

        return queryset

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        grades_data = request.data.get('grades', [])
        created_grades = []

        for grade_data in grades_data:
            serializer = GradeSerializer(data=grade_data)
            if serializer.is_valid():
                grade = serializer.save()
                created_grades.append(serializer.data)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(created_grades, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def grade_entry_grid(self, request):
        class_id = request.query_params.get('class_id')
        subject_id = request.query_params.get('subject_id')

        if not class_id or not subject_id:
            return Response({'error': 'class_id and subject_id are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            class_obj = Class.objects.get(class_id=class_id)
            subject = Subject.objects.get(subject_id=subject_id)
        except (Class.DoesNotExist, Subject.DoesNotExist):
            return Response({'error': 'Class or Subject not found'}, status=status.HTTP_404_NOT_FOUND)

        students = Student.objects.filter(class_enrolled=class_obj)
        assessments = Assessment.objects.filter(subject=subject, class_enrolled=class_obj)

        grid_data = []
        for student in students:
            student_grades = {}
            for assessment in assessments:
                try:
                    grade = Grade.objects.get(student=student, assessment=assessment)
                    student_grades[assessment.assessment_id] = {
                        'score': grade.score,
                        'grade': grade.grade,
                        'remark': grade.remark
                    }
                except Grade.DoesNotExist:
                    student_grades[assessment.assessment_id] = None

            grid_data.append({
                'student_id': student.student_id,
                'student_name': student.full_name,
                'grades': student_grades
            })

        return Response({
            'assessments': AssessmentSerializer(assessments, many=True).data,
            'grid_data': grid_data
        })

    @action(detail=False, methods=['post'])
    def update_grid(self, request):
        updates = request.data.get('updates', [])

        for update in updates:
            student_id = update.get('student_id')
            assessment_id = update.get('assessment_id')
            score = update.get('score')
            remark = update.get('remark', '')

            try:
                student = Student.objects.get(student_id=student_id)
                assessment = Assessment.objects.get(assessment_id=assessment_id)

                grade, created = Grade.objects.get_or_create(
                    student=student,
                    assessment=assessment,
                    defaults={'score': score, 'remark': remark}
                )

                if not created:
                    grade.score = score
                    grade.remark = remark
                    grade.save()

                # Calculate letter grade
                if score >= 90:
                    grade.grade = 'A'
                elif score >= 80:
                    grade.grade = 'B'
                elif score >= 70:
                    grade.grade = 'C'
                elif score >= 60:
                    grade.grade = 'D'
                else:
                    grade.grade = 'F'
                grade.save()

            except (Student.DoesNotExist, Assessment.DoesNotExist):
                continue

        return Response({'message': 'Grid updated successfully'})

    @action(detail=False, methods=['get'])
    def rankings(self, request):
        students = Student.objects.annotate(avg_score=Avg('grades__score')).order_by('-avg_score')
        data = [{'student_id': s.student_id, 'name': s.full_name, 'gpa': s.avg_score} for s in students if s.avg_score is not None]
        return Response(data)

    @action(detail=False, methods=['get'])
    def report(self, request):
        grades = Grade.objects.all()
        serializer = GradeSerializer(grades, many=True)
        return Response(serializer.data)

class FinalGradeViewSet(viewsets.ModelViewSet):
    queryset = FinalGrade.objects.all()
    serializer_class = FinalGradeSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def calculate_final_grades(self, request):
        subject_id = request.data.get('subject_id')
        semester = request.data.get('semester')
        year = request.data.get('year')

        if not subject_id or not semester or not year:
            return Response({'error': 'subject_id, semester, and year are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            subject = Subject.objects.get(subject_id=subject_id)
        except Subject.DoesNotExist:
            return Response({'error': 'Subject not found'}, status=status.HTTP_404_NOT_FOUND)

        students = Student.objects.filter(class_enrolled__subjects=subject)
        calculated_grades = []

        for student in students:
            result = FinalGrade.calculate_final_grade(student, subject, semester, year)
            if result:
                final_score, letter_grade = result
                final_grade, created = FinalGrade.objects.get_or_create(
                    student=student,
                    subject=subject,
                    semester=semester,
                    year=year,
                    defaults={
                        'final_score': final_score,
                        'final_grade': letter_grade
                    }
                )
                if not created:
                    final_grade.final_score = final_score
                    final_grade.final_grade = letter_grade
                    final_grade.save()

                calculated_grades.append(FinalGradeSerializer(final_grade).data)

        # Calculate rankings
        FinalGrade.calculate_ranks(subject, semester, year)

        return Response({
            'message': f'Calculated final grades for {len(calculated_grades)} students',
            'grades': calculated_grades
        })

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        subject_id = request.query_params.get('subject_id')
        semester = request.query_params.get('semester')
        year = request.query_params.get('year')

        queryset = FinalGrade.objects.all()
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        if semester:
            queryset = queryset.filter(semester=semester)
        if year:
            queryset = queryset.filter(year=year)

        if not queryset.exists():
            return Response({
                'average_score': None,
                'highest_score': None,
                'lowest_score': None,
                'total_students': 0,
                'pass_rate': 0
            })

        stats = queryset.aggregate(
            average_score=Avg('final_score'),
            highest_score=Max('final_score'),
            lowest_score=Min('final_score'),
            total_students=Count('id')
        )

        # Calculate pass rate (assuming passing grade is D or better)
        passing_grades = ['A', 'B', 'C', 'D']
        pass_count = queryset.filter(final_grade__in=passing_grades).count()
        pass_rate = (pass_count / stats['total_students']) * 100 if stats['total_students'] > 0 else 0

        return Response({
            'average_score': round(stats['average_score'], 2) if stats['average_score'] else None,
            'highest_score': stats['highest_score'],
            'lowest_score': stats['lowest_score'],
            'total_students': stats['total_students'],
            'pass_rate': round(pass_rate, 2)
        })

    @action(detail=False, methods=['get'])
    def export_report(self, request):
        subject_id = request.query_params.get('subject_id')
        semester = request.query_params.get('semester')
        year = request.query_params.get('year')
        format_type = request.query_params.get('format', 'pdf')

        queryset = FinalGrade.objects.filter(subject_id=subject_id, semester=semester, year=year).order_by('rank')

        if format_type == 'excel':
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Final Grades Report"

            ws.append(['Rank', 'Student ID', 'Student Name', 'Final Score', 'Final Grade'])

            for fg in queryset:
                ws.append([
                    fg.rank,
                    fg.student.student_id,
                    fg.student.full_name,
                    fg.final_score,
                    fg.final_grade
                ])

            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="final_grades_{subject_id}_{semester}_{year}.xlsx"'
            wb.save(response)
            return response

        elif format_type == 'pdf':
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="final_grades_{subject_id}_{semester}_{year}.pdf"'

            doc = SimpleDocTemplate(response, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []

            # Title
            elements.append(Paragraph(f"Final Grades Report - {semester} {year}", styles['Title']))
            elements.append(Paragraph(f"Subject: {queryset.first().subject.subject_name if queryset.exists() else 'N/A'}", styles['Heading2']))

            # Table
            data = [['Rank', 'Student ID', 'Name', 'Final Score', 'Grade']]
            for fg in queryset:
                data.append([
                    str(fg.rank),
                    fg.student.student_id,
                    fg.student.full_name,
                    str(round(fg.final_score, 2)),
                    fg.final_grade
                ])

            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), (0.8, 0.8, 0.8)),
                ('TEXTCOLOR', (0, 0), (-1, 0), (0, 0, 0)),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), (0.9, 0.9, 0.9)),
            ]))
            elements.append(table)

            doc.build(elements)
            return response

        else:
            return Response({'error': 'Invalid format. Use "pdf" or "excel"'}, status=status.HTTP_400_BAD_REQUEST)

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        student_id = self.request.query_params.get('student_id')
        status = self.request.query_params.get('status')
        payment_type = self.request.query_params.get('payment_type')

        if student_id:
            queryset = queryset.filter(student__student_id=student_id)
        if status:
            queryset = queryset.filter(status=status)
        if payment_type:
            queryset = queryset.filter(payment_type=payment_type)

        return queryset.order_by('-due_date')

    def perform_create(self, serializer):
        instance = serializer.save()
        # Auto-generate invoice when payment is created
        Invoice.objects.create(
            student=instance.student,
            payment=instance,
            total_amount=instance.amount,
            due_date=instance.due_date
        )
        log_audit_action(self.request.user, 'CREATE', 'Payment', instance.payment_id, f'Created payment for {instance.student.full_name}', self.request)

    def perform_update(self, serializer):
        instance = serializer.save()
        log_audit_action(self.request.user, 'UPDATE', 'Payment', instance.payment_id, f'Updated payment for {instance.student.full_name}', self.request)

    def perform_destroy(self, instance):
        log_audit_action(self.request.user, 'DELETE', 'Payment', instance.payment_id, f'Deleted payment for {instance.student.full_name}', self.request)
        instance.delete()

    @action(detail=False, methods=['get'])
    def total_paid(self, request):
        total = Payment.objects.filter(status='Paid').aggregate(total=Sum('amount'))['total'] or 0
        return Response({'total_paid': total})

    @action(detail=False, methods=['get'])
    def total_unpaid(self, request):
        total = Payment.objects.filter(status='Unpaid').aggregate(total=Sum('amount'))['total'] or 0
        return Response({'total_unpaid': total})

    @action(detail=False, methods=['get'])
    def total_overdue(self, request):
        from django.utils import timezone
        total = Payment.objects.filter(status='Overdue', due_date__lt=timezone.now().date()).aggregate(total=Sum('amount'))['total'] or 0
        return Response({'total_overdue': total})

    @action(detail=False, methods=['get'])
    def balance(self, request):
        paid = Payment.objects.filter(status='Paid').aggregate(total=Sum('amount'))['total'] or 0
        unpaid = Payment.objects.filter(status='Unpaid').aggregate(total=Sum('amount'))['total'] or 0
        overdue = Payment.objects.filter(status='Overdue').aggregate(total=Sum('amount'))['total'] or 0
        return Response({'paid': paid, 'unpaid': unpaid, 'overdue': overdue})

    @action(detail=False, methods=['get'])
    def monthly_income(self, request):
        from django.db.models.functions import TruncMonth
        data = Payment.objects.filter(status='Paid').annotate(
            month=TruncMonth('payment_date')
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')
        return Response(list(data))

    @action(detail=False, methods=['get'])
    def overdue_students(self, request):
        from django.utils import timezone
        overdue_payments = Payment.objects.filter(
            status__in=['Unpaid', 'Overdue'],
            due_date__lt=timezone.now().date()
        ).select_related('student')
        data = []
        for payment in overdue_payments:
            data.append({
                'student_id': payment.student.student_id,
                'student_name': payment.student.full_name,
                'amount': payment.amount,
                'due_date': payment.due_date,
                'days_overdue': (timezone.now().date() - payment.due_date).days
            })
        return Response(data)

class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        student_id = self.request.query_params.get('student_id')
        status = self.request.query_params.get('status')

        if student_id:
            queryset = queryset.filter(student__student_id=student_id)
        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by('-issued_date')

    @action(detail=True, methods=['get'])
    def download_pdf(self, request, pk=None):
        invoice = self.get_object()

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'

        doc = SimpleDocTemplate(response, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        # Title
        elements.append(Paragraph(f"Invoice: {invoice.invoice_number}", styles['Title']))

        # Invoice Info
        invoice_info = [
            ['Invoice Number', invoice.invoice_number],
            ['Student', invoice.student.full_name],
            ['Student ID', invoice.student.student_id],
            ['Total Amount', f"${invoice.total_amount}"],
            ['Issued Date', invoice.issued_date.strftime('%Y-%m-%d')],
            ['Due Date', invoice.due_date.strftime('%Y-%m-%d')],
            ['Status', invoice.status],
        ]
        invoice_table = Table(invoice_info)
        invoice_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), (0.8, 0.8, 0.8)),
            ('TEXTCOLOR', (0, 0), (-1, 0), (0, 0, 0)),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), (0.9, 0.9, 0.9)),
        ]))
        elements.append(invoice_table)

        doc.build(elements)
        return response

class ScheduleViewSet(viewsets.ModelViewSet):
    queryset = Schedule.objects.all()
    serializer_class = ScheduleSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # Use serializer validation for conflict detection
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=['get'])
    def conflicts(self, request):
        day_of_week = request.query_params.get('day_of_week')
        start_time = request.query_params.get('start_time')
        end_time = request.query_params.get('end_time')
        room = request.query_params.get('room')
        teacher_id = request.query_params.get('teacher_id')
        class_id = request.query_params.get('class_id')

        conflicts = []
        if day_of_week and start_time and end_time:
            base_filter = Q(
                day_of_week=day_of_week,
                start_time__lt=end_time,
                end_time__gt=start_time
            )

            if room:
                room_conflicts = Schedule.objects.filter(base_filter & Q(room=room))
                conflicts.extend([f"Room {room} conflict: {s.subject_name} ({s.start_time}-{s.end_time})" for s in room_conflicts])

            if teacher_id:
                teacher_conflicts = Schedule.objects.filter(base_filter & Q(teacher_id=teacher_id))
                conflicts.extend([f"Teacher conflict: {s.subject_name} ({s.start_time}-{s.end_time})" for s in teacher_conflicts])

            if class_id:
                class_conflicts = Schedule.objects.filter(base_filter & Q(class_enrolled_id=class_id))
                conflicts.extend([f"Class conflict: {s.subject_name} ({s.start_time}-{s.end_time})" for s in class_conflicts])

        return Response({'conflicts': conflicts})

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response({'error': 'Username and password are required'}, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(username=username, password=password)
    if user is not None:
        refresh = RefreshToken.for_user(user)
        user.last_login_ip = request.META.get('REMOTE_ADDR')
        user.save(update_fields=['last_login_ip'])

        # Log login action
        log_audit_action(user, 'LOGIN', 'User', str(user.id), f'User {user.username} logged in', request)

        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
        })
    else:
        # Log failed login attempt
        log_audit_action(None, 'LOGIN', 'User', None, f'Failed login attempt for username: {username}', request)
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    role = request.data.get('role')
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')

    if not username or not email or not password or not role:
        return Response({'error': 'All fields are required'}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(email=email).exists():
        return Response({'error': 'Email already exists'}, status=status.HTTP_400_BAD_REQUEST)

    if role not in ['Admin', 'Teacher', 'Student']:
        return Response({'error': 'Invalid role'}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        role=role,
        first_name=first_name,
        last_name=last_name
    )

    refresh = RefreshToken.for_user(user)
    return Response({
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'first_name': user.first_name,
            'last_name': user.last_name
        }
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'message': 'Successfully logged out'})
    except Exception as e:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    user = request.user
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'phone': user.phone,
        'address': user.address,
        'date_of_birth': user.date_of_birth,
        'last_login_ip': user.last_login_ip,
        'created_at': user.created_at,
        'updated_at': user.updated_at
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_request_view(request):
    email = request.data.get('email')
    if not email:
        return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
        # Generate reset token (simplified for demo)
        from django.utils.crypto import get_random_string
        reset_token = get_random_string(32)
        user.reset_token = reset_token
        user.save()

        # In production, send email here
        print(f"Password reset token for {email}: {reset_token}")

        return Response({'message': 'Password reset email sent'})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm_view(request):
    token = request.data.get('token')
    new_password = request.data.get('new_password')

    if not token or not new_password:
        return Response({'error': 'Token and new password are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(reset_token=token)
        user.set_password(new_password)
        user.reset_token = None
        user.save()
        return Response({'message': 'Password reset successfully'})
    except User.DoesNotExist:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enable_2fa_view(request):
    user = request.user
    if user.is_2fa_enabled:
        return Response({'error': '2FA is already enabled'}, status=status.HTTP_400_BAD_REQUEST)

    # Generate TOTP secret
    totp = pyotp.TOTP(pyotp.random_base32())
    user.two_factor_secret = totp.secret
    user.save()

    # Generate QR code
    uri = totp.provisioning_uri(name=user.email, issuer_name='University System')
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')

    # Convert to bytes
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    return Response({
        'secret': totp.secret,
        'qr_code': buffer.getvalue().decode('latin1')  # Simplified for demo
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_2fa_view(request):
    user = request.user
    code = request.data.get('code')

    if not user.two_factor_secret:
        return Response({'error': '2FA not set up'}, status=status.HTTP_400_BAD_REQUEST)

    totp = pyotp.TOTP(user.two_factor_secret)
    if totp.verify(code):
        user.is_2fa_enabled = True
        user.save()
        return Response({'message': '2FA enabled successfully'})
    else:
        return Response({'error': 'Invalid code'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def disable_2fa_view(request):
    user = request.user
    user.is_2fa_enabled = False
    user.two_factor_secret = None
    user.save()
    return Response({'message': '2FA disabled successfully'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def permissions_view(request):
    user = request.user
    permissions = user.get_all_permissions()
    return Response({'permissions': list(permissions)})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def roles_view(request):
    if not request.user.has_permission('view_user'):
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    roles = Role.objects.all()
    data = []
    for role in roles:
        data.append({
            'id': role.id,
            'name': role.name,
            'description': role.description,
            'permissions': [perm.name for perm in role.permissions.all()],
            'is_default': role.is_default
        })
    return Response(data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_role_view(request):
    if not request.user.has_permission('change_user'):
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    user_id = request.data.get('user_id')
    role_id = request.data.get('role_id')

    try:
        user = User.objects.get(id=user_id)
        role = Role.objects.get(id=role_id)
        user.roles.add(role)
        return Response({'message': 'Role assigned successfully'})
    except (User.DoesNotExist, Role.DoesNotExist):
        return Response({'error': 'User or role not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def audit_logs_view(request):
    if not request.user.has_permission('view_audit_log'):
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    user_filter = request.query_params.get('user')
    action_filter = request.query_params.get('action')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')

    logs = AuditLog.objects.all()

    if user_filter:
        logs = logs.filter(user__username__icontains=user_filter)
    if action_filter:
        logs = logs.filter(action=action_filter)
    if date_from:
        logs = logs.filter(timestamp__gte=date_from)
    if date_to:
        logs = logs.filter(timestamp__lte=date_to)

    logs = logs.order_by('-timestamp')[:100]  # Limit to last 100 entries

    data = []
    for log in logs:
        data.append({
            'id': log.id,
            'user': log.user.username if log.user else 'Anonymous',
            'action': log.action,
            'model_name': log.model_name,
            'object_id': log.object_id,
            'details': log.details,
            'ip_address': log.ip_address,
            'timestamp': log.timestamp
        })

    return Response(data)

# Template-based view for teachers list
def teachers_list_view(request):
    """Django template view for displaying teachers list"""
    # For demo purposes, allow unauthenticated access to this view
    # In production, you would add proper authentication
    teachers = Teacher.objects.all().order_by('full_name')

    # Add subject names to each teacher for template display
    for teacher in teachers:
        teacher.subject_names = [subject.subject_name for subject in teacher.subjects.all()]

    context = {
        'teachers': teachers,
    }

    return render(request, 'teachers.html', context)
