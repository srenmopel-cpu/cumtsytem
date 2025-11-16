#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BackEnd.settings')
django.setup()

from university.models import User, Role, Permission
from django.contrib.auth.hashers import make_password

def setup_admin():
    print("Setting up admin user and permissions...")

    # Create permissions if they don't exist
    permissions_data = [
        ('view_student', 'View Student'),
        ('add_student', 'Add Student'),
        ('change_student', 'Change Student'),
        ('delete_student', 'Delete Student'),
        ('view_teacher', 'View Teacher'),
        ('add_teacher', 'Add Teacher'),
        ('change_teacher', 'Change Teacher'),
        ('delete_teacher', 'Delete Teacher'),
        ('view_user', 'View User'),
        ('add_user', 'Add User'),
        ('change_user', 'Change User'),
        ('delete_user', 'Delete User'),
        ('view_audit_log', 'View Audit Log'),
    ]

    for perm_name, perm_desc in permissions_data:
        Permission.objects.get_or_create(name=perm_name, defaults={'description': perm_desc})

    print(f"Created {len(permissions_data)} permissions")

    # Create roles
    admin_role, created = Role.objects.get_or_create(
        name='Administrator',
        defaults={'description': 'Full system access'}
    )

    if created:
        # Add all permissions to admin role
        permissions = Permission.objects.all()
        admin_role.permissions.set(permissions)
        print("Created Administrator role with all permissions")

    teacher_role, created = Role.objects.get_or_create(
        name='Teacher',
        defaults={'description': 'Teaching staff access'}
    )

    if created:
        # Add teacher-specific permissions
        teacher_permissions = Permission.objects.filter(
            name__in=['view_student', 'add_student', 'change_student', 'view_teacher', 'view_class', 'view_subject', 'view_grade', 'add_grade', 'change_grade']
        )
        teacher_role.permissions.set(teacher_permissions)
        print("Created Teacher role with teaching permissions")

    student_role, created = Role.objects.get_or_create(
        name='Student',
        defaults={'description': 'Student access'}
    )

    if created:
        # Add student-specific permissions (minimal)
        student_permissions = Permission.objects.filter(
            name__in=['view_student']  # Students can only view their own data
        )
        student_role.permissions.set(student_permissions)
        print("Created Student role with basic permissions")

    # Create admin user
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@university.edu',
            'password': make_password('admin123'),
            'role': 'Admin',
            'first_name': 'System',
            'last_name': 'Administrator',
            'is_staff': True,
            'is_superuser': True,
            'is_active': True
        }
    )
    admin_user.roles.add(admin_role)
    if created:
        print('Admin user created: username=admin, password=admin123')
    else:
        print('Admin user already exists, roles updated')

    print('Setup complete!')

if __name__ == '__main__':
    setup_admin()