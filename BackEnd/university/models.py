from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password

class Permission(models.Model):
    PERMISSION_CHOICES = [
        ('view_student', 'View Student'),
        ('add_student', 'Add Student'),
        ('change_student', 'Change Student'),
        ('delete_student', 'Delete Student'),
        ('view_teacher', 'View Teacher'),
        ('add_teacher', 'Add Teacher'),
        ('change_teacher', 'Change Teacher'),
        ('delete_teacher', 'Delete Teacher'),
        ('view_class', 'View Class'),
        ('add_class', 'Add Class'),
        ('change_class', 'Change Class'),
        ('delete_class', 'Delete Class'),
        ('view_subject', 'View Subject'),
        ('add_subject', 'Add Subject'),
        ('change_subject', 'Change Subject'),
        ('delete_subject', 'Delete Subject'),
        ('view_grade', 'View Grade'),
        ('add_grade', 'Add Grade'),
        ('change_grade', 'Change Grade'),
        ('delete_grade', 'Delete Grade'),
        ('view_payment', 'View Payment'),
        ('add_payment', 'Add Payment'),
        ('change_payment', 'Change Payment'),
        ('delete_payment', 'Delete Payment'),
        ('view_schedule', 'View Schedule'),
        ('add_schedule', 'Add Schedule'),
        ('change_schedule', 'Change Schedule'),
        ('delete_schedule', 'Delete Schedule'),
        ('view_user', 'View User'),
        ('add_user', 'Add User'),
        ('change_user', 'Change User'),
        ('delete_user', 'Delete User'),
        ('view_audit_log', 'View Audit Log'),
    ]

    name = models.CharField(max_length=50, choices=PERMISSION_CHOICES, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.get_name_display()

    class Meta:
        db_table = 'permissions'

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, related_name='roles')
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'roles'

class User(AbstractUser):
    ROLE_CHOICES = [
        ('Admin', 'Admin'),
        ('Teacher', 'Teacher'),
        ('Student', 'Student'),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='Student')
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    is_2fa_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=32, blank=True, null=True)
    reset_token = models.CharField(max_length=32, blank=True, null=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # RBAC fields
    roles = models.ManyToManyField(Role, related_name='users', blank=True)
    custom_permissions = models.ManyToManyField(Permission, related_name='users', blank=True)

    # Link to specific models based on role
    student_profile = models.OneToOneField('Student', on_delete=models.SET_NULL, blank=True, null=True, related_name='user_account')
    teacher_profile = models.OneToOneField('Teacher', on_delete=models.SET_NULL, blank=True, null=True, related_name='user_account')

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith('pbkdf2_sha256$'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def has_permission(self, permission_name):
        # Check custom permissions
        if self.custom_permissions.filter(name=permission_name).exists():
            return True

        # Check role permissions
        for role in self.roles.all():
            if role.permissions.filter(name=permission_name).exists():
                return True

        return False

    def get_all_permissions(self):
        permissions = set()

        # Add custom permissions
        for perm in self.custom_permissions.all():
            permissions.add(perm.name)

        # Add role permissions
        for role in self.roles.all():
            for perm in role.permissions.all():
                permissions.add(perm.name)

        return permissions

    def __str__(self):
        return f"{self.username} - {self.role}"

    class Meta:
        db_table = 'users'

class Class(models.Model):
    class_id = models.CharField(max_length=10, primary_key=True)
    class_name = models.CharField(max_length=50)
    level = models.CharField(max_length=50, default='Undergraduate')
    capacity = models.IntegerField(default=30)
    department = models.CharField(max_length=100)
    year = models.IntegerField()
    subjects = models.ManyToManyField('Subject', related_name='assigned_classes', blank=True)

    def __str__(self):
        return f"{self.class_id} - {self.class_name}"

    class Meta:
        db_table = 'classes'

class Teacher(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
    ]

    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('On Leave', 'On Leave'),
        ('Retired', 'Retired'),
    ]

    teacher_id = models.CharField(max_length=10, primary_key=True)
    full_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=6, choices=GENDER_CHOICES)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    subjects = models.ManyToManyField('Subject', related_name='assigned_teachers', blank=True)
    classes = models.ManyToManyField('Class', related_name='assigned_teachers', blank=True)
    classes_in_charge = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.teacher_id} - {self.full_name}"

    class Meta:
        db_table = 'teachers'

class Subject(models.Model):
    subject_id = models.CharField(max_length=10, primary_key=True)
    subject_name = models.CharField(max_length=100)
    credit = models.IntegerField()

    def __str__(self):
        return f"{self.subject_id} - {self.subject_name}"

    class Meta:
        db_table = 'subjects'

class Assessment(models.Model):
    ASSESSMENT_TYPE_CHOICES = [
        ('Exam', 'Exam'),
        ('Quiz', 'Quiz'),
        ('Assignment', 'Assignment'),
        ('Project', 'Project'),
        ('Other', 'Other'),
    ]

    assessment_id = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=100)
    assessment_type = models.CharField(max_length=20, choices=ASSESSMENT_TYPE_CHOICES, default='Exam')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='assessments')
    class_enrolled = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='assessments')
    weight = models.FloatField(help_text="Weight in percentage (e.g., 50 for 50%)")
    date = models.DateField(blank=True, null=True)
    max_score = models.FloatField(default=100)

    def __str__(self):
        return f"{self.assessment_id} - {self.name} ({self.subject.subject_name})"

    class Meta:
        db_table = 'assessments'

class Student(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]

    STUDY_STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
        ('Suspended', 'Suspended'),
    ]

    student_id = models.CharField(max_length=10, primary_key=True)
    full_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=6, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    class_enrolled = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='students')
    academic_year = models.IntegerField()
    address = models.TextField()
    study_status = models.CharField(max_length=10, choices=STUDY_STATUS_CHOICES, default='Active')

    def __str__(self):
        return f"{self.student_id} - {self.full_name}"

    class Meta:
        db_table = 'students'

class Enrollment(models.Model):
    enrollment_id = models.CharField(max_length=10, primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='enrollments')
    semester = models.CharField(max_length=20)
    year = models.IntegerField()

    def __str__(self):
        return f"{self.enrollment_id}"

    class Meta:
        db_table = 'enrollments'

class Grade(models.Model):
    grade_id = models.CharField(max_length=10, primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='grades')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='grades')
    score = models.FloatField()
    grade = models.CharField(max_length=2)
    remark = models.TextField(blank=True, null=True)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='grades', null=True, blank=True)

    def __str__(self):
        return f"{self.grade_id} - {self.grade}"

    class Meta:
        db_table = 'grades'

    @property
    def class_enrolled(self):
        return self.student.class_enrolled

class Payment(models.Model):
    STATUS_CHOICES = [
        ('Paid', 'Paid'),
        ('Unpaid', 'Unpaid'),
        ('Overdue', 'Overdue'),
    ]

    PAYMENT_TYPE_CHOICES = [
        ('Online', 'Online'),
        ('Offline', 'Offline'),
    ]

    payment_id = models.CharField(max_length=10, primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(blank=True, null=True)
    due_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=7, choices=STATUS_CHOICES, default='Unpaid')
    payment_type = models.CharField(max_length=7, choices=PAYMENT_TYPE_CHOICES, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.payment_id} - {self.status}"

    class Meta:
        db_table = 'payments'

class Invoice(models.Model):
    STATUS_CHOICES = [
        ('Generated', 'Generated'),
        ('Sent', 'Sent'),
        ('Paid', 'Paid'),
        ('Overdue', 'Overdue'),
    ]

    invoice_number = models.CharField(max_length=20, unique=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='invoices')
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='invoice')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    issued_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    status = models.CharField(max_length=9, choices=STATUS_CHOICES, default='Generated')
    notes = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            # Auto-generate invoice number
            last_invoice = Invoice.objects.order_by('-id').first()
            if last_invoice:
                last_num = int(last_invoice.invoice_number.split('-')[1])
                self.invoice_number = f"INV-{last_num + 1:06d}"
            else:
                self.invoice_number = "INV-000001"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice_number} - {self.student.full_name}"

    class Meta:
        db_table = 'invoices'

class Schedule(models.Model):
    DAYS_OF_WEEK = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    ]

    schedule_id = models.CharField(max_length=10, primary_key=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='schedules')
    class_enrolled = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='schedules')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='schedules', null=True, blank=True)
    day_of_week = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.subject.subject_name} - {self.class_enrolled.class_name} - {self.day_of_week}"

    class Meta:
        db_table = 'schedules'

    def clean(self):
        # Conflict detection: Check for overlapping schedules
        from django.core.exceptions import ValidationError
        overlapping_schedules = Schedule.objects.filter(
            day_of_week=self.day_of_week,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time
        ).exclude(schedule_id=self.schedule_id)

        # Check for same teacher
        if overlapping_schedules.filter(teacher=self.teacher).exists():
            raise ValidationError(f"Teacher {self.teacher.full_name} has a conflicting schedule.")

        # Check for same class
        if overlapping_schedules.filter(class_enrolled=self.class_enrolled).exists():
            raise ValidationError(f"Class {self.class_enrolled.class_name} has a conflicting schedule.")

        # Check for same room
        if self.room and overlapping_schedules.filter(room=self.room).exists():
            raise ValidationError(f"Room {self.room} is already booked.")

class FinalGrade(models.Model):
    final_grade_id = models.CharField(max_length=10, primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='final_grades')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='final_grades')
    final_score = models.FloatField()
    final_grade = models.CharField(max_length=2)
    rank = models.IntegerField(blank=True, null=True)
    semester = models.CharField(max_length=20)
    year = models.IntegerField()

    def __str__(self):
        return f"{self.final_grade_id} - {self.final_grade}"

    class Meta:
        db_table = 'final_grades'
        unique_together = ('student', 'subject', 'semester', 'year')

    @staticmethod
    def calculate_final_grade(student, subject, semester, year):
        assessments = Assessment.objects.filter(subject=subject, class_enrolled=student.class_enrolled)
        total_weighted_score = 0
        total_weight = 0

        for assessment in assessments:
            try:
                grade = Grade.objects.get(student=student, assessment=assessment)
                weighted_score = (grade.score / assessment.max_score) * assessment.weight
                total_weighted_score += weighted_score
                total_weight += assessment.weight
            except Grade.DoesNotExist:
                continue

        if total_weight == 0:
            return None

        final_score = (total_weighted_score / total_weight) * 100

        # Determine letter grade
        if final_score >= 90:
            letter_grade = 'A'
        elif final_score >= 80:
            letter_grade = 'B'
        elif final_score >= 70:
            letter_grade = 'C'
        elif final_score >= 60:
            letter_grade = 'D'
        else:
            letter_grade = 'F'

        return final_score, letter_grade

    @staticmethod
    def calculate_ranks(subject, semester, year):
        final_grades = FinalGrade.objects.filter(subject=subject, semester=semester, year=year).order_by('-final_score')
        rank = 1
        for fg in final_grades:
            fg.rank = rank
            fg.save()
            rank += 1

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('VIEW', 'View'),
        ('EXPORT', 'Export'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=50)
    object_id = models.CharField(max_length=50, blank=True, null=True)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username if self.user else 'Anonymous'} - {self.action} - {self.model_name}"

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
