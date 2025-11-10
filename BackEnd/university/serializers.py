from rest_framework import serializers
from .models import Student, Teacher, Subject, Class, Enrollment, Grade, Payment, Schedule, Invoice, Assessment, FinalGrade

class StudentSerializer(serializers.ModelSerializer):
    class_enrolled_name = serializers.CharField(source='class_enrolled.class_name', read_only=True)
    subjects = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = '__all__'

    def get_subjects(self, obj):
        enrollments = obj.enrollments.all()
        return [enrollment.subject.subject_name for enrollment in enrollments]

    def validate_student_id(self, value):
        if self.instance and self.instance.student_id != value:
            if Student.objects.filter(student_id=value).exists():
                raise serializers.ValidationError("Student ID must be unique.")
        elif not self.instance and Student.objects.filter(student_id=value).exists():
            raise serializers.ValidationError("Student ID must be unique.")
        return value

    def validate_date_of_birth(self, value):
        from datetime import date
        if value > date.today():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        return value

    def validate_academic_year(self, value):
        if value < 2000 or value > 2100:
            raise serializers.ValidationError("Academic year must be between 2000 and 2100.")
        return value

    def validate_class_enrolled(self, value):
        # Ensure class_enrolled is provided and valid
        if not value:
            raise serializers.ValidationError("Class enrollment is required.")
        return value

class TeacherSerializer(serializers.ModelSerializer):
    subjects = serializers.SerializerMethodField()
    subject_names = serializers.SerializerMethodField()
    classes = serializers.SerializerMethodField()
    class_names = serializers.SerializerMethodField()

    class Meta:
        model = Teacher
        fields = '__all__'

    def get_subjects(self, obj):
        return [subject.subject_id for subject in obj.subjects.all()]

    def get_subject_names(self, obj):
        return [subject.subject_name for subject in obj.subjects.all()]

    def get_classes(self, obj):
        return [cls.class_id for cls in obj.classes.all()]

    def get_class_names(self, obj):
        return [cls.class_name for cls in obj.classes.all()]

class SubjectSerializer(serializers.ModelSerializer):
    assigned_teachers = serializers.SerializerMethodField()
    assigned_classes = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = '__all__'

    def get_assigned_teachers(self, obj):
        return [teacher.teacher_id for teacher in obj.assigned_teachers.all()]

    def get_assigned_classes(self, obj):
        return [cls.class_id for cls in obj.assigned_classes.all()]

    def validate_subject_id(self, value):
        if self.instance and self.instance.subject_id != value:
            if Subject.objects.filter(subject_id=value).exists():
                raise serializers.ValidationError("Subject ID must be unique.")
        elif not self.instance and Subject.objects.filter(subject_id=value).exists():
            raise serializers.ValidationError("Subject ID must be unique.")
        return value

    def validate_credit(self, value):
        if value <= 0:
            raise serializers.ValidationError("Credit must be greater than 0.")
        return value

class ClassSerializer(serializers.ModelSerializer):
    subjects = serializers.SerializerMethodField()
    subject_names = serializers.SerializerMethodField()

    class Meta:
        model = Class
        fields = '__all__'

    def get_subjects(self, obj):
        return [subject.subject_id for subject in obj.subjects.all()]

    def get_subject_names(self, obj):
        return [subject.subject_name for subject in obj.subjects.all()]

    def validate_class_id(self, value):
        if self.instance and self.instance.class_id != value:
            if Class.objects.filter(class_id=value).exists():
                raise serializers.ValidationError("Class ID must be unique.")
        elif not self.instance and Class.objects.filter(class_id=value).exists():
            raise serializers.ValidationError("Class ID must be unique.")
        return value

    def validate_capacity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Capacity must be greater than 0.")
        return value

    def validate_year(self, value):
        if value < 2000 or value > 2100:
            raise serializers.ValidationError("Year must be between 2000 and 2100.")
        return value

class EnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = '__all__'

class AssessmentSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    class_name = serializers.CharField(source='class_enrolled.class_name', read_only=True)

    class Meta:
        model = Assessment
        fields = '__all__'

    def validate_weight(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Weight must be between 0 and 100.")
        return value

    def validate_max_score(self, value):
        if value <= 0:
            raise serializers.ValidationError("Max score must be greater than 0.")
        return value

class GradeSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    assessment_name = serializers.SerializerMethodField()
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)

    class Meta:
        model = Grade
        fields = '__all__'

    def get_assessment_name(self, obj):
        return obj.assessment.name if obj.assessment else None

    def validate_score(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Score must be between 0 and 100.")
        return value

class FinalGradeSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)

    class Meta:
        model = FinalGrade
        fields = '__all__'

class PaymentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)

    class Meta:
        model = Payment
        fields = '__all__'

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0.")
        return value

class InvoiceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    payment_details = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = '__all__'

    def get_payment_details(self, obj):
        return {
            'payment_id': obj.payment.payment_id,
            'amount': obj.payment.amount,
            'status': obj.payment.status,
        }

class ScheduleSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    class_name = serializers.CharField(source='class_enrolled.class_name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)

    class Meta:
        model = Schedule
        fields = '__all__'

    def validate(self, data):
        # Conflict detection
        schedule_id = self.instance.schedule_id if self.instance else None
        day_of_week = data.get('day_of_week')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        teacher = data.get('teacher')
        class_enrolled = data.get('class_enrolled')
        room = data.get('room')

        if start_time >= end_time:
            raise serializers.ValidationError("Start time must be before end time.")

        overlapping_schedules = Schedule.objects.filter(
            day_of_week=day_of_week,
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exclude(schedule_id=schedule_id)

        if overlapping_schedules.filter(teacher=teacher).exists():
            raise serializers.ValidationError(f"Teacher {teacher.full_name} has a conflicting schedule.")

        if overlapping_schedules.filter(class_enrolled=class_enrolled).exists():
            raise serializers.ValidationError(f"Class {class_enrolled.class_name} has a conflicting schedule.")

        if room and overlapping_schedules.filter(room=room).exists():
            raise serializers.ValidationError(f"Room {room} is already booked.")

        return data