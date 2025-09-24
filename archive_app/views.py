from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetView, PasswordResetConfirmView
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from functools import wraps
from .logging_utils import (
    log_user_login, log_user_logout, log_user_registration, 
    log_password_reset, log_post_creation, log_post_verification,
    log_admin_action, log_security_event, file_logger
)
from .models import (
    User, Profile, Person, Event, Post, Comment, PostVerification, 
    PostReport, Like, VerificationRequest, AuditLog, PostTrust, IPBan
)
from .forms import (
    CustomUserCreationForm, CustomAuthenticationForm, ProfileForm, UserEditForm,
    PostForm, CommentForm, PersonForm, EventForm, PostReportForm, 
    PostVerificationForm, VerificationRequestForm, PostSearchForm,
    PeopleSearchForm, EventSearchForm, UserSearchForm, AdminUserStatusForm,
    AdminPostStatusForm, AdminPersonStatusForm, AdminEventStatusForm,
    ReportHandlingForm, VerificationHandlingForm
)

# Helper functions for role-based access control
def is_admin(user):
    """Check if user is an admin"""
    return user.is_authenticated and (user.is_superuser or (hasattr(user, 'role') and user.role == 'admin'))

def is_journalist(user):
    """Check if user is a journalist"""
    return user.is_authenticated and hasattr(user, 'role') and user.role == 'journalist'

def is_politician(user):
    """Check if user is a politician"""
    return user.is_authenticated and hasattr(user, 'role') and user.role == 'politician'

def is_journalist_or_politician(user):
    """Check if user is journalist or politician"""
    return user.is_authenticated and hasattr(user, 'role') and user.role in ['journalist', 'politician']

def can_verify_posts(user):
    """Check if user can verify posts (journalists and politicians)"""
    return user.is_authenticated and hasattr(user, 'role') and user.role in ['journalist', 'politician']

def is_identity_verified(user):
    """Check if user's identity is verified"""
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.is_identity_verified

# Custom decorators
def admin_required(view_func):
    """Decorator to require admin role"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not is_admin(request.user):
            messages.error(request, 'You need admin privileges to access this page.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def journalist_required(view_func):
    """Decorator to require journalist role"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not is_journalist(request.user):
            messages.error(request, 'You need journalist privileges to access this page.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def politician_required(view_func):
    """Decorator to require politician role"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not is_politician(request.user):
            messages.error(request, 'You need politician privileges to access this page.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def verified_user_required(view_func):
    """Decorator to require verified identity"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not is_identity_verified(request.user):
            messages.error(request, 'You need to verify your identity to access this feature.')
            return redirect('profile_edit')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def journalist_or_politician_required(view_func):
    """Decorator to require journalist or politician role"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not is_journalist_or_politician(request.user):
            messages.error(request, 'You need journalist or politician privileges to access this page.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# ==================== HOME & DASHBOARD ====================

def home(request):
    """Home page showing approved posts"""
    posts = Post.objects.filter(status='approved').select_related('user', 'event').prefetch_related('likes', 'comments').order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        posts = posts.filter(
            Q(title__icontains=search_query) | 
            Q(content__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)
    
    context = {
        'posts': posts,
        'search_query': search_query,
    }
    return render(request, 'home.html', context)

@login_required
def dashboard(request):
    """User dashboard"""
    user_posts = Post.objects.filter(user=request.user).order_by('-created_at')[:5]
    user_comments = Comment.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    context = {
        'user_posts': user_posts,
        'user_comments': user_comments,
    }
    return render(request, 'dashboard.html', context)

# ==================== AUTHENTICATION ====================

class CustomLoginView(LoginView):
    """Custom login view with Bootstrap styling"""
    form_class = CustomAuthenticationForm
    template_name = 'registration/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('dashboard')
    
    def form_valid(self, form):
        user = form.get_user()
        ip_address = self.get_client_ip()
        
        # Log successful login with structured format
        file_logger.log_authentication(
            'USER_LOGIN_SUCCESS', 
            user, 
            ip_address, 
            extra_info={'login_method': 'web_form', 'user_agent': self.request.META.get('HTTP_USER_AGENT', 'Unknown')}
        )
        
        messages.success(self.request, f'Welcome back, {user.get_full_name() or user.username}!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        ip_address = self.get_client_ip()
        username = form.data.get('username', 'Unknown')
        
        # Log failed login attempt as security event
        file_logger.log_security(
            ip_address=ip_address,
            message=f'Failed login attempt for username: {username}',
            extra_data={
                'attempted_username': username,
                'user_agent': self.request.META.get('HTTP_USER_AGENT', 'Unknown'),
                'event_type': 'failed_login',
                'timestamp': timezone.now().isoformat()
            }
        )
        
        # Detect suspicious activity patterns
        from .signals import detect_suspicious_activity
        detect_suspicious_activity(ip_address, 'failed_login')
        
        return super().form_invalid(form)
    
    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

class CustomLogoutView(LogoutView):
    """Custom logout view"""
    next_page = 'home'
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            # Log logout before the user is logged out
            ip_address = self.get_client_ip(request)
            user = request.user
            file_logger.log_authentication(
                'USER_LOGOUT',
                user,
                ip_address,
                extra_info={'session_duration': 'calculated', 'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown')}
            )
        
        messages.success(request, 'You have been successfully logged out.')
        return super().dispatch(request, *args, **kwargs)
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class CustomPasswordResetView(PasswordResetView):
    """Custom password reset view with logging"""
    template_name = 'registration/password_reset.html'
    email_template_name = 'registration/password_reset_email.html'
    success_url = '/password_reset/done/'
    
    def form_valid(self, form):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.urls import reverse
        
        email = form.cleaned_data['email']
        ip_address = self.get_client_ip()
        
        # Try to find user by email
        User = get_user_model()
        try:
            user = User.objects.get(email=email)
            
            # Generate reset token and uidb64 (same as Django does internally)
            token = default_token_generator.make_token(user)
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Construct the reset link
            protocol = 'https' if self.request.is_secure() else 'http'
            domain = self.request.get_host()
            reset_path = reverse('password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})
            reset_link = f"{protocol}://{domain}{reset_path}"
            
            # Log password reset request with the actual link
            file_logger.log_password_reset_link(
                user=user,
                ip_address=ip_address,
                reset_link=reset_link,
                user_agent=self.request.META.get('HTTP_USER_AGENT', 'Unknown')
            )
            
            # Also log to authentication log
            file_logger.log_authentication(
                event_type='PASSWORD_RESET_REQUESTED',
                user=user,
                ip_address=ip_address,
                extra_info={'email': email, 'user_agent': self.request.META.get('HTTP_USER_AGENT', 'Unknown'), 'message': f'Password reset requested for email: {email}'}
            )
            
        except User.DoesNotExist:
            # Log failed password reset attempt as security event
            file_logger.log_security(
                ip_address=ip_address,
                message=f'Password reset attempted for non-existent email: {email}',
                extra_data={'attempted_email': email, 'user_agent': self.request.META.get('HTTP_USER_AGENT', 'Unknown'), 'event_type': 'PASSWORD_RESET_INVALID_EMAIL'}
            )
        
        return super().form_valid(form)
    
    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """Custom password reset confirm view with logging"""
    template_name = 'registration/password_reset_confirm.html'
    success_url = '/reset/done/'
    
    def form_valid(self, form):
        user = form.user
        ip_address = self.get_client_ip()
        
        # Log successful password reset completion
        file_logger.log_authentication(
            'PASSWORD_RESET_COMPLETED', 
            user, 
            ip_address, 
            f'Password successfully reset for user: {user.username}',
            extra_info={
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'user_agent': self.request.META.get('HTTP_USER_AGENT', 'Unknown')
            }
        )
        
        return super().form_valid(form)
    
    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def register(request):
    """User registration"""
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create profile for the user
            Profile.objects.get_or_create(user=user)
            
            # Log user registration
            ip_address = get_client_ip(request)
            log_user_registration(user, ip_address)
            
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            
            # Log the user in automatically
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            log_user_login(user, ip_address, success=True)
            
            messages.info(request, 'Please upload your UID document to complete your registration and unlock additional features.')
            return redirect('upload_uid_document')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})

@login_required
def upload_uid_document(request):
    """Upload UID document after registration - completely optional"""
    if request.user.uid_document:
        messages.info(request, 'You have already uploaded your UID document.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        uid_document = request.FILES.get('uid_document')
        intended_role = request.POST.get('intended_role', '').strip()  # Clean whitespace
        
        # Handle all combinations: document + role, document only, role only, or neither
        has_document = bool(uid_document)
        has_role = bool(intended_role)
        
        if has_document or has_role:
            # Update user data only if there's something to save
            if has_document:
                request.user.uid_document = uid_document
            if has_role:
                request.user.intended_role = intended_role
            elif has_document:
                # Clear role if document uploaded but no role selected
                request.user.intended_role = ''
            
            request.user.save()
            
            # Log the action
            if has_document and has_role:
                log_message = f"User {request.user.username} uploaded UID document with intended role: {intended_role}"
                success_message = f'Document uploaded and role ({intended_role}) saved successfully! An admin will review for verification.'
            elif has_document:
                log_message = f"User {request.user.username} uploaded UID document for identity verification only"
                success_message = 'Document uploaded successfully! Your identity will be verified by an admin.'
            else:  # has_role only
                log_message = f"User {request.user.username} saved role preference: {intended_role}"
                success_message = f'Role preference ({intended_role}) saved successfully! You can upload your document anytime.'
            
            file_logger.log_user_action(
                user=request.user,
                ip_address=get_client_ip(request),
                message=log_message,
                extra_data={
                    'user_id': request.user.id,
                    'username': request.user.username,
                    'intended_role': intended_role or 'none',
                    'has_uid_document': has_document,
                    'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown')
                }
            )
            
            messages.success(request, success_message)
        else:
            # Neither document nor role provided - completely valid
            messages.info(request, 'Form submitted successfully! You can upload a document or select a role anytime from your profile.')
        
        return redirect('dashboard')
    
    return render(request, 'registration/upload_uid.html')

@login_required
def change_password(request):
    """Change user password"""
    from django.contrib.auth.forms import PasswordChangeForm
    
    def get_client_ip():
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Update session to prevent logout
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, user)
            
            # Log password change
            ip_address = get_client_ip()
            file_logger.log_authentication(
            event_type='PASSWORD_CHANGED',
            user=user,
            ip_address=ip_address,
            extra_info={'message': 'User changed their password successfully'}
        )
            
            messages.success(request, 'Your password has been successfully updated!')
            return redirect('profile_edit')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'registration/change_password.html', {'form': form})

# ==================== POSTS ====================

@login_required
def post_list(request):
    """List all approved posts for normal users, or user's own posts for content creators"""
    # Show all approved posts for normal users to browse
    # Show user's own posts if they want to manage their content
    if request.GET.get('my_posts') == 'true':
        posts = Post.objects.filter(user=request.user).order_by('-created_at')
    else:
        posts = Post.objects.filter(status='approved').order_by('-created_at')
    
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)
    return render(request, 'posts/post_list.html', {'posts': posts})

@login_required
def post_create(request):
    """Create a new post"""
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.save()
            
            # Log user action
            file_logger.log_user_action(
                user=request.user,
                ip_address=get_client_ip(request),
                message=f"User {request.user.username} created new post {post.id}",
                extra_data={
                    'post_id': post.id,
                    'post_title': post.title or f'Post {post.id}',
                    'post_status': post.status,
                    'has_attachment': bool(post.attachment),
                    'content_length': len(post.content) if post.content else 0,
                    'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown')
                }
            )
            
            messages.success(request, 'Post created successfully!')
            return redirect('post_list')
    else:
        form = PostForm()
    return render(request, 'posts/post_create.html', {'form': form, 'title': 'Create Post'})

@login_required
def post_detail(request, pk):
    """Post detail view with comments"""
    post = get_object_or_404(Post, pk=pk)
    comments = post.comments.all().order_by('-created_at')
    
    # Check if user has liked the post
    user_liked = False
    user_trusted = False
    if request.user.is_authenticated:
        user_liked = Like.objects.filter(post=post, user=request.user).exists()
        user_trusted = PostTrust.objects.filter(post=post, user=request.user).exists()
    
    # Comment form
    if request.method == 'POST' and request.user.is_authenticated:
        comment_form = CommentForm(request.POST, request.FILES)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.post = post
            comment.user = request.user
            comment.save()
            messages.success(request, 'Comment added successfully!')
            return redirect('post_detail', pk=pk)
    else:
        comment_form = CommentForm()
    
    context = {
        'post': post,
        'comments': comments,
        'comment_form': comment_form,
        'user_liked': user_liked,
        'user_trusted': user_trusted,
    }
    return render(request, 'posts/post_detail.html', context)

@login_required
def post_edit(request, pk):
    """Edit post (only by owner)"""
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    post = get_object_or_404(Post, pk=pk, user=request.user)
    if request.method == 'POST':
        # Store original values for comparison
        original_title = post.title
        original_content = post.content
        original_attachment = post.attachment
        
        # Handle remove_attachment checkbox
        if request.POST.get('remove_attachment'):
            post.attachment.delete(save=False)
            post.attachment = None
        
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            updated_post = form.save()
            
            # Log user action
            changes = []
            if original_title != updated_post.title:
                changes.append('title')
            if original_content != updated_post.content:
                changes.append('content')
            if original_attachment != updated_post.attachment:
                changes.append('attachment')
            
            file_logger.log_user_action(
                user=request.user,
                ip_address=get_client_ip(request),
                message=f"User {request.user.username} edited post {post.id}",
                extra_data={
                    'post_id': post.id,
                    'post_title': updated_post.title or f'Post {post.id}',
                    'changes_made': changes,
                    'has_attachment': bool(updated_post.attachment),
                    'content_length': len(updated_post.content) if updated_post.content else 0,
                    'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown')
                }
            )
            
            messages.success(request, 'Post updated successfully!')
            return redirect('post_detail', pk=pk)
    else:
        form = PostForm(instance=post)
    return render(request, 'posts/post_edit.html', {'form': form, 'title': 'Edit Post', 'post': post})

@login_required
def post_delete(request, pk):
    """Delete post (only by owner or admin)"""
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    post = get_object_or_404(Post, pk=pk)
    
    # Check if user is the owner or an admin
    if not (post.user == request.user or is_admin(request.user)):
        messages.error(request, 'You do not have permission to delete this post.')
        return redirect('post_detail', pk=pk)
    
    if request.method == 'POST':
        post_title = post.title or f"Post {post.id}"
        post_owner = post.user.username
        
        # Log admin deletion
        if is_admin(request.user) and post.user != request.user:
            file_logger.log_admin_action(
                action_type=f"Post Deletion",
                admin_user=request.user,
                ip_address=get_client_ip(request),
                details=f'Admin {request.user.username} deleted post "{post_title}" by {post_owner}',
                extra_data={
                    'post_id': post.id,
                    'post_title': post_title,
                    'post_author': post_owner,
                    'action': 'delete',
                    'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown')
                }
            )
        
        post.delete()
        messages.success(request, 'Post deleted successfully!')
        
        # Redirect to appropriate page based on user role
        if is_admin(request.user) and 'admin' in request.META.get('HTTP_REFERER', ''):
            return redirect('admin_posts')
        return redirect('post_list')
    
    return render(request, 'posts/post_confirm_delete.html', {'post': post})

# ==================== LIKES ====================

@login_required
@require_POST
def toggle_like(request, pk):
    """Toggle like on a post"""
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    post = get_object_or_404(Post, pk=pk)
    like, created = Like.objects.get_or_create(post=post, user=request.user)
    
    if not created:
        like.delete()
        liked = False
        action = 'unliked'
    else:
        liked = True
        action = 'liked'
    
    # Log user action
    file_logger.log_user_action(
        user=request.user,
        ip_address=get_client_ip(request),
        message=f"User {request.user.username} {action} post {post.id}",
        extra_data={
            'post_id': post.id,
            'post_title': post.title or f'Post {post.id}',
            'action': action,
            'like_count': post.likes.count(),
            'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown')
        }
    )
    
    return JsonResponse({
        'liked': liked,
        'like_count': post.likes.count()
    })

# ==================== TRUST/VERIFICATION ====================

@login_required
@require_POST
def toggle_trust(request, pk):
    """Toggle trust/verification on a post - only for politicians, journalists, and admins"""
    # Check if user has permission to trust posts
    if not (is_admin(request.user) or is_journalist(request.user) or is_politician(request.user)):
        return JsonResponse({'error': 'You do not have permission to verify posts'}, status=403)
    
    post = get_object_or_404(Post, pk=pk)
    trust, created = PostTrust.objects.get_or_create(post=post, user=request.user)
    
    if not created:
        trust.delete()
        trusted = False
    else:
        trusted = True
    
    # Update post verification status based on trust count
    trust_count = post.trusts.count()
    post.is_verified = trust_count > 0
    post.save()
    
    return JsonResponse({
        'trusted': trusted,
        'trust_count': trust_count,
        'is_verified': post.is_verified
    })

# ==================== REPORTS ====================

@login_required
def report_post(request, pk):
    """Report a post"""
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    post = get_object_or_404(Post, pk=pk)
    
    # Check if user already reported this post
    if PostReport.objects.filter(post=post, user=request.user).exists():
        messages.warning(request, 'You have already reported this post.')
        return redirect('post_detail', pk=pk)
    
    if request.method == 'POST':
        form = PostReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.post = post
            report.user = request.user
            report.save()
            
            # Increment report count
            post.report_count += 1
            post.save()
            
            # Log user action
            file_logger.log_user_action(
                user=request.user,
                ip_address=get_client_ip(request),
                message=f"User {request.user.username} reported post {post.id}",
                extra_data={
                    'post_id': post.id,
                    'post_title': post.title or f'Post {post.id}',
                    'report_reason': report.reason,
                    'post_report_count': post.report_count,
                    'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown')
                }
            )
            
            # Detect suspicious reporting patterns
            from .signals import detect_suspicious_activity
            detect_suspicious_activity(get_client_ip(request), 'post_report')
            
            messages.success(request, 'Post reported successfully!')
            return redirect('post_detail', pk=pk)
    else:
        form = PostReportForm()
    
    return render(request, 'posts/report_form.html', {'form': form, 'post': post})

# ==================== VERIFICATION ====================

@login_required
@journalist_or_politician_required
def verify_post(request, pk):
    """Verify a post (journalists and politicians only)"""
    post = get_object_or_404(Post, pk=pk)
    
    # Check if user has already verified this post
    existing_verification = PostVerification.objects.filter(
        post=post, verified_by=request.user
    ).first()
    
    if existing_verification:
        messages.warning(request, 'You have already verified this post.')
        return redirect('post_detail', pk=pk)
    
    if request.method == 'POST':
        form = PostVerificationForm(request.POST)
        if form.is_valid():
            verification = form.save(commit=False)
            verification.post = post
            verification.verified_by = request.user
            verification.save()
            
            # Log the verification action
            AuditLog.objects.create(
                user=request.user,
                action='verify_post',
                target_model='Post',
                target_id=post.id,
                details=f'Verified post "{post.title}" with type: {verification.verification_type}'
            )
            
            messages.success(request, 'Post has been verified successfully.')
            return redirect('post_detail', pk=pk)
    else:
        form = PostVerificationForm()
    
    context = {
        'form': form,
        'post': post,
    }
    return render(request, 'posts/verify_post.html', context)

# ==================== PEOPLE ====================

@login_required
def person_list(request):
    """List all approved people"""
    people = Person.objects.filter(status='approved').order_by('-created_at')
    
    # Filter by role
    role_filter = request.GET.get('role')
    if role_filter:
        people = people.filter(role=role_filter)
    
    paginator = Paginator(people, 12)
    page_number = request.GET.get('page')
    people = paginator.get_page(page_number)
    
    roles = Person.ROLE_CHOICES
    return render(request, 'people/person_list.html', {'people': people, 'roles': roles, 'current_role': role_filter})

@login_required
def person_create(request):
    """Create a new person entry"""
    if request.method == 'POST':
        form = PersonForm(request.POST, request.FILES)
        if form.is_valid():
            person = form.save(commit=False)
            person.added_by = request.user
            person.save()
            messages.success(request, 'Person entry submitted for approval!')
            return redirect('person_list')
    else:
        form = PersonForm()
    return render(request, 'people/person_form.html', {'form': form, 'title': 'Add Person'})

@login_required
def person_detail(request, pk):
    """Person detail view"""
    person = get_object_or_404(Person, pk=pk)
    return render(request, 'people/person_detail.html', {'person': person})

@login_required
def person_edit(request, pk):
    """Edit person (only by owner or if no owner exists)"""
    person = get_object_or_404(Person, pk=pk)
    # Allow editing if user is the owner or if no owner exists
    if person.added_by and person.added_by != request.user:
        messages.error(request, 'You can only edit people you added.')
        return redirect('person_detail', pk=pk)
    
    if request.method == 'POST':
        form = PersonForm(request.POST, request.FILES, instance=person)
        if form.is_valid():
            # If no owner exists, assign current user as owner
            if not person.added_by:
                person.added_by = request.user
            form.save()
            messages.success(request, 'Person updated successfully!')
            return redirect('person_detail', pk=pk)
    else:
        form = PersonForm(instance=person)
    return render(request, 'people/person_form.html', {'form': form, 'title': 'Edit Person', 'person': person})

@login_required
def person_delete(request, pk):
    """Delete person (only by owner or if no owner exists)"""
    person = get_object_or_404(Person, pk=pk)
    # Allow deletion if user is the owner or if no owner exists
    if person.added_by and person.added_by != request.user:
        messages.error(request, 'You can only delete people you added.')
        return redirect('person_detail', pk=pk)
    
    if request.method == 'POST':
        person.delete()
        messages.success(request, 'Person deleted successfully!')
        return redirect('person_list')
    return render(request, 'people/person_confirm_delete.html', {'person': person})

# ==================== EVENTS ====================

@login_required
def event_list(request):
    """List all approved events"""
    events = Event.objects.filter(status='approved').order_by('-date')
    paginator = Paginator(events, 10)
    page_number = request.GET.get('page')
    events = paginator.get_page(page_number)
    return render(request, 'events/event_list.html', {'events': events})

@login_required
def event_create(request):
    """Create a new event"""
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.created_by = request.user
            event.save()
            form.save_m2m()  # Save many-to-many relationships
            messages.success(request, 'Event submitted for approval!')
            return redirect('event_list')
    else:
        form = EventForm()
    return render(request, 'events/event_form.html', {'form': form, 'title': 'Create Event'})

@login_required
def event_detail(request, pk):
    """Event detail view"""
    event = get_object_or_404(Event, pk=pk)
    event_posts = Post.objects.filter(event=event, status='approved').order_by('-created_at')
    return render(request, 'events/event_detail.html', {'event': event, 'event_posts': event_posts})

@login_required
def event_edit(request, pk):
    """Edit event (only by owner or admin)"""
    event = get_object_or_404(Event, pk=pk)
    
    # Allow editing if user is the owner or admin
    if event.created_by != request.user and not is_admin(request.user):
        messages.error(request, 'You can only edit events you created.')
        return redirect('event_detail', pk=pk)
    
    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, 'Event updated successfully!')
            return redirect('event_detail', pk=pk)
    else:
        form = EventForm(instance=event)
    return render(request, 'events/event_form.html', {'form': form, 'title': 'Edit Event', 'event': event})

# ==================== VERIFICATION REQUESTS ====================

@login_required
def request_verification(request):
    """Request role verification"""
    # Check if user has uploaded UID document
    if not request.user.uid_document:
        messages.error(request, 'You must upload your UID document before requesting verification.')
        return redirect('upload_uid_document')
    
    # Check if user already has a pending request
    if VerificationRequest.objects.filter(user=request.user, status='pending').exists():
        messages.warning(request, 'You already have a pending verification request.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = VerificationRequestForm(request.POST, request.FILES)
        if form.is_valid():
            verification_request = form.save(commit=False)
            verification_request.user = request.user
            verification_request.save()
            messages.success(request, 'Verification request submitted successfully!')
            return redirect('dashboard')
    else:
        form = VerificationRequestForm()
    
    return render(request, 'verification/request_form.html', {'form': form})

# ==================== PROFILE ====================

@login_required
def profile_view(request, username=None):
    """View user profile"""
    if username:
        user = get_object_or_404(User, username=username)
    else:
        user = request.user
    
    user_posts = Post.objects.filter(user=user, status='approved').order_by('-created_at')[:10]
    
    context = {
        'profile_user': user,
        'user_posts': user_posts,
        'is_own_profile': user == request.user,
    }
    return render(request, 'profile/profile.html', context)

@login_required
def profile_edit(request):
    """Edit user profile"""
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    # Ensure user has a profile
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)
    
    if request.method == 'POST':
        # Store original values for comparison
        original_first_name = request.user.first_name
        original_last_name = request.user.last_name
        original_email = request.user.email
        original_bio = profile.bio
        original_intended_role = request.user.intended_role
        
        user_form = UserEditForm(request.POST, request.FILES, instance=request.user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile, user=request.user)
        
        if user_form.is_valid() and profile_form.is_valid():
            updated_user = user_form.save()
            updated_profile = profile_form.save()
            
            # Handle intended_role update for users with UID documents
            if request.user.uid_document and 'intended_role' in request.POST:
                new_intended_role = request.POST.get('intended_role')
                if new_intended_role in ['journalist', 'politician']:
                    updated_user.intended_role = new_intended_role
                    updated_user.save()
            
            # Log user action
            changes = []
            if original_first_name != updated_user.first_name:
                changes.append('first_name')
            if original_last_name != updated_user.last_name:
                changes.append('last_name')
            if original_email != updated_user.email:
                changes.append('email')
            if original_bio != updated_profile.bio:
                changes.append('bio')
            if original_intended_role != updated_user.intended_role:
                changes.append('intended_role')
            
            file_logger.log_user_action(
                user=request.user,
                ip_address=get_client_ip(request),
                message=f"User {request.user.username} updated profile",
                extra_data={
                    'user_id': request.user.id,
                    'username': request.user.username,
                    'changes_made': changes,
                    'intended_role': updated_user.intended_role if 'intended_role' in changes else None,
                    'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown')
                }
            )
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile_view')
    else:
        user_form = UserEditForm(instance=request.user)
        profile_form = ProfileForm(instance=profile, user=request.user)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }
    return render(request, 'profile/profile_edit.html', context)

# ==================== ADMIN DASHBOARD ====================

@admin_required
def admin_dashboard(request):
    """Admin dashboard with statistics"""
    from django.utils import timezone
    from datetime import timedelta
    
    # Calculate date ranges
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    stats = {
        'total_users': User.objects.count(),
        'total_posts': Post.objects.count(),
        'total_reports': PostReport.objects.count(),
        'total_verifications': VerificationRequest.objects.count(),
        'total_people': Person.objects.count(),
        'total_events': Event.objects.count(),
        'pending_posts': Post.objects.filter(status='pending_review').count(),
        'pending_reports': PostReport.objects.filter(status='pending').count(),
        'unhandled_reports': PostReport.objects.filter(status='pending').count(),
        'pending_verifications': VerificationRequest.objects.filter(status='pending').count(),
        'pending_people': Person.objects.filter(status='pending').count(),
        'pending_events': Event.objects.filter(status='pending').count(),
        'new_users_today': User.objects.filter(date_joined__date=today).count(),
        'journalists_count': User.objects.filter(role='journalist').count(),
        'politicians_count': User.objects.filter(role='politician').count(),
        'active_users_24h': User.objects.filter(last_login__gte=yesterday).count(),
        'active_ip_bans': IPBan.objects.filter(is_active=True).count(),
        'users_with_uid': User.objects.exclude(uid_document='').exclude(uid_document__isnull=True).count(),
    }
    
    recent_activities = AuditLog.objects.select_related('admin', 'target_user').order_by('-created_at')[:10]
    
    context = {
        'stats': stats,
        'recent_activities': recent_activities,
        'current_time': timezone.now(),
    }
    return render(request, 'admin/admin_dashboard.html', context)

@admin_required
def admin_users(request):
    """Admin user management"""
    users = User.objects.all().order_by('-date_joined')
    
    # Filter by role
    role_filter = request.GET.get('role')
    if role_filter:
        users = users.filter(role=role_filter)
    
    # Filter by UID document status
    has_uid = request.GET.get('has_uid')
    if has_uid == 'true':
        users = users.exclude(uid_document='').exclude(uid_document__isnull=True)
    elif has_uid == 'false':
        users = users.filter(Q(uid_document='') | Q(uid_document__isnull=True))
    
    # Search
    search_query = request.GET.get('search')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)
    
    context = {
        'users': users,
        'role_filter': role_filter,
        'search_query': search_query,
        'user_roles': User.ROLE_CHOICES,
    }
    return render(request, 'admin/admin_users.html', context)

@admin_required
def admin_user_detail(request, pk):
    """Admin user detail and management"""
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    user = get_object_or_404(User, pk=pk)
    user_posts = Post.objects.filter(user=user).order_by('-created_at')[:10]
    user_reports = PostReport.objects.filter(user=user).order_by('-created_at')[:10]
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'change_role':
            new_role = request.POST.get('role')
            if new_role in dict(User.ROLE_CHOICES):
                old_role = user.role
                user.role = new_role
                user.save()
                
                # Log the action
                file_logger.log_admin_action(
                    action_type=f"User Role Change",
                    admin_user=request.user,
                    target_user=user,
                    ip_address=get_client_ip(request),
                    details=f"Admin {request.user.username} changed user {user.username} role from {old_role} to {new_role}"
                )
                
                messages.success(request, f'User role changed from {old_role} to {new_role}')
        
        elif action == 'confirm_identity':
            user.identity_confirmed = True
            user.save()
            
            # Log the action
            file_logger.log_admin_action(
                action_type=f"Identity Confirmation",
                admin_user=request.user,
                target_user=user,
                ip_address=get_client_ip(request),
                details=f"Admin {request.user.username} confirmed identity for user {user.username}"
            )
            
            messages.success(request, 'User identity confirmed')
        
        elif action == 'revoke_identity':
            user.identity_confirmed = False
            user.save()
            
            # Log the action
            file_logger.log_admin_action(
                action_type=f"Identity Revocation",
                admin_user=request.user,
                target_user=user,
                ip_address=get_client_ip(request),
                details=f"Admin {request.user.username} revoked identity verification for user {user.username}"
            )
            
            messages.success(request, 'User identity verification revoked')
        
        elif action == 'toggle_active':
            old_status = user.is_active
            user.is_active = not user.is_active
            user.save()
            status = 'activated' if user.is_active else 'deactivated'
            
            # Log the action
            file_logger.log_admin_action(
                action_type=f"User Status Change",
                admin_user=request.user,
                target_user=user,
                ip_address=get_client_ip(request),
                details=f"Admin {request.user.username} {status} user {user.username}"
            )
            
            messages.success(request, f'User {status} successfully')
        
        elif action == 'ban_user':
            ban_reason = request.POST.get('ban_reason', '')
            user.is_banned = True
            user.ban_reason = ban_reason
            user.banned_at = timezone.now()
            user.banned_by = request.user
            user.is_active = False  # Also deactivate when banned
            user.save()
            
            # Log the action
            file_logger.log_admin_action(
                action_type=f"User Ban",
                admin_user=request.user,
                target_user=user,
                ip_address=get_client_ip(request),
                details=f"Admin {request.user.username} banned user {user.username}. Reason: {ban_reason}"
            )
            
            messages.success(request, f'User banned successfully. Reason: {ban_reason}')
        
        elif action == 'unban_user':
            user.is_banned = False
            user.ban_reason = None
            user.banned_at = None
            user.banned_by = None
            user.is_active = True  # Reactivate when unbanned
            user.save()
            
            # Log the action
            file_logger.log_admin_action(
                action_type=f"User Unban",
                admin_user=request.user,
                target_user=user,
                ip_address=get_client_ip(request),
                details=f"Admin {request.user.username} unbanned user {user.username}"
            )
            
            messages.success(request, 'User unbanned successfully')
        
        elif action == 'delete_user':
            # Prevent deleting admin users
            if user.role == 'admin':
                messages.error(request, 'Cannot delete admin users')
            else:
                # Log the action before deletion
                file_logger.log_admin_action(
                    action_type=f"User Deletion",
                    admin_user=request.user,
                    target_user=user,
                    ip_address=get_client_ip(request),
                    details=f"Admin {request.user.username} deleted user {username}"
                )
                
                username = user.username
                user.delete()
                messages.success(request, f'User {username} deleted successfully')
                return redirect('admin_users')
        
        return redirect('admin_user_detail', pk=pk)
    
    context = {
        'user_obj': user,
        'user_posts': user_posts,
        'user_reports': user_reports,
        'user_roles': User.ROLE_CHOICES,
    }
    return render(request, 'admin/user_detail.html', context)

@admin_required
def admin_posts(request):
    """Admin post management"""
    posts = Post.objects.select_related('user', 'event').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        posts = posts.filter(status=status_filter)
    
    paginator = Paginator(posts, 20)
    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)
    
    context = {
        'posts': posts,
        'status_filter': status_filter,
        'post_statuses': Post.STATUS_CHOICES,
    }
    return render(request, 'admin/posts.html', context)

@admin_required
def admin_post_detail(request, pk):
    """Admin post detail and management"""
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    post = get_object_or_404(Post, pk=pk)
    post_reports = PostReport.objects.filter(post=post).select_related('user').order_by('-created_at')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'change_status':
            new_status = request.POST.get('status')
            if new_status in dict(Post.STATUS_CHOICES):
                old_status = post.status
                post.status = new_status
                post.save()
                
                # Log the action
                file_logger.log_admin_action(
                    action_type=f"Post Status Change",
                    admin_user=request.user,
                    target_user=post.user,
                    ip_address=get_client_ip(request),
                    details=f"Admin {request.user.username} changed post {post.id} status from {old_status} to {new_status}"
                )
                
                messages.success(request, f'Post status changed from {old_status} to {new_status}')
        
        return redirect('admin_post_detail', pk=pk)
    
    context = {
        'post': post,
        'post_reports': post_reports,
        'post_statuses': Post.STATUS_CHOICES,
    }
    return render(request, 'admin/post_detail.html', context)

@admin_required
def admin_post_status_update(request, pk):
    """Update post status from admin panel"""
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    post = get_object_or_404(Post, pk=pk)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        admin_notes = request.POST.get('admin_notes', '')
        
        if new_status in dict(Post.STATUS_CHOICES):
            old_status = post.status
            post.status = new_status
            post.save()
            
            # Log the action with description
            description = f'Changed post status from {old_status} to {new_status}'
            if admin_notes:
                description += f'. Notes: {admin_notes}'
            
            file_logger.log_admin_action(
                action_type=f"Post Status Update",
                admin_user=request.user,
                ip_address=get_client_ip(request),
                details={
                    'post_id': post.id,
                    'post_title': post.title or f'Post {post.id}',
                    'post_author': post.user.username,
                    'old_status': old_status,
                    'new_status': new_status,
                    'admin_notes': admin_notes,
                    'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown')
                }
            )
            
            messages.success(request, f'Post status changed from {old_status} to {new_status}')
        else:
            messages.error(request, 'Invalid status selected')
    
    return redirect('admin_post_detail', pk=pk)

@admin_required
def admin_reports(request):
    """Admin report management"""
    reports = PostReport.objects.select_related('user', 'post', 'handled_by_admin').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        reports = reports.filter(status=status_filter)
    
    paginator = Paginator(reports, 20)
    page_number = request.GET.get('page')
    reports = paginator.get_page(page_number)
    
    context = {
        'reports': reports,
        'status_filter': status_filter,
        'report_statuses': PostReport.STATUS_CHOICES,
    }
    return render(request, 'admin/reports.html', context)

@admin_required
def admin_reports(request):
    """Admin reports management page"""
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    
    # Base queryset
    reports = PostReport.objects.select_related('post', 'user', 'handled_by_admin').order_by('-created_at')
    
    # Apply filters
    if status_filter:
        reports = reports.filter(status=status_filter)
    
    if search_query:
        reports = reports.filter(
            Q(post__title__icontains=search_query) |
            Q(post__content__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(reports, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    stats = {
        'total_reports': PostReport.objects.count(),
        'pending_reports': PostReport.objects.filter(status='pending').count(),
        'resolved_reports': PostReport.objects.filter(status='resolved').count(),
        'dismissed_reports': PostReport.objects.filter(status='dismissed').count(),
    }
    
    context = {
        'reports': page_obj,
        'stats': stats,
        'status_filter': status_filter,
        'search_query': search_query,
        'report_statuses': PostReport.STATUS_CHOICES,
    }
    return render(request, 'admin/reports.html', context)

@admin_required
def admin_report_detail(request, pk):
    """Admin report detail and handling"""
    report = get_object_or_404(PostReport, pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'handle_report':
            new_status = request.POST.get('status')
            if new_status in dict(PostReport.STATUS_CHOICES):
                report.status = new_status
                report.handled_by_admin = request.user
                report.save()
                
                # Log the action
                AuditLog.objects.create(
                    admin=request.user,
                    action_type='report_handled',
                    report=report
                )
                
                messages.success(request, f'Report marked as {new_status}')
        
        return redirect('admin_report_detail', pk=pk)
    
    context = {
        'report': report,
        'report_statuses': PostReport.STATUS_CHOICES,
    }
    return render(request, 'admin/report_detail.html', context)

@admin_required
def admin_verifications(request):
    """Admin verification requests management page"""
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    role_filter = request.GET.get('role', '')
    search_query = request.GET.get('search', '')
    
    # Base queryset
    verifications = VerificationRequest.objects.select_related('user', 'handled_by_admin').order_by('-created_at')
    
    # Apply filters
    if status_filter:
        verifications = verifications.filter(status=status_filter)
    
    if role_filter:
        verifications = verifications.filter(requested_role=role_filter)
    
    if search_query:
        verifications = verifications.filter(
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(verifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    stats = {
        'total_verifications': VerificationRequest.objects.count(),
        'pending_verifications': VerificationRequest.objects.filter(status='pending').count(),
        'approved_verifications': VerificationRequest.objects.filter(status='approved').count(),
        'rejected_verifications': VerificationRequest.objects.filter(status='rejected').count(),
        'journalist_requests': VerificationRequest.objects.filter(requested_role='journalist').count(),
        'politician_requests': VerificationRequest.objects.filter(requested_role='politician').count(),
    }
    
    context = {
        'verifications': page_obj,
        'stats': stats,
        'status_filter': status_filter,
        'role_filter': role_filter,
        'search_query': search_query,
        'verification_statuses': VerificationRequest._meta.get_field('status').choices,
        'role_choices': VerificationRequest.ROLE_CHOICES,
    }
    return render(request, 'admin/verifications.html', context)

@admin_required
def admin_verification_detail(request, pk):
    """Admin verification request detail and handling"""
    verification = get_object_or_404(VerificationRequest, pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'handle_verification':
            new_status = request.POST.get('status')
            if new_status in ['approved', 'rejected', 'under_review']:
                verification.status = new_status
                verification.handled_by_admin = request.user
                verification.save()
                
                # If approved, update user role
                if new_status == 'approved':
                    user = verification.user
                    user.role = verification.requested_role
                    user.identity_confirmed = True
                    user.save()
                    
                    messages.success(request, f'Verification approved. User role updated to {verification.requested_role}.')
                elif new_status == 'rejected':
                    messages.success(request, 'Verification request rejected.')
                else:
                    messages.success(request, 'Verification request marked as under review.')
                
                # Log the action
                AuditLog.objects.create(
                    admin=request.user,
                    action_type='verification_handled',
                    verification_request=verification
                )
        
        return redirect('admin_verification_detail', pk=pk)
    
    context = {
        'verification': verification,
    }
    return render(request, 'admin/verification_detail.html', context)

@admin_required
def admin_people(request):
    """Admin people management"""
    people = Person.objects.select_related('added_by').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        people = people.filter(status=status_filter)
    
    # Filter by role
    role_filter = request.GET.get('role')
    if role_filter:
        people = people.filter(role=role_filter)
    
    # Search
    search_query = request.GET.get('search')
    if search_query:
        people = people.filter(
            Q(name__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    paginator = Paginator(people, 20)
    page_number = request.GET.get('page')
    people = paginator.get_page(page_number)
    
    context = {
        'people': people,
        'status_filter': status_filter,
        'role_filter': role_filter,
        'search_query': search_query,
    }
    return render(request, 'admin/people.html', context)

@admin_required
def admin_person_detail(request, pk):
    """Admin person detail and management"""
    person = get_object_or_404(Person, pk=pk)
    related_posts = Post.objects.filter(people__id=pk).select_related('user')[:10]
    
    context = {
        'person': person,
        'related_posts': related_posts,
    }
    return render(request, 'admin/person_detail.html', context)

@admin_required
def admin_person_update_role(request, pk):
    """Update person role"""
    person = get_object_or_404(Person, pk=pk)
    
    if request.method == 'POST':
        new_role = request.POST.get('role')
        role_choices = ['victim', 'witness', 'perpetrator', 'journalist', 'activist', 'official', 'other']
        
        if new_role in role_choices:
            old_role = person.role
            person.role = new_role
            person.save()
            
            # Log the action
            AuditLog.objects.create(
                admin=request.user,
                action_type='person_role_change',
                description=f'Changed person role for "{person.name}" from {old_role} to {new_role}'
            )
            
            messages.success(request, f'Person role changed from {old_role} to {new_role}')
        else:
            messages.error(request, 'Invalid role selected')
    
    return redirect('admin_person_detail', pk=pk)

@admin_required
def admin_person_update_status(request, pk):
    """Update person status"""
    person = get_object_or_404(Person, pk=pk)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        status_choices = ['pending', 'approved', 'rejected']
        
        if new_status in status_choices:
            old_status = person.status
            person.status = new_status
            person.save()
            
            # Log the action
            AuditLog.objects.create(
                admin=request.user,
                action_type='person_status_change',
                description=f'Changed person status for "{person.name}" from {old_status} to {new_status}'
            )
            
            messages.success(request, f'Person status changed from {old_status} to {new_status}')
        else:
            messages.error(request, 'Invalid status selected')
    
    return redirect('admin_person_detail', pk=pk)

@admin_required
def admin_person_delete(request, pk):
    """Delete person"""
    person = get_object_or_404(Person, pk=pk)
    
    if request.method == 'POST':
        person_name = person.name
        person.delete()
        
        # Log the action
        AuditLog.objects.create(
            admin=request.user,
            action_type='person_deleted',
            description=f'Deleted person: {person_name}'
        )
        
        messages.success(request, f'Person "{person_name}" deleted successfully')
        return redirect('admin_people')
    
    return redirect('admin_person_detail', pk=pk)

@admin_required
def admin_events(request):
    """Admin events management"""
    events = Event.objects.select_related('created_by').order_by('-date')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        events = events.filter(status=status_filter)
    
    paginator = Paginator(events, 20)
    page_number = request.GET.get('page')
    events = paginator.get_page(page_number)
    
    context = {
        'events': events,
        'status_filter': status_filter,
    }
    return render(request, 'admin/events.html', context)

@admin_required
def admin_event_detail(request, pk):
    """Admin event detail and management"""
    event = get_object_or_404(Event, pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'change_status':
            new_status = request.POST.get('status')
            if new_status in ['pending', 'approved', 'rejected']:
                old_status = event.status
                event.status = new_status
                event.save()
                
                # Create audit log
                AuditLog.objects.create(
                    admin=request.user,
                    action_type='event_status_change',
                    description=f'Changed event "{event.title}" status from {old_status} to {new_status}'
                )
                
                messages.success(request, f'Event status changed to {new_status}')
        
        return redirect('admin_event_detail', pk=pk)
    
    context = {
        'event': event,
    }
    return render(request, 'admin/event_detail.html', context)

# --------------------
# IP Ban Management Views
# --------------------

@admin_required
def admin_ip_bans(request):
    """Admin IP bans list and management"""
    # Handle new IP ban creation
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_ip_ban':
            ip_address = request.POST.get('ip_address')
            reason = request.POST.get('reason', '')
            
            if ip_address:
                try:
                    # Check if IP is already banned
                    existing_ban = IPBan.objects.filter(ip_address=ip_address, is_active=True).first()
                    if existing_ban:
                        messages.warning(request, f'IP {ip_address} is already banned.')
                    else:
                        IPBan.objects.create(
                            ip_address=ip_address,
                            reason=reason,
                            banned_by=request.user
                        )
                        messages.success(request, f'IP {ip_address} has been banned successfully.')
                except Exception as e:
                    messages.error(request, f'Error banning IP: {str(e)}')
            else:
                messages.error(request, 'Please provide a valid IP address.')
        
        elif action == 'remove_ip_ban':
            ban_id = request.POST.get('ban_id')
            try:
                ban = IPBan.objects.get(id=ban_id)
                ban.is_active = False
                ban.save()
                messages.success(request, f'IP ban for {ban.ip_address} has been removed.')
            except IPBan.DoesNotExist:
                messages.error(request, 'IP ban not found.')
        
        return redirect('admin_ip_bans')
    
    # Get search and filter parameters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', 'all')
    
    # Filter IP bans
    ip_bans = IPBan.objects.all()
    
    if search_query:
        ip_bans = ip_bans.filter(
            Q(ip_address__icontains=search_query) |
            Q(reason__icontains=search_query)
        )
    
    if status_filter == 'active':
        ip_bans = ip_bans.filter(is_active=True)
    elif status_filter == 'inactive':
        ip_bans = ip_bans.filter(is_active=False)
    
    ip_bans = ip_bans.order_by('-banned_at')
    
    # Pagination
    paginator = Paginator(ip_bans, 20)  # Show 20 IP bans per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'ip_bans': ip_bans,
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    return render(request, 'admin/ip_bans.html', context)

@admin_required
def admin_ip_ban_detail(request, pk):
    """Admin IP ban detail view"""
    ip_ban = get_object_or_404(IPBan, pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'toggle_status':
            ip_ban.is_active = not ip_ban.is_active
            ip_ban.save()
            status = 'activated' if ip_ban.is_active else 'deactivated'
            messages.success(request, f'IP ban has been {status}.')
        
        elif action == 'update_reason':
            new_reason = request.POST.get('reason', '')
            ip_ban.reason = new_reason
            ip_ban.save()
            messages.success(request, 'IP ban reason updated successfully.')
        
        return redirect('admin_ip_ban_detail', pk=pk)
    
    context = {
        'ip_ban': ip_ban,
    }
    return render(request, 'admin/ip_ban_detail.html', context)

@admin_required
def admin_logs(request):
    """Admin view to display system logs"""
    log_type = request.GET.get('type', 'authentication')
    search_term = request.GET.get('search', '')
    lines_count = int(request.GET.get('lines', 50))
    
    # Available log types with detailed descriptions
    log_types = [
        ('authentication', 'User Authentication (Login, Logout, Password Reset)'),
        ('user_actions', 'User Actions (Profile Updates, General Activities)'),
        ('admin_actions', 'Admin Actions (User Management, System Changes)'),
        ('post_actions', 'Post Actions (Creation, Verification, Moderation)'),
        ('security', 'Security Events (Failed Logins, Suspicious Activities)'),
        ('system', 'Server Logs (System Events, Errors, Performance)')
    ]
    
    logs = []
    if search_term:
        # Search in logs
        logs = file_logger.search_logs(log_type, search_term, max_results=100)
    else:
        # Get recent logs
        recent_logs = file_logger.get_recent_logs(log_type, lines=lines_count)
        logs = [{
            'line_number': idx + 1,
            'content': line.strip(),
            'timestamp': line.split(']')[0][1:] if ']' in line else 'Unknown'
        } for idx, line in enumerate(recent_logs)]
    
    context = {
        'logs': logs,
        'log_types': log_types,
        'current_log_type': log_type,
        'search_term': search_term,
        'lines_count': lines_count,
        'total_logs': len(logs)
    }
    
    return render(request, 'admin/logs.html', context)

@admin_required
def admin_logs_download(request):
    """Download log file"""
    from django.http import HttpResponse
    import os
    
    log_type = request.GET.get('type', 'authentication')
    log_filename = file_logger.get_log_filename(log_type)
    
    if not os.path.exists(log_filename):
        messages.error(request, f'Log file for {log_type} does not exist.')
        return redirect('admin_logs')
    
    try:
        with open(log_filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="{log_type}_{timezone.now().strftime("%Y-%m-%d")}.log"'
        return response
    except Exception as e:
        messages.error(request, f'Error downloading log file: {str(e)}')
        return redirect('admin_logs')