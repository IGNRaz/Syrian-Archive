# Syrian Archive API Endpoints for Flutter Integration

This document provides a comprehensive list of API endpoints for Flutter integration with the Syrian Archive application.

## Base Configuration
```dart
class ApiConfig {
  static const String baseUrl = 'http://127.0.0.1:8000';
  static const String apiVersion = '/api/';
  static const String authPaymentsBase = '/auth_payments/api/';
  
  static String get apiBaseUrl => '$baseUrl$apiVersion';
  static String get authPaymentsBaseUrl => '$baseUrl$authPaymentsBase';
}
```

## Authentication Setup

### JWT Token Management
```dart
class TokenManager {
  static const String _accessTokenKey = 'access_token';
  static const String _refreshTokenKey = 'refresh_token';
  
  static Future<void> saveTokens(String accessToken, String refreshToken) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_accessTokenKey, accessToken);
    await prefs.setString(_refreshTokenKey, refreshToken);
  }
  
  static Future<String?> getAccessToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_accessTokenKey);
  }
  
  static Future<String?> getRefreshToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_refreshTokenKey);
  }
  
  static Future<void> clearTokens() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_accessTokenKey);
    await prefs.remove(_refreshTokenKey);
  }
}
```

## Authentication Endpoints

### JWT Authentication
```dart
// Login and get JWT tokens
POST $apiBaseUrl/auth/login/

// Get JWT token pair
POST $apiBaseUrl/token/

// Refresh JWT token
POST $apiBaseUrl/token/refresh/
```

## User Management Endpoints

```dart
// List all active users
GET $apiBaseUrl/users/

// Get specific user details
GET $apiBaseUrl/users/{id}/

// Get current user profile
GET $apiBaseUrl/profile/

// Update current user profile (full update)
PUT $apiBaseUrl/profile/

// Partially update current user profile
PATCH $apiBaseUrl/profile/
```

## Post Management Endpoints

```dart
// List all approved posts (supports ?search= and ?user= params)
GET $apiBaseUrl/posts/

// Create new post
POST $apiBaseUrl/posts/

// Get specific post details
GET $apiBaseUrl/posts/{id}/

// Update specific post
PUT $apiBaseUrl/posts/{id}/

// Delete specific post
DELETE $apiBaseUrl/posts/{id}/

// Get current user's posts
GET $apiBaseUrl/posts/my/
```

## Post Interaction Endpoints

```dart
// Toggle like on post
POST $apiBaseUrl/posts/{post_id}/like/

// Toggle trust on post
POST $apiBaseUrl/posts/{post_id}/trust/

// Report a post
POST $apiBaseUrl/posts/{post_id}/report/

// Verify a post
POST $apiBaseUrl/posts/{post_id}/verify/
```

## Comment Endpoints

```dart
// List comments for a post
GET $apiBaseUrl/posts/{post_id}/comments/

// Create comment on post
POST $apiBaseUrl/posts/{post_id}/comments/

// Get specific comment
GET $apiBaseUrl/comments/{id}/

// Update specific comment
PUT $apiBaseUrl/comments/{id}/

// Delete specific comment
DELETE $apiBaseUrl/comments/{id}/
```

## Person Management Endpoints

```dart
// List all approved persons
GET $apiBaseUrl/persons/

// Create new person
POST $apiBaseUrl/persons/

// Get specific person details
GET $apiBaseUrl/persons/{id}/
```

## Event Management Endpoints

```dart
// List all approved events
GET $apiBaseUrl/events/

// Create new event
POST $apiBaseUrl/events/

// Get specific event details
GET $apiBaseUrl/events/{id}/
```

## Verification Request Endpoints

```dart
// Create verification request
POST $apiBaseUrl/verification-requests/

// Get current user's verification requests
GET $apiBaseUrl/verification-requests/my/
```

## Payment System Endpoints

### Payment Methods
```dart
// Get user's payment methods
GET $authBaseUrl/api/payment-methods/

// Add new payment method
POST $authBaseUrl/api/payment-methods/

// Delete payment method
DELETE $authBaseUrl/api/payment-methods/{id}/

// Set default payment method
POST $authBaseUrl/api/payment-methods/{id}/set-default/
```

### Payment Processing
```dart
// Process a payment
POST $authBaseUrl/api/process-payment/

// Refund a payment
POST $authBaseUrl/api/payments/{id}/refund/

// Get payment statistics
GET $authBaseUrl/api/payment-statistics/
```

### Payment History
```dart
// Get payment transaction history (supports pagination)
GET $authBaseUrl/api/payment-history/
```

### Subscriptions
```dart
// Get user subscriptions
GET $authBaseUrl/api/subscriptions/

// Create new subscription
POST $authBaseUrl/api/subscriptions/

// Cancel subscription
DELETE $authBaseUrl/api/subscriptions/{id}/
```

### Social Authentication
```dart
// Get user's social account information
GET $authBaseUrl/api/social-accounts/
```

## Webhook Endpoints (for backend integration)

```dart
// Stripe webhook endpoint
POST $authBaseUrl/webhooks/stripe/

// PayPal webhook endpoint
POST $authBaseUrl/webhooks/paypal/
```

## HTTP Client Setup

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';

class ApiClient {
  static Future<Map<String, String>> _getHeaders({bool requiresAuth = true}) async {
    Map<String, String> headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    
    if (requiresAuth) {
      final token = await TokenManager.getAccessToken();
      if (token != null) {
        headers['Authorization'] = 'Bearer $token';
      }
    }
    
    return headers;
  }
  
  static Future<http.Response> _makeRequest(Future<http.Response> Function() request) async {
    try {
      final response = await request();
      
      // Handle token refresh if needed
      if (response.statusCode == 401) {
        final refreshed = await _refreshToken();
        if (refreshed) {
          // Retry the request with new token
          return await request();
        } else {
          // Redirect to login
          await TokenManager.clearTokens();
          throw Exception('Authentication failed. Please login again.');
        }
      }
      
      return response;
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }
  
  static Future<bool> _refreshToken() async {
    try {
      final refreshToken = await TokenManager.getRefreshToken();
      if (refreshToken == null) return false;
      
      final response = await http.post(
        Uri.parse('${ApiConfig.apiBaseUrl}token/refresh/'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'refresh': refreshToken}),
      );
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        await TokenManager.saveTokens(data['access'], refreshToken);
        return true;
      }
      
      return false;
    } catch (e) {
      return false;
    }
  }
  
  static Future<Map<String, dynamic>> get(String endpoint, {bool requiresAuth = true}) async {
    final headers = await _getHeaders(requiresAuth: requiresAuth);
    
    final response = await _makeRequest(() => http.get(
      Uri.parse('${ApiConfig.apiBaseUrl}$endpoint'),
      headers: headers,
    ));
    
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to load data: ${response.statusCode} - ${response.body}');
    }
  }
  
  static Future<Map<String, dynamic>> post(String endpoint, Map<String, dynamic> data, {bool requiresAuth = true}) async {
    final headers = await _getHeaders(requiresAuth: requiresAuth);
    
    final response = await _makeRequest(() => http.post(
      Uri.parse('${ApiConfig.apiBaseUrl}$endpoint'),
      headers: headers,
      body: json.encode(data),
    ));
    
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to post data: ${response.statusCode} - ${response.body}');
    }
  }
  
  static Future<Map<String, dynamic>> put(String endpoint, Map<String, dynamic> data, {bool requiresAuth = true}) async {
    final headers = await _getHeaders(requiresAuth: requiresAuth);
    
    final response = await _makeRequest(() => http.put(
      Uri.parse('${ApiConfig.apiBaseUrl}$endpoint'),
      headers: headers,
      body: json.encode(data),
    ));
    
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to update data: ${response.statusCode} - ${response.body}');
    }
  }
  
  static Future<bool> delete(String endpoint, {bool requiresAuth = true}) async {
    final headers = await _getHeaders(requiresAuth: requiresAuth);
    
    final response = await _makeRequest(() => http.delete(
      Uri.parse('${ApiConfig.apiBaseUrl}$endpoint'),
      headers: headers,
    ));
    
    return response.statusCode >= 200 && response.statusCode < 300;
  }
}

## Flutter HTTP Client Usage Examples

### Authentication Service
```dart
class AuthService {
  // Login with username/password
  static Future<Map<String, dynamic>> login(String username, String password) async {
    try {
      final response = await ApiClient.post('login/', {
        'username': username,
        'password': password,
      }, requiresAuth: false);
      
      // Save tokens
      if (response['access'] != null && response['refresh'] != null) {
        await TokenManager.saveTokens(response['access'], response['refresh']);
      }
      
      return response;
    } catch (e) {
      throw Exception('Login failed: $e');
    }
  }
  
  // Register new user
  static Future<Map<String, dynamic>> register({
    required String username,
    required String email,
    required String password,
    required String firstName,
    required String lastName,
  }) async {
    try {
      return await ApiClient.post('register/', {
        'username': username,
        'email': email,
        'password': password,
        'first_name': firstName,
        'last_name': lastName,
      }, requiresAuth: false);
    } catch (e) {
      throw Exception('Registration failed: $e');
    }
  }
  
  // Get user profile
  static Future<Map<String, dynamic>> getProfile() async {
    return await ApiClient.get('profile/');
  }
  
  // Update user profile
  static Future<Map<String, dynamic>> updateProfile(Map<String, dynamic> data) async {
    return await ApiClient.put('profile/', data);
  }
  
  // Logout
  static Future<void> logout() async {
    await TokenManager.clearTokens();
  }
}
```

### Post Service
```dart
class PostService {
  // Get all posts with pagination
  static Future<Map<String, dynamic>> getPosts({int page = 1, int pageSize = 20}) async {
    return await ApiClient.get('posts/?page=$page&page_size=$pageSize');
  }
  
  // Get single post
  static Future<Map<String, dynamic>> getPost(int postId) async {
    return await ApiClient.get('posts/$postId/');
  }
  
  // Create new post
  static Future<Map<String, dynamic>> createPost({
    required String title,
    required String content,
    String? location,
    List<int>? peopleIds,
    List<int>? eventIds,
  }) async {
    Map<String, dynamic> data = {
      'title': title,
      'content': content,
    };
    
    if (location != null) data['location'] = location;
    if (peopleIds != null) data['people'] = peopleIds;
    if (eventIds != null) data['events'] = eventIds;
    
    return await ApiClient.post('posts/', data);
  }
  
  // Update post
  static Future<Map<String, dynamic>> updatePost(int postId, Map<String, dynamic> data) async {
    return await ApiClient.put('posts/$postId/', data);
  }
  
  // Delete post
  static Future<bool> deletePost(int postId) async {
    return await ApiClient.delete('posts/$postId/');
  }
  
  // Like/Unlike post
  static Future<Map<String, dynamic>> likePost(int postId) async {
    return await ApiClient.post('posts/$postId/like/', {});
  }
  
  static Future<bool> unlikePost(int postId) async {
    return await ApiClient.delete('posts/$postId/unlike/');
  }
  
  // Trust post
  static Future<Map<String, dynamic>> trustPost(int postId) async {
    return await ApiClient.post('posts/$postId/trust/', {});
  }
  
  // Report post
  static Future<Map<String, dynamic>> reportPost(int postId, String reason) async {
    return await ApiClient.post('posts/$postId/report/', {'reason': reason});
  }
  
  // Verify post (admin only)
  static Future<Map<String, dynamic>> verifyPost(int postId, bool isVerified) async {
    return await ApiClient.post('posts/$postId/verify/', {'is_verified': isVerified});
  }
}
```

### Comment Service
```dart
class CommentService {
  // Get comments for a post
  static Future<List<dynamic>> getComments({int? postId}) async {
    String endpoint = 'comments/';
    if (postId != null) endpoint += '?post=$postId';
    
    final response = await ApiClient.get(endpoint);
    return response['results'] ?? [];
  }
  
  // Create comment
  static Future<Map<String, dynamic>> createComment({
    required int postId,
    required String content,
    int? parentId,
  }) async {
    Map<String, dynamic> data = {
      'post': postId,
      'content': content,
    };
    
    if (parentId != null) data['parent'] = parentId;
    
    return await ApiClient.post('comments/', data);
  }
  
  // Update comment
  static Future<Map<String, dynamic>> updateComment(int commentId, String content) async {
    return await ApiClient.put('comments/$commentId/', {'content': content});
  }
  
  // Delete comment
  static Future<bool> deleteComment(int commentId) async {
    return await ApiClient.delete('comments/$commentId/');
  }
}
```

### Person Service
```dart
class PersonService {
  // Get all persons
  static Future<Map<String, dynamic>> getPersons({int page = 1}) async {
    return await ApiClient.get('persons/?page=$page');
  }
  
  // Get single person
  static Future<Map<String, dynamic>> getPerson(int personId) async {
    return await ApiClient.get('persons/$personId/');
  }
  
  // Create new person
  static Future<Map<String, dynamic>> createPerson({
    required String name,
    String? role,
    String? description,
    String? location,
  }) async {
    Map<String, dynamic> data = {'name': name};
    
    if (role != null) data['role'] = role;
    if (description != null) data['description'] = description;
    if (location != null) data['location'] = location;
    
    return await ApiClient.post('persons/', data);
  }
  
  // Update person
  static Future<Map<String, dynamic>> updatePerson(int personId, Map<String, dynamic> data) async {
    return await ApiClient.put('persons/$personId/', data);
  }
  
  // Delete person
  static Future<bool> deletePerson(int personId) async {
    return await ApiClient.delete('persons/$personId/');
  }
}
```

### Event Service
```dart
class EventService {
  // Get all events
  static Future<Map<String, dynamic>> getEvents({int page = 1}) async {
    return await ApiClient.get('events/?page=$page');
  }
  
  // Get single event
  static Future<Map<String, dynamic>> getEvent(int eventId) async {
    return await ApiClient.get('events/$eventId/');
  }
  
  // Create new event
  static Future<Map<String, dynamic>> createEvent({
    required String title,
    required String description,
    required String date,
    String? location,
  }) async {
    return await ApiClient.post('events/', {
      'title': title,
      'description': description,
      'date': date,
      if (location != null) 'location': location,
    });
  }
  
  // Update event
  static Future<Map<String, dynamic>> updateEvent(int eventId, Map<String, dynamic> data) async {
    return await ApiClient.put('events/$eventId/', data);
  }
  
  // Delete event
  static Future<bool> deleteEvent(int eventId) async {
    return await ApiClient.delete('events/$eventId/');
  }
}
```

### Verification Request Service
```dart
class VerificationService {
  // Get verification requests
  static Future<Map<String, dynamic>> getVerificationRequests({int page = 1}) async {
    return await ApiClient.get('verification-requests/?page=$page');
  }
  
  // Get single verification request
  static Future<Map<String, dynamic>> getVerificationRequest(int requestId) async {
    return await ApiClient.get('verification-requests/$requestId/');
  }
  
  // Create verification request
  static Future<Map<String, dynamic>> createVerificationRequest({
    required String requestType,
    required String description,
    Map<String, dynamic>? additionalData,
  }) async {
    Map<String, dynamic> data = {
      'request_type': requestType,
      'description': description,
    };
    
    if (additionalData != null) {
      data.addAll(additionalData);
    }
    
    return await ApiClient.post('verification-requests/', data);
  }
  
  // Update verification request
  static Future<Map<String, dynamic>> updateVerificationRequest(int requestId, Map<String, dynamic> data) async {
    return await ApiClient.put('verification-requests/$requestId/', data);
  }
}
```

## Dependencies

Add these to your `pubspec.yaml`:

```yaml
dependencies:
  http: ^0.13.5
  shared_preferences: ^2.0.15
  # For file uploads (if needed)
  http_parser: ^4.0.2
  mime: ^1.0.4
```

## Usage Example in Flutter Widget

```dart
class PostListWidget extends StatefulWidget {
  @override
  _PostListWidgetState createState() => _PostListWidgetState();
}

class _PostListWidgetState extends State<PostListWidget> {
  List<dynamic> posts = [];
  bool isLoading = true;
  String? error;
  
  @override
  void initState() {
    super.initState();
    loadPosts();
  }
  
  Future<void> loadPosts() async {
    try {
      setState(() {
        isLoading = true;
        error = null;
      });
      
      final response = await PostService.getPosts();
      
      setState(() {
        posts = response['results'] ?? [];
        isLoading = false;
      });
    } catch (e) {
      setState(() {
        error = e.toString();
        isLoading = false;
      });
    }
  }
  
  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return Center(child: CircularProgressIndicator());
    }
    
    if (error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('Error: $error'),
            ElevatedButton(
              onPressed: loadPosts,
              child: Text('Retry'),
            ),
          ],
        ),
      );
    }
    
    return ListView.builder(
      itemCount: posts.length,
      itemBuilder: (context, index) {
        final post = posts[index];
        return ListTile(
          title: Text(post['title'] ?? ''),
          subtitle: Text(post['content'] ?? ''),
          onTap: () {
            // Navigate to post detail
          },
        );
      },
    );
  }
}
```

## Authentication Notes

- **JWT Authentication**: Most endpoints require JWT authentication with automatic token refresh
- **Bearer Token**: Access tokens are automatically included in Authorization headers
- **Token Management**: Use TokenManager class for secure token storage and retrieval
- **Auto-Refresh**: ApiClient automatically refreshes expired tokens using refresh tokens
- **Payment Security**: Payment endpoints have additional rate limiting and security checks

## Response Format

- **JSON Responses**: All endpoints return JSON responses
- **Pagination**: List endpoints support pagination with `page` and `page_size` parameters
- **Error Handling**: Comprehensive error responses with descriptive messages
- **Success Data**: Response format varies by endpoint but includes requested data
- **Status Codes**: Standard HTTP status codes (200, 201, 400, 401, 404, 500)

## Rate Limiting & Security

- **Payment API**: Limited requests per time window with enhanced security
- **General API**: Standard rate limiting applies to all endpoints
- **Headers**: Check response headers for rate limit information
- **Retry Logic**: Implement exponential backoff for rate-limited requests

## CORS Configuration

- **Development**: CORS configured for localhost development
- **Production**: Ensure your Flutter app's domain is in allowed origins
- **Webhooks**: Special CORS handling for payment webhook endpoints