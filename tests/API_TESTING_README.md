# Syrian Archive API Testing Suite

This comprehensive testing suite provides complete coverage for all API endpoints in the Syrian Archive application. It includes both standalone HTTP tests and Django-integrated unit tests.

## 📋 Test Coverage

The test suite covers all major API endpoints:

### Authentication & User Management
- ✅ User registration (`/api/register/`)
- ✅ User login (`/api/login/`)
- ✅ Token refresh (`/api/token/refresh/`)
- ✅ User profile management (`/api/profile/`)
- ✅ User listing and details (`/api/users/`)
- ✅ Password change and reset

### Post Management
- ✅ Create, read, update, delete posts (`/api/posts/`)
- ✅ Post verification (`/api/posts/{id}/verify/`)
- ✅ Post trust/untrust (`/api/posts/{id}/trust/`)
- ✅ Post like/unlike (`/api/posts/{id}/like/`, `/api/posts/{id}/unlike/`)
- ✅ Post reporting (`/api/posts/{id}/report/`)

### Comment Management
- ✅ Create, read, update, delete comments (`/api/comments/`)
- ✅ Comment listing and filtering

### Person Management
- ✅ Create, read, update, delete persons (`/api/persons/`)
- ✅ Person role management

### Event Management
- ✅ Create, read, update, delete events (`/api/events/`)
- ✅ Event date and location handling

### Verification Requests
- ✅ Create, read, update verification requests (`/api/verification-requests/`)
- ✅ Request type validation

### Payment & Auth System
- ✅ Payment methods (`/auth_payments/api/payment-methods/`)
- ✅ Payment history (`/auth_payments/api/payment-history/`)
- ✅ Subscriptions (`/auth_payments/api/subscriptions/`)
- ✅ Payment statistics and refunds

### Error Handling
- ✅ Unauthorized access (401)
- ✅ Forbidden access (403)
- ✅ Not found errors (404)
- ✅ Validation errors (400)
- ✅ Method not allowed (405)

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+** installed
2. **Django project** set up and running
3. **Database** configured and migrated

### Installation

1. Install test dependencies:
```bash
pip install -r test_requirements.txt
```

2. Make sure your Django server is running:
```bash
python manage.py runserver
```

### Running All Tests

**Option 1: Use the automated test runner (Recommended)**
```bash
python run_tests.py
```

**Option 2: Run with automatic server startup**
```bash
python run_tests.py --start-server
```

**Option 3: Install dependencies and run tests**
```bash
python run_tests.py --install-deps --start-server
```

## 🔧 Advanced Usage

### Running Specific Test Types

**Django Integrated Tests Only:**
```bash
python run_tests.py --django-only
```

**Standalone API Tests Only:**
```bash
python run_tests.py --standalone-only
```

**Custom API URL:**
```bash
python run_tests.py --url http://localhost:8080
```

### Running Individual Test Files

**Standalone HTTP Tests:**
```bash
python test_api_endpoints.py
```

**Django Unit Tests:**
```bash
python manage.py test tests.test_api_comprehensive
```

**Specific Test Class:**
```bash
python manage.py test tests.test_api_comprehensive.AuthenticationTestCase
```

**Specific Test Method:**
```bash
python manage.py test tests.test_api_comprehensive.AuthenticationTestCase.test_user_login
```

## 📁 Test Files Structure

```
syrian_archive/
├── test_api_endpoints.py          # Standalone HTTP API tests
├── tests/
│   └── test_api_comprehensive.py  # Django integrated unit tests
├── run_tests.py                   # Automated test runner
├── test_requirements.txt          # Test dependencies
└── API_TESTING_README.md          # This documentation
```

## 🧪 Test Types Explained

### 1. Standalone HTTP Tests (`test_api_endpoints.py`)

**What it does:**
- Makes real HTTP requests to your running Django server
- Tests the complete request/response cycle
- Validates authentication flows with JWT tokens
- Tests error handling and edge cases
- Creates and cleans up test data

**When to use:**
- Integration testing
- End-to-end API validation
- Testing with real HTTP clients
- Validating complete authentication flows

**Example output:**
```
=== Testing Authentication ===
[PASS] User Registration - User registered successfully
[PASS] User Login - Login successful, tokens received
[PASS] Token Refresh - New access token received

=== Testing Post Endpoints ===
[PASS] Create Post - Post created with ID: 123
[PASS] List Posts - Posts list retrieved successfully
[PASS] Get Specific Post - Post details retrieved successfully
```

### 2. Django Integrated Tests (`tests/test_api_comprehensive.py`)

**What it does:**
- Uses Django's built-in test framework
- Tests API views directly without HTTP overhead
- Uses test database with automatic rollback
- Faster execution than HTTP tests
- Better for unit testing individual components

**When to use:**
- Unit testing
- Fast development feedback
- Testing database interactions
- Continuous integration pipelines

**Example output:**
```
test_user_login (tests.test_api_comprehensive.AuthenticationTestCase) ... ok
test_user_registration (tests.test_api_comprehensive.AuthenticationTestCase) ... ok
test_create_post (tests.test_api_comprehensive.PostManagementTestCase) ... ok

----------------------------------------------------------------------
Ran 45 tests in 12.345s

OK
```

## 🔍 Understanding Test Results

### Success Indicators
- ✅ `[PASS]` - Test passed successfully
- ✅ `ok` - Django test passed
- 🎉 `ALL TESTS PASSED!` - Complete success

### Failure Indicators
- ❌ `[FAIL]` - Test failed
- ❌ `FAIL` - Django test failed
- 💥 `SOME TESTS FAILED!` - Some tests need attention

### Common Status Codes
- `200 OK` - Successful GET/PATCH requests
- `201 Created` - Successful POST requests
- `204 No Content` - Successful DELETE requests
- `400 Bad Request` - Validation errors
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Permission denied
- `404 Not Found` - Resource not found
- `405 Method Not Allowed` - Wrong HTTP method

## 🛠️ Troubleshooting

### Common Issues

**1. Server Not Running**
```
⚠️ Warning: Server not responding at http://127.0.0.1:8000
```
**Solution:** Start your Django server or use `--start-server` flag

**2. Database Errors**
```
django.db.utils.OperationalError: no such table
```
**Solution:** Run migrations: `python manage.py migrate`

**3. Import Errors**
```
ModuleNotFoundError: No module named 'api.models'
```
**Solution:** Make sure your Django app is properly configured

**4. Authentication Failures**
```
[FAIL] User Login - Status: 400
```
**Solution:** Check your authentication settings and user creation

**5. Permission Errors**
```
[FAIL] Trust Post - Status: 403
```
**Solution:** This is expected for regular users; admin permissions required

### Debug Mode

For detailed debugging, you can modify the test files:

**Enable verbose output in standalone tests:**
```python
# In test_api_endpoints.py, add this to see full responses
print(f"Response: {response.text}")
```

**Enable verbose Django test output:**
```bash
python manage.py test tests.test_api_comprehensive --verbosity=3
```

## 📊 Test Metrics

The test suite provides comprehensive metrics:

- **Total Tests:** ~50+ individual test cases
- **Coverage:** All major API endpoints
- **Execution Time:** 
  - Django tests: ~10-30 seconds
  - Standalone tests: ~30-60 seconds
- **Success Rate:** Displayed as percentage

## 🔄 Continuous Integration

To integrate with CI/CD pipelines:

**GitHub Actions Example:**
```yaml
- name: Run API Tests
  run: |
    python run_tests.py --install-deps --start-server
```

**Jenkins Example:**
```bash
#!/bin/bash
python run_tests.py --install-deps
if [ $? -eq 0 ]; then
    echo "All tests passed!"
else
    echo "Tests failed!"
    exit 1
fi
```

## 📝 Adding New Tests

### For Standalone Tests

1. Add new test method to `APITester` class in `test_api_endpoints.py`:
```python
def test_new_endpoint(self):
    """Test new endpoint functionality"""
    response = self.make_request('GET', '/api/new-endpoint/')
    if response and response.status_code == 200:
        self.log_test("New Endpoint", True, "Endpoint works")
    else:
        self.log_test("New Endpoint", False, f"Status: {response.status_code}")
```

2. Call it in `run_all_tests()` method:
```python
self.test_new_endpoint()
```

### For Django Tests

1. Add new test class or method to `tests/test_api_comprehensive.py`:
```python
class NewEndpointTestCase(BaseAPITestCase):
    def test_new_functionality(self):
        """Test new functionality"""
        self.authenticate_user()
        response = self.client.get('/api/new-endpoint/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
```

## 🤝 Contributing

When adding new API endpoints:

1. **Add tests first** (TDD approach)
2. **Test both success and failure cases**
3. **Include authentication tests**
4. **Test data validation**
5. **Update this documentation**

## 📞 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Verify your Django setup is correct
3. Ensure all dependencies are installed
4. Check that your database is properly migrated
5. Verify your API endpoints are correctly configured

---

**Happy Testing! 🚀**

This comprehensive test suite ensures your Syrian Archive API is robust, reliable, and ready for production use.