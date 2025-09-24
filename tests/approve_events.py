#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'syrian_archive.settings')
django.setup()

from archive_app.models import Event, AuditLog, User

# Get admin user (assuming first admin user)
admin_user = User.objects.filter(role='admin').first()
if not admin_user:
    print("No admin user found. Please create an admin user first.")
    sys.exit(1)

# Get first 3 pending events and approve them
pending_events = Event.objects.filter(status='pending')[:3]

print(f"Found {pending_events.count()} pending events to approve")

for event in pending_events:
    old_status = event.status
    event.status = 'approved'
    event.save()
    
    # Create audit log
    AuditLog.objects.create(
        admin=admin_user,
        action_type='event_status_change',
        description=f'Changed event "{event.title}" status from {old_status} to approved'
    )
    
    print(f"✓ Approved event: {event.title}")

print("\nEvent approval completed!")

# Show updated counts
total_events = Event.objects.count()
pending_events = Event.objects.filter(status='pending').count()
approved_events = Event.objects.filter(status='approved').count()
rejected_events = Event.objects.filter(status='rejected').count()

print(f"\nUpdated event counts:")
print(f"Total events: {total_events}")
print(f"Pending events: {pending_events}")
print(f"Approved events: {approved_events}")
print(f"Rejected events: {rejected_events}")