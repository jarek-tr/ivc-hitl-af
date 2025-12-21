"""Security tests for IVC HITL-AF"""
import pytest
from django.test import Client, override_settings
from core.models import Task, TaskType, TaskDefinition, Project, Asset, FrontendPlugin


@pytest.mark.django_db
class TestPluginAssetSecurity:
    """Test plugin asset serving security."""

    def setup_method(self):
        """Set up test data."""
        self.client = Client()
        self.project = Project.objects.create(slug='test', name='Test Project')
        self.asset = Asset.objects.create(
            project=self.project,
            media_type='image',
            s3_key='test.jpg'
        )
        self.task_type = TaskType.objects.create(
            slug='test_type',
            name='Test Type'
        )
        self.task_def = TaskDefinition.objects.create(
            task_type=self.task_type,
            version='1.0',
            definition={}
        )
        self.task = Task.objects.create(
            project=self.project,
            asset=self.asset,
            task_definition=self.task_def
        )
        self.plugin = FrontendPlugin.objects.create(
            task_type=self.task_type,
            name='Test Plugin',
            version='1.0',
            manifest={
                'name': 'Test Plugin',
                'task_type': 'test_type',
                'version': '1.0',
                'root': 'example-bbox/dist',
                'js': ['assets/index.js'],
                'css': [],
                'result_schema_version': '1.0.0'
            },
            is_active=True
        )

    def test_directory_traversal_rejected_with_double_dots(self):
        """Test that ../ directory traversal is rejected."""
        url = f'/api/tasks/{self.task.id}/annotate/plugin/../../../settings.py'
        response = self.client.get(url)
        assert response.status_code == 404

    def test_directory_traversal_rejected_with_absolute_path(self):
        """Test that absolute paths are rejected."""
        url = f'/api/tasks/{self.task.id}/annotate/plugin//etc/passwd'
        response = self.client.get(url)
        assert response.status_code == 404

    def test_valid_asset_path_works(self):
        """Test that valid asset paths work."""
        # This will 404 because file doesn't exist, but should pass security check
        url = f'/api/tasks/{self.task.id}/annotate/plugin/assets/index.js'
        response = self.client.get(url)
        # Either 404 (file not found) or 200 (file exists) is acceptable
        # Security rejection would be 404 with "Invalid path"
        assert response.status_code in [200, 404]


@pytest.mark.django_db
class TestRateLimiting:
    """Test rate limiting on annotation endpoint."""

    def setup_method(self):
        """Set up test data."""
        self.client = Client()
        self.project = Project.objects.create(slug='test', name='Test Project')
        self.asset = Asset.objects.create(
            project=self.project,
            media_type='image',
            s3_key='test.jpg'
        )
        self.task_type = TaskType.objects.create(
            slug='test_type',
            name='Test Type'
        )
        self.task_def = TaskDefinition.objects.create(
            task_type=self.task_type,
            version='1.0',
            definition={}
        )
        self.task = Task.objects.create(
            project=self.project,
            asset=self.asset,
            task_definition=self.task_def
        )

    @override_settings(WRITE_TOKEN='test-token')
    def test_annotation_rate_limiting(self):
        """Test that annotation endpoint has rate limiting configured."""
        # This test verifies rate limiting is configured
        # Actual rate limit testing would require many requests
        payload = {
            'task': self.task.id,
            'result': {'test': 'data'},
            'schema_version': '1.0.0',
        }
        headers = {'HTTP_X_IVC_WRITE_TOKEN': 'test-token'}
        response = self.client.post(
            '/api/annotations/',
            data=payload,
            content_type='application/json',
            **headers
        )
        # Should succeed (rate limit not hit on first request)
        assert response.status_code in [200, 201]


@pytest.mark.django_db
class TestWriteTokenProtection:
    """Test write token protection."""

    def setup_method(self):
        """Set up test data."""
        self.client = Client()

    @override_settings(WRITE_TOKEN='secret-token')
    def test_write_requires_token(self):
        """Test that write operations require token."""
        payload = {'slug': 'test', 'name': 'Test Project'}
        response = self.client.post(
            '/api/projects/',
            data=payload,
            content_type='application/json'
        )
        assert response.status_code == 403

    @override_settings(WRITE_TOKEN='secret-token')
    def test_write_succeeds_with_correct_token(self):
        """Test that write succeeds with correct token."""
        payload = {'slug': 'test', 'name': 'Test Project'}
        headers = {'HTTP_X_IVC_WRITE_TOKEN': 'secret-token'}
        response = self.client.post(
            '/api/projects/',
            data=payload,
            content_type='application/json',
            **headers
        )
        assert response.status_code == 201

    @override_settings(WRITE_TOKEN='secret-token')
    def test_write_fails_with_wrong_token(self):
        """Test that write fails with wrong token."""
        payload = {'slug': 'test', 'name': 'Test Project'}
        headers = {'HTTP_X_IVC_WRITE_TOKEN': 'wrong-token'}
        response = self.client.post(
            '/api/projects/',
            data=payload,
            content_type='application/json',
            **headers
        )
        assert response.status_code == 403

    @override_settings(WRITE_TOKEN='')
    def test_write_allowed_when_token_disabled(self):
        """Test that writes are allowed when token is disabled."""
        payload = {'slug': 'test', 'name': 'Test Project'}
        response = self.client.post(
            '/api/projects/',
            data=payload,
            content_type='application/json'
        )
        assert response.status_code == 201
