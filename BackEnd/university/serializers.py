from rest_framework import serializers
from .models import Student, Teacher, Subject, Class, Enrollment, Grade, Payment, Schedule, Invoice, Assessment, FinalGrade, User, Role, Permission

class StudentSerializer(serializers.ModelSerializer):
    class_enrolled_name = serializers.SerializerMethodField()
    subjects = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = '__all__'

    def get_class_enrolled_name(self, obj):
        return obj.class_enrolled.class_name if obj.class_enrolled else ''

    def get_subjects(self, obj):
        enrollments = obj.enrollments.all()
        return [enrollment.subject.subject_name for enrollment in enrollments if enrollment.subject]

    def validate_student_id(self, value):
        if self.instance and self.instance.student_id != value:
            if Student.objects.filter(student_id=value).exists():
                raise serializers.ValidationError("Student ID must be unique.")
        elif not self.instance and Student.objects.filter(student_id=value).exists():
            raise serializers.ValidationError("Student ID must be unique.")
        return value



    def validate_class_enrolled(self, value):
        # Ensure class_enrolled is provided and valid
        if not value:
            raise serializers.ValidationError("Class enrollment is required.")
        return value

class TeacherSerializer(serializers.ModelSerializer):
    subjects = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)
    subject_names = serializers.SerializerMethodField()
    classes = serializers.SerializerMethodField()
    class_names = serializers.SerializerMethodField()
    profile_picture_url = serializers.SerializerMethodField()

    class Meta:
        model = Teacher
        fields = '__all__'

    def get_profile_picture_url(self, obj):
        if obj.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None

    def get_subjects(self, obj):
        return [subject.subject_id for subject in obj.subjects.all()]

    def get_subject_names(self, obj):
        return [subject.subject_name for subject in obj.subjects.all()]

    def get_classes(self, obj):
        return [cls.class_id for cls in obj.classes.all()]

    def get_class_names(self, obj):
        return [cls.class_name for cls in obj.classes.all()]

    def create(self, validated_data):
        subjects_data = validated_data.pop('subjects', [])
        teacher = super().create(validated_data)
        if subjects_data:
            subjects = []
            for subject_name in subjects_data:
                subject, created = Subject.objects.get_or_create(
                    subject_name=subject_name,
                    defaults={'subject_id': subject_name[:10], 'credit': 3}  # Default values
                )
                subjects.append(subject)
            teacher.subjects.set(subjects)
        return teacher

    def update(self, instance, validated_data):
        subjects_data = validated_data.pop('subjects', [])
        teacher = super().update(instance, validated_data)
        if subjects_data is not None:
            subjects = []
            for subject_name in subjects_data:
                subject, created = Subject.objects.get_or_create(
                    subject_name=subject_name,
                    defaults={'subject_id': subject_name[:10], 'credit': 3}
                )
                subjects.append(subject)
            teacher.subjects.set(subjects)
        return teacher

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
    student_id = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['payment_id']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0.")
        return value

    def create(self, validated_data):
        student_id = validated_data.pop('student_id')
        student = Student.objects.get(student_id=student_id)
        validated_data['student'] = student

        # Auto-generate payment_id
        last_payment = Payment.objects.order_by('-id').first()
        if last_payment:
            last_id = int(last_payment.payment_id[1:])  # Assuming format P000001
            new_id = f"P{last_id + 1:06d}"
        else:
            new_id = "P000001"
        validated_data['payment_id'] = new_id

        return super().create(validated_data)

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

class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SlugRelatedField(
        many=True,
        slug_field='name',
        queryset=Role.objects.all(),
        required=False
    )
    custom_permissions = serializers.SlugRelatedField(
        many=True,
        slug_field='name',
        queryset=Permission.objects.all(),
        required=False
    )
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    all_permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'role',
            'phone', 'address', 'date_of_birth', 'profile_picture',
            'is_active', 'is_staff', 'is_superuser', 'date_joined',
            'last_login', 'roles', 'custom_permissions', 'role_display',
            'all_permissions', 'is_2fa_enabled', 'last_login_ip'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login', 'last_login_ip']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def get_all_permissions(self, obj):
        return list(obj.get_all_permissions())

    def create(self, validated_data):
        roles_data = validated_data.pop('roles', [])
        custom_permissions_data = validated_data.pop('custom_permissions', [])
        password = validated_data.pop('password', None)
        role = validated_data.get('role')

        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()

        # Assign default role based on the role field
        if role and not roles_data:
            try:
                if role == 'Admin':
                    admin_role = Role.objects.get(name='Administrator')
                    user.roles.add(admin_role)
                elif role == 'Teacher':
                    teacher_role = Role.objects.get(name='Teacher')
                    user.roles.add(teacher_role)
                elif role == 'Student':
                    student_role = Role.objects.get(name='Student')
                    user.roles.add(student_role)
            except Role.DoesNotExist:
                pass  # Roles might not exist yet

        if roles_data:
            user.roles.set(roles_data)
        if custom_permissions_data:
            user.custom_permissions.set(custom_permissions_data)

        return user

    def update(self, instance, validated_data):
        roles_data = validated_data.pop('roles', [])
        custom_permissions_data = validated_data.pop('custom_permissions', [])
        role = validated_data.get('role')

        for attr, value in validated_data.items():
            if attr == 'password':
                instance.set_password(value)
            else:
                setattr(instance, attr, value)

        instance.save()

        # Update roles based on role field change
        if role is not None:
            instance.roles.clear()  # Clear existing roles
            try:
                if role == 'Admin':
                    admin_role = Role.objects.get(name='Administrator')
                    instance.roles.add(admin_role)
                elif role == 'Teacher':
                    teacher_role = Role.objects.get(name='Teacher')
                    instance.roles.add(teacher_role)
                elif role == 'Student':
                    student_role = Role.objects.get(name='Student')
                    instance.roles.add(student_role)
            except Role.DoesNotExist:
                pass

        if roles_data is not None:
            instance.roles.set(roles_data)
        if custom_permissions_data is not None:
            instance.custom_permissions.set(custom_permissions_data)

        return instance

class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.SlugRelatedField(
        many=True,
        slug_field='name',
        queryset=Permission.objects.all()
    )

    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'permissions', 'is_default']

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name', 'description']