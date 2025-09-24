#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'syrian_archive.settings')
django.setup()

from archive_app.models import User

# Check if admin exists
admin = User.objects.filter(role='admin').first()
if admin:
    print(f'Admin user already exists: {admin.username}')
else:
    # Create admin user
    admin = User.objects.create_user(
        username='testadmin',
        email='admin@test.com',
        password='testpass123',
        role='admin'
    )
    print(f'Created admin user: {admin.username}')