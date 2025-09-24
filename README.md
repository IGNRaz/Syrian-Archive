# Syrian Archive

A comprehensive digital archive platform for documenting and preserving Syrian conflict-related content, built with Django and Django REST Framework.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Installation](#installation)
- [API Documentation](#api-documentation)
- [User Roles](#user-roles)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## 🌟 Overview

Syrian Archive is a digital platform designed to collect, verify, and preserve documentation related to the Syrian conflict. The platform enables users to submit posts, manage events, document people involved, and maintain a comprehensive archive of conflict-related information.

## ✨ Features

### Core Functionality
- **User Authentication & Authorization**: Multi-role user system with role-based permissions
- **Content Management**: Create, edit, and manage posts with media attachments
- **Event Documentation**: Track and document significant events with participant information
- **People Registry**: Maintain records of individuals involved in events
- **Verification System**: Multi-level content verification and approval workflow
- **Reporting System**: Community-driven content reporting and moderation

### Advanced Features
- **Social Authentication**: Login via Google, Microsoft, GitHub, and LinkedIn
- **JWT Token Authentication**: Secure API access with token-based authentication
- **Admin Dashboard**: Comprehensive administrative interface
- **Content Moderation**: Automated and manual content review processes
- **User Management**: Role upgrades, banning, and identity verification
- **API Integration**: Full REST API for external integrations

## 🛠 Technology Stack

### Backend
- **Django 5.2.5**: Web framework
- **Django REST Framework**: API development
- **MySQL**: Primary database
- **Django Allauth**: Authentication and social login
- **JWT**: Token-based authentication

### Frontend
- **HTML5/CSS3**: Template rendering
- **Bootstrap**: UI framework
- **JavaScript**: Interactive functionality

### Third-Party Integrations
- **Social OAuth Providers**: Google, Microsoft, GitHub, LinkedIn
- **File Storage**: Django file handling for media uploads

## 🚀 Installation

### Prerequisites
- Python 3.8+
- MySQL 5.7+
- pip (Python package manager)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/Syrian-Archive.git
   cd Syrian-Archive
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install django djangorestframework django-allauth djangorestframework-simplejwt mysqlclient pillow
   ```

4. **Database Configuration**
   - Create a MySQL database named `syrianarchive_db`
   - Update database credentials in `settings.py`

5. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start development server**
   ```bash
   python manage.py runserver
   ```

The application will be available at `http://127.0.0.1:8000/`

## 📚 API Documentation

### Authentication Endpoints
- `POST /api/token/` - Obtain JWT token
- `POST /api/token/refresh/` - Refresh JWT token
- `POST /api/login/` - API login

### User Management
- `GET /api/users/` - List all users
- `GET /api/users/{id}/` - Get user details
- `GET /api/profile/` - Get current user profile
- `PUT /api/profile/` - Update current user profile

### Posts
- `GET /api/posts/` - List all posts
- `POST /api/posts/` - Create new post
- `GET /api/posts/{id}/` - Get post details
- `PUT /api/posts/{id}/` - Update post
- `DELETE /api/posts/{id}/` - Delete post
- `GET /api/posts/my/` - Get current user's posts

### Post Interactions
- `POST /api/posts/{id}/like/` - Like/unlike post
- `POST /api/posts/{id}/trust/` - Trust/untrust post
- `POST /api/posts/{id}/report/` - Report post
- `POST /api/posts/{id}/verify/` - Verify post (admin only)

### Comments
- `GET /api/posts/{post_id}/comments/` - Get post comments
- `POST /api/posts/{post_id}/comments/` - Create comment
- `GET /api/comments/{id}/` - Get comment details
- `PUT /api/comments/{id}/` - Update comment
- `DELETE /api/comments/{id}/` - Delete comment

### People
- `GET /api/people/` - List all people
- `POST /api/people/` - Create person record
- `GET /api/people/{id}/` - Get person details
- `PUT /api/people/{id}/` - Update person
- `DELETE /api/people/{id}/` - Delete person

### Events
- `GET /api/events/` - List all events
- `POST /api/events/` - Create event
- `GET /api/events/{id}/` - Get event details
- `PUT /api/events/{id}/` - Update event
- `DELETE /api/events/{id}/` - Delete event

### Verification Requests
- `POST /api/verification-requests/` - Create verification request
- `GET /api/verification-requests/my/` - Get user's verification requests

## 👥 User Roles

### Normal User
- Create and manage posts
- Comment on posts
- Report inappropriate content
- Request role upgrades

### Journalist
- All normal user permissions
- Enhanced content creation privileges
- Access to journalist-specific features

### Politician
- All normal user permissions
- Auto-approved content
- Political content privileges

### Admin
- Full system access
- User management
- Content moderation
- System configuration

## 📁 Project Structure

```
syrian_archive/
├── archive_app/           # Main application
│   ├── models.py         # Data models
│   ├── views.py          # View logic
│   ├── urls.py           # URL routing
│   ├── admin.py          # Admin interface
│   └── middleware.py     # Custom middleware
├── api/                  # REST API application
│   ├── views.py          # API views
│   ├── urls.py           # API routing
│   └── serializers.py    # Data serializers
├── auth_payments/        # Authentication & payments
├── templates/            # HTML templates
├── static/              # Static files (CSS, JS, images)
├── media/               # User uploaded files
└── syrian_archive/      # Project configuration
    ├── settings.py      # Django settings
    ├── urls.py          # Main URL configuration
    └── wsgi.py          # WSGI configuration
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔒 Security

- Never commit sensitive information like API keys or database credentials
- Use environment variables for configuration in production
- Regularly update dependencies to patch security vulnerabilities
- Follow Django security best practices

## 📞 Support

For support and questions, please open an issue in the GitHub repository or contact the development team.

---

**Note**: This is a development version. For production deployment, additional configuration for security, performance, and scalability is required.