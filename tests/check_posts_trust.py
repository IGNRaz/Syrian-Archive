#!/usr/bin/env python
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'syrian_archive.settings')
django.setup()

from archive_app.models import Post, PostTrust, User

def check_posts_and_trust():
    print("=== Posts and Trust Status ===")
    
    # Get all approved posts
    approved_posts = Post.objects.filter(status='approved')
    print(f"Total approved posts: {approved_posts.count()}")
    
    if approved_posts.exists():
        print("\n--- Approved Posts ---")
        for post in approved_posts[:5]:  # Show first 5
            trust_count = post.trusts.count()
            print(f"Post ID: {post.id}")
            print(f"Title: {post.title or 'No title'}")
            print(f"Author: {post.user.username}")
            print(f"Trust count: {trust_count}")
            print(f"Is verified: {post.is_verified}")
            
            if trust_count > 0:
                print("Trusted by:")
                for trust in post.trusts.all():
                    print(f"  - {trust.user.username} ({trust.user.role})")
            print("-" * 40)
    
    # Check users who can trust posts
    trusted_users = User.objects.filter(role__in=['admin', 'journalist', 'politician'])
    print(f"\nUsers who can trust posts: {trusted_users.count()}")
    for user in trusted_users:
        print(f"  - {user.username} ({user.role})")
    
    # Check total trust actions
    total_trusts = PostTrust.objects.count()
    print(f"\nTotal trust actions: {total_trusts}")

if __name__ == '__main__':
    check_posts_and_trust()