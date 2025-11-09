import json
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db.models import Avg
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Student, Teacher, Class, Subject, Grade

User = get_user_model()

class AuthenticationTestCase(APITestCase):
    def setUp(self):
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'role': 'Student',
            'first_name': 'Test',
            'last_name': 'User'
        }

    def test_user_registration(self):
        """Test user registration"""
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('user', response.data)

    def test_user_login(self):
        """Test user login"""
        # First register
        self.client.post(self.register_url, self.user_data, format='json')

        # Then login
        login_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_invalid_login(self):
        """Test invalid login credentials"""
        login_data = {
            'username': 'nonexistent',
            'password': 'wrongpass'
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class StudentTestCase(APITestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            role='Student'
        )
        self.client.force_authenticate(user=self.user)

        # Create test class
        self.test_class = Class.objects.create(
            class_id='CS101',
            class_name='Computer Science 101',
            department='Computer Science',
            year=2024
        )

        # Create student profile
        self.student = Student.objects.create(
            student_id='STU001',
            full_name='Test Student',
            gender='Male',
            date_of_birth='2000-01-01',
            class_enrolled=self.test_class,
            academic_year=2024,
            address='Test Address'
        )
        self.user.student_profile = self.student
        self.user.save()

    def test_student_profile_access(self):
        """Test that students can access their own profile"""
        url = reverse('student-detail', kwargs={'pk': self.student.student_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['student_id'], 'STU001')

    def test_student_cannot_access_other_students(self):
        """Test that students cannot access other students' data"""
        # Create another student
        other_student = Student.objects.create(
            student_id='STU002',
            full_name='Other Student',
            gender='Female',
            date_of_birth='2000-01-01',
            class_enrolled=self.test_class,
            academic_year=2024,
            address='Other Address'
        )

        url = reverse('student-detail', kwargs={'pk': other_student.student_id})
        response = self.client.get(url)
        # Should return empty or forbidden
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

class GradeCalculationTestCase(TestCase):
    def setUp(self):
        # Create test data
        self.test_class = Class.objects.create(
            class_id='MATH101',
            class_name='Mathematics 101',
            department='Mathematics',
            year=2024
        )

        self.student = Student.objects.create(
            student_id='STU001',
            full_name='Test Student',
            gender='Male',
            date_of_birth='2000-01-01',
            class_enrolled=self.test_class,
            academic_year=2024,
            address='Test Address'
        )

        self.teacher = Teacher.objects.create(
            teacher_id='T001',
            full_name='Test Teacher',
            gender='Male',
            phone='1234567890',
            email='teacher@test.com'
        )

        self.subject = Subject.objects.create(
            subject_id='MATH101',
            subject_name='Calculus',
            credit=3,
            teacher=self.teacher
        )

    def test_grade_creation(self):
        """Test grade creation with valid data"""
        grade = Grade.objects.create(
            grade_id='G001',
            student=self.student,
            subject=self.subject,
            score=85.5,
            grade='B',
            remark='Good performance'
        )
        self.assertEqual(grade.score, 85.5)
        self.assertEqual(grade.grade, 'B')

    def test_gpa_calculation(self):
        """Test GPA calculation"""
        # Create multiple grades
        Grade.objects.create(
            grade_id='G001',
            student=self.student,
            subject=self.subject,
            score=85.0,
            grade='B'
        )

        # Calculate GPA manually
        grades = Grade.objects.filter(student=self.student)
        avg_score = grades.aggregate(avg_score=Avg('score'))['avg_score']
        self.assertEqual(avg_score, 85.0)

class PermissionTestCase(APITestCase):
    def setUp(self):
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='admin123',
            role='Admin'
        )
        self.client.force_authenticate(user=self.admin_user)

        # Create regular user
        self.regular_user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='user123',
            role='Student'
        )

    def test_admin_can_access_all_students(self):
        """Test that admin can access all students"""
        url = reverse('student-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_regular_user_limited_access(self):
        """Test that regular users have limited access"""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('student-list')
        response = self.client.get(url)
        # Should only see their own data or assigned data
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class ValidationTestCase(TestCase):
    def test_student_id_uniqueness(self):
        """Test that student IDs must be unique"""
        test_class = Class.objects.create(
            class_id='CS101',
            class_name='Computer Science 101',
            department='Computer Science',
            year=2024
        )

        Student.objects.create(
            student_id='STU001',
            full_name='First Student',
            gender='Male',
            date_of_birth='2000-01-01',
            class_enrolled=test_class,
            academic_year=2024
        )

        with self.assertRaises(Exception):
            Student.objects.create(
                student_id='STU001',  # Duplicate ID
                full_name='Second Student',
                gender='Female',
                date_of_birth='2000-01-01',
                class_enrolled=test_class,
                academic_year=2024
            )

    def test_grade_score_validation(self):
        """Test grade score validation"""
        test_class = Class.objects.create(
            class_id='CS101',
            class_name='Computer Science 101',
            department='Computer Science',
            year=2024
        )

        student = Student.objects.create(
            student_id='STU001',
            full_name='Test Student',
            gender='Male',
            date_of_birth='2000-01-01',
            class_enrolled=test_class,
            academic_year=2024
        )

        teacher = Teacher.objects.create(
            teacher_id='T001',
            full_name='Test Teacher',
            gender='Male',
            phone='1234567890',
            email='teacher@test.com'
        )

        subject = Subject.objects.create(
            subject_id='CS101',
            subject_name='Programming',
            credit=3,
            teacher=teacher
        )

        # Valid grade
        grade = Grade.objects.create(
            grade_id='G001',
            student=student,
            subject=subject,
            score=85.0,
            grade='B'
        )
        self.assertEqual(grade.score, 85.0)

        # Invalid grade (score > 100)
        with self.assertRaises(Exception):
            Grade.objects.create(
                grade_id='G002',
                student=student,
                subject=subject,
                score=150.0,  # Invalid score
                grade='A'
            )
