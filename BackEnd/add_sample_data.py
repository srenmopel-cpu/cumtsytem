#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BackEnd.settings')
django.setup()

from university.models import Student, Teacher, Class, Subject, User
from django.contrib.auth.hashers import make_password

def add_sample_data():
    print("Adding sample data...")

    # Create a class
    class_obj, created = Class.objects.get_or_create(
        class_id='CS101',
        defaults={
            'class_name': 'Computer Science 101',
            'level': 'Undergraduate',
            'capacity': 30,
            'department': 'Computer Science',
            'year': 2024
        }
    )
    if created:
        print("Created class CS101")

    # Create a subject
    subject, created = Subject.objects.get_or_create(
        subject_id='CS101',
        defaults={
            'subject_name': 'Introduction to Programming',
            'credit': 3
        }
    )
    if created:
        print("Created subject CS101")

    # Create a teacher
    teacher_user, created = User.objects.get_or_create(
        username='teacher1',
        defaults={
            'email': 'teacher1@university.edu',
            'password': make_password('teacher123'),
            'role': 'Teacher',
            'first_name': 'John',
            'last_name': 'Doe',
            'is_active': True
        }
    )
    teacher, created = Teacher.objects.get_or_create(
        teacher_id='T001',
        defaults={
            'full_name': 'John Doe',
            'gender': 'Male',
            'phone': '123-456-7890',
            'email': 'john.doe@university.edu',
            'status': 'Active'
        }
    )
    if created:
        teacher.subjects.add(subject)
        print("Created teacher John Doe")

    # Create some students
    for i in range(1, 11):
        student_user, created = User.objects.get_or_create(
            username=f'student{i}',
            defaults={
                'email': f'student{i}@university.edu',
                'password': make_password('student123'),
                'role': 'Student',
                'first_name': f'Student{i}',
                'last_name': 'Test',
                'is_active': True
            }
        )
        from datetime import date
        student, created = Student.objects.get_or_create(
            student_id=f'S{i:03d}',
            defaults={
                'full_name': f'Student{i} Test',
                'gender': 'Male' if i % 2 == 0 else 'Female',
                'date_of_birth': date(2000 + i, 1, 1),
                'class_enrolled': class_obj,
                'academic_year': 2024,
                'address': f'Address {i}',
                'study_status': 'Active'
            }
        )
        if created:
            print(f"Created student {student.full_name}")

    print("Sample data added!")

if __name__ == '__main__':
    add_sample_data()