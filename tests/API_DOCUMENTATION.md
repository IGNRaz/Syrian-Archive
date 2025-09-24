# Syrian Archive API Documentation

This API provides programmatic access to the Syrian Archive platform functionality, mirroring the web interface capabilities.

## Base URL
```
http://127.0.0.1:8000/api/
```

## Authentication

The API uses JWT (JSON Web Token) authentication. Most endpoints require authentication.

### Login
```
POST /api/auth/login/
```
**Request Body:**
```json
{
    "username": "your_username",
    "password": "your_password"
}
```
**Response:**
```json
{
    "refresh": "refresh_token_here",
    "access": "access_token_here",
    "user": {
        "id": 1,
        "username": "username",
        "email": "user@example.com",
        "role": "normal",
        "identity_confirmed": false
    }
}
```

### Using JWT Tokens
Include the access token in the Authorization header:
```
Authorization: Bearer your_access_token_here
```

## User Endpoints

### List Users
```
GET /api/users/
```
Returns a paginated list of active, non-banned users.

### Get User Details
```
GET /api/users/{user_id}/
```
Returns details for a specific user.

### Get Current User Profile
```
GET /api/profile/
```
Returns the authenticated user's profile information.

### Update Current User Profile
```
PUT /api/profile/
PATCH /api/profile/
```
Update the authenticated user's profile information.

## Post Endpoints

### List Posts
```
GET /api/posts/
```
Returns a paginated list of approved posts.

**Query Parameters:**
- `search`: Search in title and content
- `user`: Filter by user ID
- `event`: Filter by event ID

### Create Post
```
POST /api/posts/
```
**Request Body:**
```json
{
    "title": "Post Title",
    "content": "Post content here",
    "attachment": "file_upload_optional",
    "event": "event_id_optional"
}
```

### Get Post Details
```
GET /api/posts/{post_id}/
```
Returns detailed information about a specific post including comments, likes, and verifications.

### Update Post
```
PUT /api/posts/{post_id}/
PATCH /api/posts/{post_id}/
```
Update a post (only allowed for post owner).

### Delete Post
```
DELETE /api/posts/{post_id}/
```
Delete a post (only allowed for post owner).

### Get My Posts
```
GET /api/posts/my/
```
Returns all posts created by the authenticated user.

## Post Interactions

### Like/Unlike Post
```
POST /api/posts/{post_id}/like/
```
**Response:**
```json
{
    "liked": true,
    "likes_count": 5
}
```

### Trust/Untrust Post (Verification)
```
POST /api/posts/{post_id}/trust/
```
Only available for admins, journalists, and politicians.
**Response:**
```json
{
    "trusted": true,
    "trusts_count": 3,
    "is_verified": true
}
```

### Report Post
```
POST /api/posts/{post_id}/report/
```
**Request Body:**
```json
{
    "reason": "spam"  // Options: spam, fake_news, offensive, other
}
```

### Verify Post (Formal Verification)
```
POST /api/posts/{post_id}/verify/
```
Only available for journalists and politicians.

## Comment Endpoints

### List Comments for Post
```
GET /api/posts/{post_id}/comments/
```
Returns comments for a specific post.

### Create Comment
```
POST /api/posts/{post_id}/comments/
```
**Request Body:**
```json
{
    "content": "Comment content",
    "attachment": "file_upload_optional"
}
```

### Get Comment Details
```
GET /api/comments/{comment_id}/
```

### Update Comment
```
PUT /api/comments/{comment_id}/
PATCH /api/comments/{comment_id}/
```
Only allowed for comment owner.

### Delete Comment
```
DELETE /api/comments/{comment_id}/
```
Only allowed for comment owner.

## Person Endpoints

### List Persons
```
GET /api/persons/
```
Returns approved persons in the database.

### Create Person
```
POST /api/persons/
```
**Request Body:**
```json
{
    "name": "Person Name",
    "role": "victim",  // Options: victim, witness, perpetrator, journalist, activist, official, other
    "image": "image_upload_optional"
}
```

### Get Person Details
```
GET /api/persons/{person_id}/
```

## Event Endpoints

### List Events
```
GET /api/events/
```
Returns approved events.

### Create Event
```
POST /api/events/
```
**Request Body:**
```json
{
    "title": "Event Title",
    "description": "Event description",
    "date": "2024-01-01"
}
```

### Get Event Details
```
GET /api/events/{event_id}/
```

## Verification Request Endpoints

### Create Verification Request
```
POST /api/verification-requests/
```
**Request Body:**
```json
{
    "requested_role": "journalist",  // Options: journalist, politician
    "uid_document": "document_upload"
}
```

### Get My Verification Requests
```
GET /api/verification-requests/my/
```
Returns verification requests created by the authenticated user.

## Response Format

All API responses follow a consistent format:

### Success Response
```json
{
    "count": 100,
    "next": "http://127.0.0.1:8000/api/posts/?page=2",
    "previous": null,
    "results": [
        // Array of objects
    ]
}
```

### Error Response
```json
{
    "error": "Error message here"
}
```

### Validation Error Response
```json
{
    "field_name": [
        "This field is required."
    ]
}
```

## Status Codes

- `200 OK`: Successful GET, PUT, PATCH
- `201 Created`: Successful POST
- `204 No Content`: Successful DELETE
- `400 Bad Request`: Validation errors
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Permission denied
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

## Pagination

List endpoints support pagination with the following parameters:
- `page`: Page number (default: 1)
- `page_size`: Number of items per page (default: 10, max: 100)

## File Uploads

For endpoints that accept file uploads, use `multipart/form-data` content type.

## Rate Limiting

Currently, no rate limiting is implemented, but it's recommended for production use.

## Examples

### Creating a Post with cURL
```bash
curl -X POST http://127.0.0.1:8000/api/posts/ \
  -H "Authorization: Bearer your_access_token" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My Post Title",
    "content": "This is the content of my post"
  }'
```

### Getting Posts with JavaScript
```javascript
fetch('http://127.0.0.1:8000/api/posts/', {
  headers: {
    'Authorization': 'Bearer your_access_token'
  }
})
.then(response => response.json())
.then(data => console.log(data));
```