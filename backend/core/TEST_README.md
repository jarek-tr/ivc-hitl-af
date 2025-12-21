# Core Module Unit Tests

This document describes the unit tests for the core module and how to run them.

## Test Coverage

The test suite (`tests.py`) includes comprehensive unit tests for the following components:

### 1. `GetMturkClientTestCase` - MTurk Client Configuration
Tests that `get_mturk_client()` returns the correct boto3 client configuration:
- ✅ Sandbox environment endpoint
- ✅ Production environment endpoint
- ✅ AWS region configuration from settings
- ✅ Environment variable overrides for region and endpoint

### 2. `ExternalQuestionXmlTestCase` - XML Generation
Tests that `external_question_xml()` generates valid XML with proper escaping:
- ✅ Simple URL generation
- ✅ URL with query parameters (ampersand escaping)
- ✅ URL with special characters (`<`, `>`, `"`, `&`)
- ✅ Custom frame height parameter
- ✅ Well-formed XML validation

### 3. `ParseMturkAnswersTestCase` - XML Parsing
Tests that `_parse_mturk_answers()` correctly extracts annotation data:
- ✅ Valid XML with annotation JSON
- ✅ Multiple answer fields
- ✅ Malformed XML handling
- ✅ Empty and None input handling
- ✅ Invalid JSON in annotation field
- ✅ XML without namespace
- ✅ Empty field values

### 4. `AnnotationSerializerTestCase` - Serializer Validation
Tests that `AnnotationSerializer` handles idempotency and validation:
- ✅ Automatic submission_id generation
- ✅ Preserving provided submission_id
- ✅ Default empty raw_payload
- ✅ Valid assignment-task relationship
- ✅ Invalid assignment-task relationship rejection
- ✅ Optional assignment field handling
- ✅ Full annotation creation with all fields

### 5. `ValidatePluginManifestTestCase` - Plugin Manifest Validation
Tests that `validate_plugin_manifest()` validates plugin manifests correctly:
- ✅ Complete valid manifest
- ✅ Missing required fields detection
- ✅ Type validation (manifest must be dict)
- ✅ Path safety - absolute path rejection
- ✅ Path safety - parent directory traversal (`..`) rejection
- ✅ Path safety - asset file traversal rejection
- ✅ Directory and file existence validation
- ✅ Field type validation (js/css must be lists)
- ✅ result_schema_version type validation
- ✅ Empty asset path rejection
- ✅ Extra fields preservation
- ✅ Empty js/css lists allowed

## Running the Tests

### Prerequisites

1. **Database Setup**: Tests require a PostgreSQL database connection. You can either:
   - Use the existing Docker database (ensure it's running)
   - Configure a test database in environment variables
   - Override database settings to use SQLite for testing

2. **Environment Variables**: Set up your `.env` file or export:
   ```bash
   export POSTGRES_HOST=localhost
   export POSTGRES_DB=ivc_hitl_af_test
   export POSTGRES_USER=ivc
   export POSTGRES_PASSWORD=ivc
   export MTURK_SANDBOX=1
   ```

### Run All Tests

```bash
cd /Users/jarek/Code/ivc-hitl-af/backend
python manage.py test core.tests
```

### Run Specific Test Classes

```bash
# Test MTurk client only
python manage.py test core.tests.GetMturkClientTestCase

# Test XML generation only
python manage.py test core.tests.ExternalQuestionXmlTestCase

# Test XML parsing only
python manage.py test core.tests.ParseMturkAnswersTestCase

# Test annotation serializer only
python manage.py test core.tests.AnnotationSerializerTestCase

# Test plugin validation only
python manage.py test core.tests.ValidatePluginManifestTestCase
```

### Run Specific Test Methods

```bash
# Test single method
python manage.py test core.tests.GetMturkClientTestCase.test_sandbox_environment
```

### Run with Verbose Output

```bash
python manage.py test core.tests -v 2
```

### Run with Coverage (if coverage.py is installed)

```bash
coverage run --source='.' manage.py test core.tests
coverage report
coverage html  # Generate HTML report
```

## Test Statistics

- **Total Test Cases**: 5 test classes
- **Total Test Methods**: 40+ individual tests
- **Mocking**: Uses `unittest.mock` for external dependencies (boto3, file system)
- **Database**: Uses Django's TestCase for transaction rollback

## Notes

- Tests use Django's `TestCase` which provides automatic transaction rollback
- External dependencies (boto3, file system) are mocked to avoid side effects
- Plugin validation tests create temporary directories in `setUp()` and clean them in `tearDown()`
- All tests are isolated and can run in any order
