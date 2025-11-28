# Test Suite for George Jetson Dashcam

Comprehensive unit and integration tests for security features and core functionality.

## Test Coverage

### Security Tests (`test_web_server.py`)
- ✅ Random Flask secret key generation
- ✅ Rate limiting (5 attempts, 5-minute lockout)
- ✅ Input validation (date format, string sanitization)
- ✅ Production mode enforcement
- ✅ API endpoint authentication
- ✅ Dangerous input sanitization (SQL injection, XSS)

### Logging Tests (`test_utils.py`)
- ✅ Log rotation setup and configuration
- ✅ Automatic rotation when size limit reached
- ✅ Backup count enforcement
- ✅ Utility functions (GPS parsing, formatting, etc.)
- ✅ Configuration manager

### Resource Management Tests (`test_video_recorder.py`)
- ✅ Encoder cleanup (normal shutdown)
- ✅ Encoder cleanup (timeout handling)
- ✅ Encoder cleanup (error handling)
- ✅ Camera resource cleanup
- ✅ Cleanup on exception in recording loop
- ✅ FFmpeg command generation

### Integration Tests (`test_integration.py`)
- ✅ Full login workflow with rate limiting
- ✅ Successful login clears failed attempts
- ✅ API input validation end-to-end
- ✅ Database operations with search
- ✅ File permissions verification

## Running Tests

### Run All Tests
```bash
cd /opt/george-jetson
python3 run_tests.py
```

### Run Specific Test Module
```bash
python3 run_tests.py -t test_web_server
python3 run_tests.py -t test_utils
python3 run_tests.py -t test_video_recorder
python3 run_tests.py -t test_integration
```

### Run with Different Verbosity
```bash
# Quiet (only show failures)
python3 run_tests.py -v 0

# Normal
python3 run_tests.py -v 1

# Verbose (default)
python3 run_tests.py -v 2
```

### List Available Tests
```bash
python3 run_tests.py --list
```

### Run Specific Pattern
```bash
# Only integration tests
python3 run_tests.py -p "test_integration*.py"

# Only security tests
python3 run_tests.py -p "test_web*.py"
```

## Test Structure

```
tests/
├── __init__.py                  # Package marker
├── test_web_server.py           # Web security tests (150+ lines)
├── test_utils.py                # Utility & logging tests (200+ lines)
├── test_video_recorder.py       # Resource cleanup tests (150+ lines)
└── test_integration.py          # End-to-end tests (100+ lines)
```

## Test Statistics

- **Total Test Files:** 4
- **Total Test Cases:** 40+
- **Total Test Lines:** 600+
- **Coverage Areas:**
  - Security: 15 tests
  - Logging: 10 tests
  - Resource Management: 8 tests
  - Integration: 7+ tests

## Requirements

Install test dependencies:
```bash
pip install -r requirements-test.txt
```

Or manually:
```bash
pip install Flask werkzeug
```

## Example Test Output

```
======================================================================
GEORGE JETSON DASHCAM - TEST SUITE
======================================================================

Running all tests (pattern: test_*.py)

test_backup_count_limit (tests.test_utils.TestLoggingRotation) ... ok
test_log_rotation_occurs (tests.test_utils.TestLoggingRotation) ... ok
test_log_rotation_setup (tests.test_utils.TestLoggingRotation) ... ok
test_random_secret_key_generated (tests.test_web_server.TestWebServerSecurity) ... ok
test_rate_limiting_initialization (tests.test_web_server.TestWebServerSecurity) ... ok
test_rate_limiting_lockout (tests.test_web_server.TestWebServerSecurity) ... ok
test_sanitize_string_function (tests.test_web_server.TestWebServerSecurity) ... ok
test_validate_date_function (tests.test_web_server.TestWebServerSecurity) ... ok
...

======================================================================
TEST SUMMARY
======================================================================
Tests run: 42
Successes: 42
Failures: 0
Errors: 0
Skipped: 0

✅ ALL TESTS PASSED!
======================================================================
```

## Continuous Integration

Add to your CI/CD pipeline:

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.8'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      - name: Run tests
        run: python3 run_tests.py
```

## Writing New Tests

### Template for New Test
```python
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.your_module import YourClass

class TestYourFeature(unittest.TestCase):
    """Test your feature."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.instance = YourClass()
    
    def tearDown(self):
        """Clean up after tests."""
        pass
    
    def test_your_feature(self):
        """Test specific functionality."""
        result = self.instance.your_method()
        self.assertEqual(result, expected_value)

if __name__ == '__main__':
    unittest.main()
```

## Debugging Failed Tests

### Run with Python debugger
```bash
python3 -m pdb run_tests.py -t test_web_server
```

### Run single test method
```bash
python3 -m unittest tests.test_web_server.TestWebServerSecurity.test_rate_limiting_lockout
```

### Show test output
```bash
python3 run_tests.py -v 2 2>&1 | tee test_output.log
```

## Test Coverage Report

To generate coverage report:
```bash
pip install coverage
coverage run run_tests.py
coverage report
coverage html  # Generate HTML report
```

## Known Test Limitations

1. **Camera Tests:** Requires actual camera hardware (mocked in tests)
2. **GPU Tests:** NVENC encoder tests require NVIDIA GPU
3. **Network Tests:** Some tests assume localhost access
4. **File System:** Tests create temporary files/directories

## Troubleshooting

### Import Errors
```bash
# Ensure project is in Python path
export PYTHONPATH=/opt/george-jetson:$PYTHONPATH
```

### Permission Errors
```bash
# Ensure test directories are writable
chmod 755 /opt/george-jetson/tests
```

### Missing Dependencies
```bash
# Install all requirements
pip install -r requirements.txt
pip install Flask werkzeug
```

## Contributing

When adding new features:
1. Write tests first (TDD)
2. Ensure all tests pass
3. Aim for >80% code coverage
4. Document test purpose clearly

## License

Same as main project.
