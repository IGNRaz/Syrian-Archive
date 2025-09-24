from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    # Authentication
    path('auth/login/', views.LoginAPIView.as_view(), name='login'),
    
    # User endpoints
    path('users/', views.UserListAPIView.as_view(), name='user-list'),
    path('users/<int:pk>/', views.UserDetailAPIView.as_view(), name='user-detail'),
    path('profile/', views.UserProfileAPIView.as_view(), name='user-profile'),
    
    # Post endpoints
    path('posts/', views.PostListCreateAPIView.as_view(), name='post-list-create'),
    path('posts/<int:pk>/', views.PostDetailAPIView.as_view(), name='post-detail'),
    path('posts/my/', views.MyPostsAPIView.as_view(), name='my-posts'),
    
    # Post interactions
    path('posts/<int:post_id>/like/', views.toggle_like, name='toggle-like'),
    path('posts/<int:post_id>/trust/', views.toggle_trust, name='toggle-trust'),
    path('posts/<int:post_id>/report/', views.PostReportCreateAPIView.as_view(), name='report-post'),
    path('posts/<int:post_id>/verify/', views.PostVerificationCreateAPIView.as_view(), name='verify-post'),
    
    # Comment endpoints
    path('posts/<int:post_id>/comments/', views.CommentListCreateAPIView.as_view(), name='comment-list-create'),
    path('comments/<int:pk>/', views.CommentDetailAPIView.as_view(), name='comment-detail'),
    
    # Person endpoints
    path('persons/', views.PersonListCreateAPIView.as_view(), name='person-list-create'),
    path('persons/<int:pk>/', views.PersonDetailAPIView.as_view(), name='person-detail'),
    
    # Event endpoints
    path('events/', views.EventListCreateAPIView.as_view(), name='event-list-create'),
    path('events/<int:pk>/', views.EventDetailAPIView.as_view(), name='event-detail'),
    
    # Verification requests
    path('verification-requests/', views.VerificationRequestCreateAPIView.as_view(), name='verification-request-create'),
    path('verification-requests/my/', views.MyVerificationRequestsAPIView.as_view(), name='my-verification-requests'),
]