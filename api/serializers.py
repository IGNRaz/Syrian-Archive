from rest_framework import serializers
from archive_app.models import (
    User, Post, Comment, Like, PostTrust, PostReport, PostVerification,
    Person, Event, VerificationRequest, Profile
)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'profile_picture', 'identity_confirmed', 'is_active',
            'date_joined', 'is_banned'
        ]
        read_only_fields = ['id', 'date_joined', 'is_banned', 'identity_confirmed']


class ProfileSerializer(serializers.ModelSerializer):
    """Serializer for Profile model"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Profile
        fields = ['user', 'bio']


class PersonSerializer(serializers.ModelSerializer):
    """Serializer for Person model"""
    added_by = UserSerializer(read_only=True)
    
    class Meta:
        model = Person
        fields = ['id', 'name', 'role', 'image', 'added_by', 'status', 'created_at']
        read_only_fields = ['id', 'added_by', 'created_at']


class EventSerializer(serializers.ModelSerializer):
    """Serializer for Event model"""
    created_by = UserSerializer(read_only=True)
    participants = PersonSerializer(many=True, read_only=True)
    journalists = UserSerializer(many=True, read_only=True)
    
    class Meta:
        model = Event
        fields = [
            'id', 'title', 'description', 'date', 'created_by',
            'participants', 'journalists', 'status'
        ]
        read_only_fields = ['id', 'created_by']


class CommentSerializer(serializers.ModelSerializer):
    """Serializer for Comment model"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'post', 'user', 'content', 'attachment', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class LikeSerializer(serializers.ModelSerializer):
    """Serializer for Like model"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Like
        fields = ['id', 'post', 'user', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class PostTrustSerializer(serializers.ModelSerializer):
    """Serializer for PostTrust model"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = PostTrust
        fields = ['id', 'post', 'user', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class PostVerificationSerializer(serializers.ModelSerializer):
    """Serializer for PostVerification model"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = PostVerification
        fields = ['id', 'post', 'user', 'type', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class PostReportSerializer(serializers.ModelSerializer):
    """Serializer for PostReport model"""
    user = UserSerializer(read_only=True)
    handled_by_admin = UserSerializer(read_only=True)
    
    class Meta:
        model = PostReport
        fields = [
            'id', 'post', 'user', 'reason', 'status', 'created_at', 'handled_by_admin'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'handled_by_admin']


class PostSerializer(serializers.ModelSerializer):
    """Serializer for Post model"""
    user = UserSerializer(read_only=True)
    event = EventSerializer(read_only=True)
    people = PersonSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    likes = LikeSerializer(many=True, read_only=True)
    trusts = PostTrustSerializer(many=True, read_only=True)
    verifications = PostVerificationSerializer(many=True, read_only=True)
    reports = PostReportSerializer(many=True, read_only=True)
    
    # Count fields
    likes_count = serializers.SerializerMethodField()
    trusts_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = [
            'id', 'user', 'event', 'people', 'title', 'content', 'attachment',
            'status', 'report_count', 'is_verified', 'created_at',
            'comments', 'likes', 'trusts', 'verifications', 'reports',
            'likes_count', 'trusts_count', 'comments_count'
        ]
        read_only_fields = [
            'id', 'user', 'created_at', 'report_count', 'is_verified',
            'comments', 'likes', 'trusts', 'verifications', 'reports'
        ]
    
    def get_likes_count(self, obj):
        return obj.likes.count()
    
    def get_trusts_count(self, obj):
        return obj.trusts.count()
    
    def get_comments_count(self, obj):
        return obj.comments.count()


class PostCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating posts"""
    class Meta:
        model = Post
        fields = ['title', 'content', 'attachment', 'event']


class VerificationRequestSerializer(serializers.ModelSerializer):
    """Serializer for VerificationRequest model"""
    user = UserSerializer(read_only=True)
    handled_by_admin = UserSerializer(read_only=True)
    
    class Meta:
        model = VerificationRequest
        fields = [
            'id', 'user', 'requested_role', 'uid_document', 'created_at',
            'status', 'handled_by_admin'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'handled_by_admin']