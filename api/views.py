from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q

from archive_app.models import (
    User, Post, Comment, Like, PostTrust, PostReport, PostVerification,
    Person, Event, VerificationRequest, Profile
)
from .serializers import (
    UserSerializer, PostSerializer, PostCreateSerializer, CommentSerializer,
    LikeSerializer, PostTrustSerializer, PostReportSerializer,
    PostVerificationSerializer, PersonSerializer, EventSerializer,
    VerificationRequestSerializer, ProfileSerializer
)


# Authentication Views
class LoginAPIView(APIView):
    """API view for user login"""
    permission_classes = []
    
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {'error': 'Username and password required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = authenticate(username=username, password=password)
        if user:
            if user.is_banned:
                return Response(
                    {'error': 'Account is banned'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data
            })
        
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )


class UserProfileAPIView(generics.RetrieveUpdateAPIView):
    """API view for user profile"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class UserListAPIView(generics.ListAPIView):
    """API view for listing users"""
    queryset = User.objects.filter(is_active=True, is_banned=False)
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class UserDetailAPIView(generics.RetrieveAPIView):
    """API view for user details"""
    queryset = User.objects.filter(is_active=True, is_banned=False)
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


# Post Views
class PostListCreateAPIView(generics.ListCreateAPIView):
    """API view for listing and creating posts"""
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = Post.objects.filter(status='approved').order_by('-created_at')
        
        # Filter by search query
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(content__icontains=search)
            )
        
        # Filter by user
        user_id = self.request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filter by event
        event_id = self.request.query_params.get('event')
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        
        return queryset
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PostCreateSerializer
        return PostSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PostDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """API view for post details"""
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            # Only allow modification of own posts
            return Post.objects.filter(user=self.request.user)
        return Post.objects.filter(status='approved')


class MyPostsAPIView(generics.ListAPIView):
    """API view for user's own posts"""
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Post.objects.filter(user=self.request.user).order_by('-created_at')


# Comment Views
class CommentListCreateAPIView(generics.ListCreateAPIView):
    """API view for listing and creating comments"""
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        post_id = self.kwargs.get('post_id')
        return Comment.objects.filter(post_id=post_id).order_by('-created_at')
    
    def perform_create(self, serializer):
        post_id = self.kwargs.get('post_id')
        post = get_object_or_404(Post, id=post_id, status='approved')
        serializer.save(user=self.request.user, post=post)


class CommentDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """API view for comment details"""
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Comment.objects.filter(user=self.request.user)


# Like Views
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_like(request, post_id):
    """API view to toggle like on a post"""
    post = get_object_or_404(Post, id=post_id, status='approved')
    
    like, created = Like.objects.get_or_create(
        post=post,
        user=request.user
    )
    
    if not created:
        like.delete()
        return Response({'liked': False, 'likes_count': post.likes.count()})
    
    return Response({'liked': True, 'likes_count': post.likes.count()})


# Trust Views
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_trust(request, post_id):
    """API view to toggle trust on a post"""
    post = get_object_or_404(Post, id=post_id, status='approved')
    
    # Check if user can verify posts
    if request.user.role not in ['admin', 'journalist', 'politician']:
        return Response(
            {'error': 'Only admins, journalists, and politicians can verify posts'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    trust, created = PostTrust.objects.get_or_create(
        post=post,
        user=request.user
    )
    
    if not created:
        trust.delete()
        trusted = False
    else:
        trusted = True
    
    # Update post verification status based on trust count
    trust_count = post.trusts.count()
    if trust_count >= 3:  # Threshold for verification
        post.is_verified = True
        post.save()
    elif trust_count == 0:
        post.is_verified = False
        post.save()
    
    return Response({
        'trusted': trusted,
        'trusts_count': trust_count,
        'is_verified': post.is_verified
    })


# Report Views
class PostReportCreateAPIView(generics.CreateAPIView):
    """API view for reporting posts"""
    serializer_class = PostReportSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        post_id = self.kwargs.get('post_id')
        post = get_object_or_404(Post, id=post_id)
        
        # Check if user already reported this post
        if PostReport.objects.filter(post=post, user=self.request.user).exists():
            return Response(
                {'error': 'You have already reported this post'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer.save(user=self.request.user, post=post)
        
        # Increment report count
        post.report_count += 1
        post.save()


# Verification Views
class PostVerificationCreateAPIView(generics.CreateAPIView):
    """API view for post verification by journalists/politicians"""
    serializer_class = PostVerificationSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        post_id = self.kwargs.get('post_id')
        post = get_object_or_404(Post, id=post_id, status='approved')
        
        # Check if user can verify posts
        if self.request.user.role not in ['journalist', 'politician']:
            return Response(
                {'error': 'Only journalists and politicians can verify posts'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Determine verification type based on user role
        verify_type = f"{self.request.user.role}_confirm"
        
        # Check if user already verified this post
        if PostVerification.objects.filter(
            post=post, user=self.request.user, type=verify_type
        ).exists():
            return Response(
                {'error': 'You have already verified this post'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer.save(
            user=self.request.user,
            post=post,
            type=verify_type
        )


# Person Views
class PersonListCreateAPIView(generics.ListCreateAPIView):
    """API view for listing and creating persons"""
    queryset = Person.objects.filter(status='approved')
    serializer_class = PersonSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def perform_create(self, serializer):
        serializer.save(added_by=self.request.user)


class PersonDetailAPIView(generics.RetrieveAPIView):
    """API view for person details"""
    queryset = Person.objects.filter(status='approved')
    serializer_class = PersonSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


# Event Views
class EventListCreateAPIView(generics.ListCreateAPIView):
    """API view for listing and creating events"""
    queryset = Event.objects.filter(status='approved')
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class EventDetailAPIView(generics.RetrieveAPIView):
    """API view for event details"""
    queryset = Event.objects.filter(status='approved')
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


# Verification Request Views
class VerificationRequestCreateAPIView(generics.CreateAPIView):
    """API view for creating verification requests"""
    serializer_class = VerificationRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        # Check if user already has a pending request
        if VerificationRequest.objects.filter(
            user=self.request.user,
            status__in=['pending', 'under_review']
        ).exists():
            return Response(
                {'error': 'You already have a pending verification request'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer.save(user=self.request.user)


class MyVerificationRequestsAPIView(generics.ListAPIView):
    """API view for user's verification requests"""
    serializer_class = VerificationRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return VerificationRequest.objects.filter(
            user=self.request.user
        ).order_by('-created_at')
