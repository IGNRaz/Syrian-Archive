from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

# --------------------
# Users
# --------------------
class User(AbstractUser):
    ROLE_CHOICES = [
        ('normal', 'Normal User'),
        ('journalist', 'Journalist'),
        ('politician', 'Politician'),
        ('admin', 'Admin'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='normal')
    uid_document = models.FileField(upload_to='uid_docs/', null=True, blank=True)
    intended_role = models.CharField(max_length=20, choices=[('journalist', 'Journalist'), ('politician', 'Politician')], null=True, blank=True, help_text='Role requested during UID upload')
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    identity_confirmed = models.BooleanField(default=False) 
    is_banned = models.BooleanField(default=False)  # User ban status
    ban_reason = models.TextField(blank=True, null=True)  # Reason for ban
    banned_at = models.DateTimeField(blank=True, null=True)  # When user was banned
    banned_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='banned_users')  # Admin who banned the user

    def __str__(self):
        return self.username

# --------------------
# Profile
# --------------------
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.username}"

# --------------------
# Person
# --------------------
class Person(models.Model):
    ROLE_CHOICES = [
        ('victim', 'Victim'),
        ('witness', 'Witness'),
        ('perpetrator', 'Perpetrator'),
        ('journalist', 'Journalist'),
        ('activist', 'Activist'),
        ('official', 'Official'),
        ('other', 'Other'),
    ]
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    image = models.ImageField(upload_to='people/', blank=True, null=True)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='person_requests')
    status = models.CharField(max_length=20, choices=[('pending','Pending'), ('approved','Approved')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.role})"

# --------------------
# Event
# --------------------
class Event(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    date = models.DateField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='event_requests')
    participants = models.ManyToManyField(Person, blank=True, related_name='events')
    journalists = models.ManyToManyField(User, blank=True, limit_choices_to={'role':'journalist'}, related_name='journalist_events')
    status = models.CharField(max_length=20, choices=[('pending','Pending'),('approved','Approved')], default='pending')

    def __str__(self):
        return self.title

# --------------------
# Post
# --------------------
class Post(models.Model):
    STATUS_CHOICES = [
        ('pending_review', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('removed', 'Removed'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts")
    people = models.ManyToManyField(Person, blank=True, related_name="posts")
    title = models.CharField(max_length=255, blank=True, null=True)
    content = models.TextField()
    attachment = models.FileField(upload_to='posts/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_review')
    report_count = models.PositiveIntegerField(default=0)
    is_verified = models.BooleanField(default=False)  # Post verification status
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Auto-verify and approve posts by admins and politicians
        if self.user.role in ['admin', 'politician'] and not self.pk:
            self.is_verified = True
            self.status = 'approved'
        # Auto-approve posts by ANY identity-verified user
        elif self.user.identity_confirmed and not self.pk:
            self.status = 'approved'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Post {self.id} by {self.user.username}"

# --------------------
# Comment
# --------------------
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    content = models.TextField(blank=True, null=True)
    attachment = models.FileField(upload_to='comments/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on Post {self.post.id}"

# --------------------
# Post Verification
# --------------------
class PostVerification(models.Model):
    VERIFY_CHOICES = [
        ('journalist_confirm', 'Journalist Confirm'),
        ('politician_confirm', 'Politician Confirm'),
    ]
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="verifications")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="verifications")
    type = models.CharField(max_length=30, choices=VERIFY_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post','user','type')

    def __str__(self):
        return f"{self.type} by {self.user.username} on Post {self.post.id}"

# --------------------
# Post Report
# --------------------
class PostReport(models.Model):
    REASON_CHOICES = [
        ('spam','Spam'),
        ('fake_news','Fake News'),
        ('offensive','Offensive Content'),
        ('other','Other'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('dismissed', 'Dismissed'),
        ('resolved', 'Resolved'),
    ]
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reports")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reports")
    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    handled_by_admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='handled_reports')

    def __str__(self):
        return f"Report by {self.user.username} on Post {self.post.id} ({self.reason})"

# --------------------
# Like
# --------------------
class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post','user')

    def __str__(self):
        return f"{self.user.username} likes {self.post.id}"

# --------------------
# PostTrust
# --------------------
class PostTrust(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="trusts")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="trusts")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post','user')

    def __str__(self):
        return f"{self.user.username} trusts {self.post.id}"

# --------------------
# Verification Request
# --------------------
class VerificationRequest(models.Model):
    ROLE_CHOICES = [
        ('journalist', 'Journalist'),
        ('politician', 'Politician'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    requested_role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    uid_document = models.ImageField(upload_to='documents/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='pending')
    handled_by_admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='handled_verifications')

    def __str__(self):
        return f"{self.user.username} → {self.requested_role} ({self.status})"

# --------------------
# Admin Audit Log
# --------------------
class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('role_change', 'Role Change'),
        ('post_status', 'Post Status Change'),
        ('post_deleted', 'Post Deleted'),
        ('report_handled', 'Report Handled'),
        ('verification_handled', 'Verification Handled'),
        ('user_banned', 'User Banned'),
        ('user_unbanned', 'User Unbanned'),
        ('user_deleted', 'User Deleted'),
        ('person_deleted', 'Person Deleted'),
        ('person_status_change', 'Person Status Change'),
        ('person_role_change', 'Person Role Change'),
        ('event_status_change', 'Event Status Change'),
    ]
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audit_logs')
    action_type = models.CharField(max_length=50, choices=ACTION_CHOICES)
    target_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_target_user')
    target_post = models.ForeignKey(Post, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_target_post')
    report = models.ForeignKey(PostReport, on_delete=models.SET_NULL, null=True, blank=True)
    verification_request = models.ForeignKey(VerificationRequest, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True, null=True)  # Additional details about the action
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.admin.username} performed {self.action_type} at {self.created_at}"

# --------------------
# IP Ban Model
# --------------------
class IPBan(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    reason = models.TextField(blank=True, null=True)
    banned_at = models.DateTimeField(auto_now_add=True)
    banned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ip_bans_created')
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"IP Ban: {self.ip_address}"
    
    class Meta:
        verbose_name = "IP Ban"
        verbose_name_plural = "IP Bans"
        ordering = ['-banned_at']

# --------------------
# Signals
# --------------------
User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
