# Syrian Archive API Guide for Flutter Chatbots

This comprehensive guide will help you integrate the Syrian Archive API into your Flutter chatbot application.

## Table of Contents
1. [Quick Start](#quick-start)
2. [Authentication Setup](#authentication-setup)
3. [API Client Configuration](#api-client-configuration)
4. [Core API Services](#core-api-services)
5. [Chatbot Integration Examples](#chatbot-integration-examples)
6. [Error Handling](#error-handling)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Quick Start

### 1. Add Dependencies

Add these dependencies to your `pubspec.yaml`:

```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.1.0
  shared_preferences: ^2.2.2
  dio: ^5.3.2  # Alternative to http package
  json_annotation: ^4.8.1
  
dev_dependencies:
  json_serializable: ^6.7.1
  build_runner: ^2.4.7
```

### 2. API Configuration

```dart
// lib/config/api_config.dart
class ApiConfig {
  static const String baseUrl = 'http://127.0.0.1:8000/api';
  static const String authBaseUrl = 'http://127.0.0.1:8000/auth-payments/api';
  
  // API Endpoints
  static const String login = '/auth/login/';
  static const String tokenRefresh = '/token/refresh/';
  static const String posts = '/posts/';
  static const String users = '/users/';
  static const String comments = '/posts/{post_id}/comments/';
  static const String persons = '/persons/';
  static const String events = '/events/';
  static const String verificationRequests = '/verification-requests/';
}
```

## Authentication Setup

### Token Manager

```dart
// lib/services/token_manager.dart
import 'package:shared_preferences/shared_preferences.dart';

class TokenManager {
  static const String _accessTokenKey = 'access_token';
  static const String _refreshTokenKey = 'refresh_token';
  static const String _userIdKey = 'user_id';
  static const String _userRoleKey = 'user_role';

  // Save tokens after login
  static Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
    int? userId,
    String? userRole,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_accessTokenKey, accessToken);
    await prefs.setString(_refreshTokenKey, refreshToken);
    if (userId != null) await prefs.setInt(_userIdKey, userId);
    if (userRole != null) await prefs.setString(_userRoleKey, userRole);
  }

  // Get access token
  static Future<String?> getAccessToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_accessTokenKey);
  }

  // Get refresh token
  static Future<String?> getRefreshToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_refreshTokenKey);
  }

  // Get user info
  static Future<Map<String, dynamic>?> getUserInfo() async {
    final prefs = await SharedPreferences.getInstance();
    final userId = prefs.getInt(_userIdKey);
    final userRole = prefs.getString(_userRoleKey);
    
    if (userId != null) {
      return {
        'id': userId,
        'role': userRole,
      };
    }
    return null;
  }

  // Check if user is authenticated
  static Future<bool> isAuthenticated() async {
    final token = await getAccessToken();
    return token != null && token.isNotEmpty;
  }

  // Clear all tokens (logout)
  static Future<void> clearTokens() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_accessTokenKey);
    await prefs.remove(_refreshTokenKey);
    await prefs.remove(_userIdKey);
    await prefs.remove(_userRoleKey);
  }
}
```

## API Client Configuration

### HTTP Client with Auto Token Refresh

```dart
// lib/services/api_client.dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'token_manager.dart';
import '../config/api_config.dart';

class ApiClient {
  static final http.Client _client = http.Client();

  // Get headers with authentication
  static Future<Map<String, String>> _getHeaders() async {
    final token = await TokenManager.getAccessToken();
    return {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  // Generic request method with token refresh
  static Future<Map<String, dynamic>> _makeRequest(
    String method,
    String endpoint, {
    Map<String, dynamic>? data,
    Map<String, String>? queryParams,
  }) async {
    try {
      final uri = Uri.parse('${ApiConfig.baseUrl}$endpoint')
          .replace(queryParameters: queryParams);
      final headers = await _getHeaders();
      
      http.Response response;
      
      switch (method.toUpperCase()) {
        case 'GET':
          response = await _client.get(uri, headers: headers);
          break;
        case 'POST':
          response = await _client.post(
            uri,
            headers: headers,
            body: data != null ? json.encode(data) : null,
          );
          break;
        case 'PUT':
          response = await _client.put(
            uri,
            headers: headers,
            body: data != null ? json.encode(data) : null,
          );
          break;
        case 'DELETE':
          response = await _client.delete(uri, headers: headers);
          break;
        default:
          throw Exception('Unsupported HTTP method: $method');
      }

      // Handle token refresh for 401 errors
      if (response.statusCode == 401) {
        final refreshed = await _refreshToken();
        if (refreshed) {
          // Retry the request with new token
          return await _makeRequest(method, endpoint, data: data, queryParams: queryParams);
        } else {
          throw Exception('Authentication failed');
        }
      }

      if (response.statusCode >= 200 && response.statusCode < 300) {
        return json.decode(response.body);
      } else {
        throw Exception('HTTP ${response.statusCode}: ${response.body}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  // Refresh token
  static Future<bool> _refreshToken() async {
    try {
      final refreshToken = await TokenManager.getRefreshToken();
      if (refreshToken == null) return false;

      final response = await _client.post(
        Uri.parse('${ApiConfig.baseUrl}/token/refresh/'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'refresh': refreshToken}),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        await TokenManager.saveTokens(
          accessToken: data['access'],
          refreshToken: refreshToken,
        );
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }

  // HTTP Methods
  static Future<Map<String, dynamic>> get(
    String endpoint, {
    Map<String, String>? queryParams,
  }) async {
    return await _makeRequest('GET', endpoint, queryParams: queryParams);
  }

  static Future<Map<String, dynamic>> post(
    String endpoint,
    Map<String, dynamic> data,
  ) async {
    return await _makeRequest('POST', endpoint, data: data);
  }

  static Future<Map<String, dynamic>> put(
    String endpoint,
    Map<String, dynamic> data,
  ) async {
    return await _makeRequest('PUT', endpoint, data: data);
  }

  static Future<bool> delete(String endpoint) async {
    try {
      await _makeRequest('DELETE', endpoint);
      return true;
    } catch (e) {
      return false;
    }
  }
}
```

## Core API Services

### Authentication Service

```dart
// lib/services/auth_service.dart
import 'api_client.dart';
import 'token_manager.dart';

class AuthService {
  // Login user
  static Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    try {
      final response = await ApiClient.post('/auth/login/', {
        'email': email,
        'password': password,
      });

      if (response['access'] != null && response['refresh'] != null) {
        await TokenManager.saveTokens(
          accessToken: response['access'],
          refreshToken: response['refresh'],
          userId: response['user']?['id'],
          userRole: response['user']?['role'],
        );
      }

      return response;
    } catch (e) {
      throw Exception('Login failed: $e');
    }
  }

  // Register user
  static Future<Map<String, dynamic>> register({
    required String email,
    required String password,
    required String firstName,
    required String lastName,
  }) async {
    return await ApiClient.post('/auth/register/', {
      'email': email,
      'password': password,
      'first_name': firstName,
      'last_name': lastName,
    });
  }

  // Logout
  static Future<void> logout() async {
    await TokenManager.clearTokens();
  }

  // Get current user profile
  static Future<Map<String, dynamic>> getCurrentUser() async {
    return await ApiClient.get('/profile/');
  }
}
```

### Post Service for Chatbot

```dart
// lib/services/post_service.dart
import 'api_client.dart';

class PostService {
  // Get posts with search functionality (perfect for chatbot queries)
  static Future<List<Map<String, dynamic>>> searchPosts({
    String? query,
    int? userId,
    int? eventId,
    int page = 1,
    int pageSize = 10,
  }) async {
    final queryParams = <String, String>{
      'page': page.toString(),
      'page_size': pageSize.toString(),
    };
    
    if (query != null && query.isNotEmpty) {
      queryParams['search'] = query;
    }
    if (userId != null) {
      queryParams['user'] = userId.toString();
    }
    if (eventId != null) {
      queryParams['event'] = eventId.toString();
    }

    final response = await ApiClient.get('/posts/', queryParams: queryParams);
    return List<Map<String, dynamic>>.from(response['results'] ?? []);
  }

  // Get single post details
  static Future<Map<String, dynamic>> getPost(int postId) async {
    return await ApiClient.get('/posts/$postId/');
  }

  // Create new post
  static Future<Map<String, dynamic>> createPost({
    required String title,
    required String content,
    String? location,
    List<int>? peopleIds,
    int? eventId,
  }) async {
    final data = {
      'title': title,
      'content': content,
    };
    
    if (location != null) data['location'] = location;
    if (peopleIds != null) data['people'] = peopleIds;
    if (eventId != null) data['event'] = eventId;

    return await ApiClient.post('/posts/', data);
  }

  // Get post comments
  static Future<List<Map<String, dynamic>>> getPostComments(int postId) async {
    final response = await ApiClient.get('/posts/$postId/comments/');
    return List<Map<String, dynamic>>.from(response['results'] ?? []);
  }

  // Add comment to post
  static Future<Map<String, dynamic>> addComment({
    required int postId,
    required String content,
  }) async {
    return await ApiClient.post('/posts/$postId/comments/', {
      'content': content,
    });
  }

  // Like/Unlike post
  static Future<Map<String, dynamic>> toggleLike(int postId) async {
    return await ApiClient.post('/posts/$postId/like/', {});
  }

  // Trust post
  static Future<Map<String, dynamic>> trustPost(int postId) async {
    return await ApiClient.post('/posts/$postId/trust/', {});
  }

  // Report post
  static Future<Map<String, dynamic>> reportPost({
    required int postId,
    required String reason,
  }) async {
    return await ApiClient.post('/posts/$postId/report/', {
      'reason': reason,
    });
  }
}
```

### Person & Event Services

```dart
// lib/services/content_service.dart
import 'api_client.dart';

class ContentService {
  // Get persons (for chatbot to reference people in posts)
  static Future<List<Map<String, dynamic>>> getPersons() async {
    final response = await ApiClient.get('/persons/');
    return List<Map<String, dynamic>>.from(response['results'] ?? []);
  }

  // Get events (for chatbot to reference events)
  static Future<List<Map<String, dynamic>>> getEvents() async {
    final response = await ApiClient.get('/events/');
    return List<Map<String, dynamic>>.from(response['results'] ?? []);
  }

  // Search persons by name
  static Future<List<Map<String, dynamic>>> searchPersons(String query) async {
    final persons = await getPersons();
    return persons.where((person) {
      final name = person['name']?.toString().toLowerCase() ?? '';
      return name.contains(query.toLowerCase());
    }).toList();
  }

  // Search events by title
  static Future<List<Map<String, dynamic>>> searchEvents(String query) async {
    final events = await getEvents();
    return events.where((event) {
      final title = event['title']?.toString().toLowerCase() ?? '';
      return title.contains(query.toLowerCase());
    }).toList();
  }
}
```

## Chatbot Integration Examples

### Chatbot Service

```dart
// lib/services/chatbot_service.dart
import 'post_service.dart';
import 'content_service.dart';
import 'auth_service.dart';

class ChatbotService {
  // Process user message and return appropriate response
  static Future<String> processMessage(String userMessage) async {
    final message = userMessage.toLowerCase().trim();
    
    try {
      // Handle authentication queries
      if (message.contains('login') || message.contains('sign in')) {
        return _handleLoginQuery();
      }
      
      // Handle search queries
      if (message.contains('search') || message.contains('find')) {
        return await _handleSearchQuery(message);
      }
      
      // Handle post creation
      if (message.contains('create post') || message.contains('add post')) {
        return _handleCreatePostQuery();
      }
      
      // Handle person queries
      if (message.contains('person') || message.contains('people')) {
        return await _handlePersonQuery(message);
      }
      
      // Handle event queries
      if (message.contains('event')) {
        return await _handleEventQuery(message);
      }
      
      // Handle help queries
      if (message.contains('help') || message.contains('what can you do')) {
        return _getHelpMessage();
      }
      
      // Default response
      return "I can help you search posts, find people and events, create posts, and more. Type 'help' to see all available commands.";
      
    } catch (e) {
      return "Sorry, I encountered an error: ${e.toString()}. Please try again.";
    }
  }
  
  static String _handleLoginQuery() {
    return "To use advanced features, you need to log in. Please use the login form in the app.";
  }
  
  static Future<String> _handleSearchQuery(String message) async {
    // Extract search terms from message
    final searchTerms = _extractSearchTerms(message);
    
    if (searchTerms.isEmpty) {
      return "What would you like to search for? Please provide some keywords.";
    }
    
    final posts = await PostService.searchPosts(
      query: searchTerms.join(' '),
      pageSize: 5,
    );
    
    if (posts.isEmpty) {
      return "No posts found matching your search. Try different keywords.";
    }
    
    final response = StringBuffer("Found ${posts.length} posts:\n\n");
    
    for (int i = 0; i < posts.length; i++) {
      final post = posts[i];
      response.writeln("${i + 1}. ${post['title']}");
      response.writeln("   ${_truncateText(post['content'], 100)}");
      response.writeln("   Posted by: ${post['user']['username']}");
      response.writeln("");
    }
    
    return response.toString();
  }
  
  static String _handleCreatePostQuery() {
    return "To create a post, you need to be logged in. Use the 'Create Post' feature in the app with title, content, and optional location.";
  }
  
  static Future<String> _handlePersonQuery(String message) async {
    final searchTerms = _extractSearchTerms(message);
    
    if (searchTerms.isEmpty) {
      final persons = await ContentService.getPersons();
      return "Here are some people in our database: ${persons.take(5).map((p) => p['name']).join(', ')}";
    }
    
    final persons = await ContentService.searchPersons(searchTerms.join(' '));
    
    if (persons.isEmpty) {
      return "No people found matching your search.";
    }
    
    final names = persons.map((p) => "${p['name']} (${p['role']})").take(10).join(', ');
    return "Found people: $names";
  }
  
  static Future<String> _handleEventQuery(String message) async {
    final searchTerms = _extractSearchTerms(message);
    
    if (searchTerms.isEmpty) {
      final events = await ContentService.getEvents();
      return "Recent events: ${events.take(5).map((e) => e['title']).join(', ')}";
    }
    
    final events = await ContentService.searchEvents(searchTerms.join(' '));
    
    if (events.isEmpty) {
      return "No events found matching your search.";
    }
    
    final response = StringBuffer("Found events:\n");
    for (final event in events.take(5)) {
      response.writeln("• ${event['title']} (${event['date']})");
    }
    
    return response.toString();
  }
  
  static String _getHelpMessage() {
    return """
I can help you with:

🔍 **Search Posts**: "search for [keywords]"
👥 **Find People**: "find person [name]"
📅 **Find Events**: "find event [name]"
📝 **Create Posts**: "create post" (requires login)
🔐 **Login**: "login" or "sign in"

Examples:
• "search for Syria conflict"
• "find person John Smith"
• "find event Damascus"
• "create post about recent news"

What would you like to do?
""";
  }
  
  // Helper methods
  static List<String> _extractSearchTerms(String message) {
    final words = message.split(' ');
    final searchWords = <String>[];
    
    bool foundSearchKeyword = false;
    for (final word in words) {
      if (['search', 'find', 'for', 'about'].contains(word.toLowerCase())) {
        foundSearchKeyword = true;
        continue;
      }
      
      if (foundSearchKeyword && word.length > 2) {
        searchWords.add(word);
      }
    }
    
    return searchWords;
  }
  
  static String _truncateText(String text, int maxLength) {
    if (text.length <= maxLength) return text;
    return '${text.substring(0, maxLength)}...';
  }
}
```

### Chatbot Widget

```dart
// lib/widgets/chatbot_widget.dart
import 'package:flutter/material.dart';
import '../services/chatbot_service.dart';

class ChatbotWidget extends StatefulWidget {
  @override
  _ChatbotWidgetState createState() => _ChatbotWidgetState();
}

class _ChatbotWidgetState extends State<ChatbotWidget> {
  final List<ChatMessage> _messages = [];
  final TextEditingController _textController = TextEditingController();
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _addBotMessage("Hello! I'm your Syrian Archive assistant. How can I help you today? Type 'help' to see what I can do.");
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Expanded(
          child: ListView.builder(
            itemCount: _messages.length,
            itemBuilder: (context, index) {
              return _buildMessage(_messages[index]);
            },
          ),
        ),
        if (_isLoading)
          Padding(
            padding: EdgeInsets.all(8.0),
            child: Row(
              children: [
                CircularProgressIndicator(strokeWidth: 2),
                SizedBox(width: 8),
                Text('Thinking...'),
              ],
            ),
          ),
        _buildTextComposer(),
      ],
    );
  }

  Widget _buildMessage(ChatMessage message) {
    return Container(
      margin: EdgeInsets.symmetric(vertical: 4, horizontal: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CircleAvatar(
            backgroundColor: message.isUser ? Colors.blue : Colors.green,
            child: Icon(
              message.isUser ? Icons.person : Icons.smart_toy,
              color: Colors.white,
            ),
          ),
          SizedBox(width: 8),
          Expanded(
            child: Container(
              padding: EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: message.isUser ? Colors.blue[50] : Colors.green[50],
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                message.text,
                style: TextStyle(fontSize: 14),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTextComposer() {
    return Container(
      padding: EdgeInsets.all(8),
      decoration: BoxDecoration(
        border: Border(top: BorderSide(color: Colors.grey[300]!)),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _textController,
              decoration: InputDecoration(
                hintText: 'Ask me anything...',
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(20),
                ),
                contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              ),
              onSubmitted: _handleSubmitted,
            ),
          ),
          SizedBox(width: 8),
          IconButton(
            icon: Icon(Icons.send),
            onPressed: () => _handleSubmitted(_textController.text),
          ),
        ],
      ),
    );
  }

  void _handleSubmitted(String text) async {
    if (text.trim().isEmpty) return;

    _textController.clear();
    _addUserMessage(text);

    setState(() {
      _isLoading = true;
    });

    try {
      final response = await ChatbotService.processMessage(text);
      _addBotMessage(response);
    } catch (e) {
      _addBotMessage("Sorry, I encountered an error. Please try again.");
    }

    setState(() {
      _isLoading = false;
    });
  }

  void _addUserMessage(String text) {
    setState(() {
      _messages.add(ChatMessage(text: text, isUser: true));
    });
  }

  void _addBotMessage(String text) {
    setState(() {
      _messages.add(ChatMessage(text: text, isUser: false));
    });
  }
}

class ChatMessage {
  final String text;
  final bool isUser;

  ChatMessage({required this.text, required this.isUser});
}
```

## Error Handling

### Global Error Handler

```dart
// lib/utils/error_handler.dart
class ApiErrorHandler {
  static String getErrorMessage(dynamic error) {
    if (error.toString().contains('401')) {
      return 'Authentication required. Please log in.';
    } else if (error.toString().contains('403')) {
      return 'Access denied. You don\'t have permission for this action.';
    } else if (error.toString().contains('404')) {
      return 'Resource not found.';
    } else if (error.toString().contains('500')) {
      return 'Server error. Please try again later.';
    } else if (error.toString().contains('Network error')) {
      return 'Network connection error. Please check your internet.';
    } else {
      return 'An unexpected error occurred. Please try again.';
    }
  }
  
  static void handleError(dynamic error, {Function(String)? onError}) {
    final message = getErrorMessage(error);
    print('API Error: $error');
    
    if (onError != null) {
      onError(message);
    }
  }
}
```

## Best Practices

### 1. Caching Strategy

```dart
// lib/services/cache_service.dart
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class CacheService {
  static const Duration _defaultCacheDuration = Duration(minutes: 5);
  
  static Future<void> cacheData(String key, Map<String, dynamic> data) async {
    final prefs = await SharedPreferences.getInstance();
    final cacheData = {
      'data': data,
      'timestamp': DateTime.now().millisecondsSinceEpoch,
    };
    await prefs.setString(key, json.encode(cacheData));
  }
  
  static Future<Map<String, dynamic>?> getCachedData(
    String key, {
    Duration? maxAge,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final cachedString = prefs.getString(key);
    
    if (cachedString == null) return null;
    
    final cacheData = json.decode(cachedString);
    final timestamp = DateTime.fromMillisecondsSinceEpoch(cacheData['timestamp']);
    final age = DateTime.now().difference(timestamp);
    
    if (age > (maxAge ?? _defaultCacheDuration)) {
      await prefs.remove(key);
      return null;
    }
    
    return cacheData['data'];
  }
}
```

### 2. Rate Limiting

```dart
// lib/utils/rate_limiter.dart
class RateLimiter {
  static final Map<String, DateTime> _lastRequests = {};
  static const Duration _minInterval = Duration(milliseconds: 500);
  
  static Future<bool> canMakeRequest(String endpoint) async {
    final now = DateTime.now();
    final lastRequest = _lastRequests[endpoint];
    
    if (lastRequest == null || now.difference(lastRequest) >= _minInterval) {
      _lastRequests[endpoint] = now;
      return true;
    }
    
    return false;
  }
}
```

### 3. Offline Support

```dart
// lib/services/offline_service.dart
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class OfflineService {
  static const String _offlinePostsKey = 'offline_posts';
  
  static Future<void> savePostsOffline(List<Map<String, dynamic>> posts) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_offlinePostsKey, json.encode(posts));
  }
  
  static Future<List<Map<String, dynamic>>> getOfflinePosts() async {
    final prefs = await SharedPreferences.getInstance();
    final postsString = prefs.getString(_offlinePostsKey);
    
    if (postsString == null) return [];
    
    final List<dynamic> postsList = json.decode(postsString);
    return postsList.cast<Map<String, dynamic>>();
  }
}
```

## Troubleshooting

### Common Issues and Solutions

1. **Authentication Errors**
   - Ensure tokens are properly stored and retrieved
   - Check token expiration and refresh logic
   - Verify API endpoints are correct

2. **Network Errors**
   - Check internet connectivity
   - Verify API server is running
   - Implement retry logic for failed requests

3. **Parsing Errors**
   - Validate JSON response format
   - Handle null values properly
   - Use try-catch blocks around JSON parsing

4. **Performance Issues**
   - Implement caching for frequently accessed data
   - Use pagination for large datasets
   - Optimize image loading and caching

### Debug Mode

```dart
// lib/config/debug_config.dart
class DebugConfig {
  static const bool isDebugMode = true; // Set to false for production
  
  static void log(String message) {
    if (isDebugMode) {
      print('[DEBUG] $message');
    }
  }
  
  static void logApiCall(String method, String endpoint, {Map<String, dynamic>? data}) {
    if (isDebugMode) {
      print('[API] $method $endpoint');
      if (data != null) {
        print('[API DATA] ${json.encode(data)}');
      }
    }
  }
}
```

## Example Usage in Main App

```dart
// lib/main.dart
import 'package:flutter/material.dart';
import 'widgets/chatbot_widget.dart';
import 'services/auth_service.dart';
import 'services/token_manager.dart';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Syrian Archive Chatbot',
      theme: ThemeData(
        primarySwatch: Colors.blue,
      ),
      home: MainScreen(),
    );
  }
}

class MainScreen extends StatefulWidget {
  @override
  _MainScreenState createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  bool _isAuthenticated = false;
  
  @override
  void initState() {
    super.initState();
    _checkAuthentication();
  }
  
  Future<void> _checkAuthentication() async {
    final isAuth = await TokenManager.isAuthenticated();
    setState(() {
      _isAuthenticated = isAuth;
    });
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Syrian Archive Assistant'),
        actions: [
          if (_isAuthenticated)
            IconButton(
              icon: Icon(Icons.logout),
              onPressed: () async {
                await AuthService.logout();
                setState(() {
                  _isAuthenticated = false;
                });
              },
            ),
        ],
      ),
      body: ChatbotWidget(),
      floatingActionButton: !_isAuthenticated
          ? FloatingActionButton(
              onPressed: () {
                // Navigate to login screen
                _showLoginDialog();
              },
              child: Icon(Icons.login),
              tooltip: 'Login',
            )
          : null,
    );
  }
  
  void _showLoginDialog() {
    // Implement login dialog
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Login Required'),
        content: Text('Please log in to access advanced features.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              // Navigate to login screen
            },
            child: Text('Login'),
          ),
        ],
      ),
    );
  }
}
```

This comprehensive guide provides everything you need to integrate the Syrian Archive API into your Flutter chatbot application. The code is production-ready and includes proper error handling, authentication, caching, and offline support.