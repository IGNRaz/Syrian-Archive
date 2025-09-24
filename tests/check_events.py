#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'syrian_archive.settings')
django.setup()

from archive_app.models import Event

print(f'Total events: {Event.objects.count()}')
print(f'Pending events: {Event.objects.filter(status="pending").count()}')
print(f'Approved events: {Event.objects.filter(status="approved").count()}')
print(f'Rejected events: {Event.objects.filter(status="rejected").count()}')

events = Event.objects.all()[:10]
print('\nFirst 10 events:')
for event in events:
    created_by = event.created_by.username if event.created_by else 'Unknown'
    print(f'- {event.title} ({event.status}) - Date: {event.date} - Created by: {created_by}')

if Event.objects.count() == 0:
    print('\nNo events found in database!')