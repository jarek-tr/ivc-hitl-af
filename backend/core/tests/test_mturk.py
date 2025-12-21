"""MTurk integration tests"""
import pytest
from unittest.mock import Mock, patch
from core.mturk import _map_assignment_status, _parse_mturk_answers
from core.models import Assignment, Task, TaskType, TaskDefinition, Project, Asset


class TestMTurkStatusMapping:
    """Test MTurk assignment status mapping."""

    def test_map_approved_status(self):
        """Test approved status mapping."""
        assert _map_assignment_status('Approved') == 'approved'
        assert _map_assignment_status('APPROVED') == 'approved'

    def test_map_rejected_status(self):
        """Test rejected status mapping."""
        assert _map_assignment_status('Rejected') == 'rejected'
        assert _map_assignment_status('REJECTED') == 'rejected'

    def test_map_returned_status(self):
        """Test returned status mapping."""
        assert _map_assignment_status('Returned') == 'returned'
        assert _map_assignment_status('RETURNED') == 'returned'

    def test_map_expired_status(self):
        """Test expired status mapping."""
        assert _map_assignment_status('Expired') == 'expired'

    def test_map_submitted_status(self):
        """Test submitted status (default)."""
        assert _map_assignment_status('Submitted') == 'submitted'
        assert _map_assignment_status('SUBMITTED') == 'submitted'
        assert _map_assignment_status('Unknown') == 'submitted'
        assert _map_assignment_status('') == 'submitted'


class TestMTurkAnswerParsing:
    """Test MTurk answer XML parsing."""

    def test_parse_empty_answer(self):
        """Test parsing empty answer."""
        result = _parse_mturk_answers('')
        assert result == {'fields': {}}

    def test_parse_simple_answer(self):
        """Test parsing simple MTurk answer XML."""
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <QuestionFormAnswers xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2005-10-01/QuestionFormAnswers.xsd">
          <Answer>
            <QuestionIdentifier>annotation</QuestionIdentifier>
            <FreeText>{"polygon": [[0,0], [1,1]]}</FreeText>
          </Answer>
        </QuestionFormAnswers>'''

        result = _parse_mturk_answers(xml)
        assert 'fields' in result
        assert 'annotation' in result['fields']
        assert 'annotation_json' in result
        assert result['annotation_json'] == {'polygon': [[0, 0], [1, 1]]}

    def test_parse_multiple_fields(self):
        """Test parsing multiple answer fields."""
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <QuestionFormAnswers xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2005-10-01/QuestionFormAnswers.xsd">
          <Answer>
            <QuestionIdentifier>field1</QuestionIdentifier>
            <FreeText>value1</FreeText>
          </Answer>
          <Answer>
            <QuestionIdentifier>field2</QuestionIdentifier>
            <FreeText>value2</FreeText>
          </Answer>
        </QuestionFormAnswers>'''

        result = _parse_mturk_answers(xml)
        assert result['fields']['field1'] == 'value1'
        assert result['fields']['field2'] == 'value2'


@pytest.mark.django_db
class TestAssignmentModel:
    """Test Assignment model."""

    def setup_method(self):
        """Set up test data."""
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

    def test_assignment_creation(self):
        """Test creating an assignment."""
        assignment = Assignment.objects.create(
            task=self.task,
            backend='mturk',
            hit_id='test-hit-123',
            status='created',
            sandbox=True
        )
        assert assignment.id is not None
        assert assignment.task == self.task
        assert assignment.status == 'created'

    def test_assignment_supports_returned_status(self):
        """Test that assignments support 'returned' status."""
        assignment = Assignment.objects.create(
            task=self.task,
            backend='mturk',
            hit_id='test-hit-123',
            status='returned',
            sandbox=True
        )
        assert assignment.status == 'returned'

    def test_assignment_touch_updates_timestamp(self):
        """Test that touch() updates the updated_at timestamp."""
        assignment = Assignment.objects.create(
            task=self.task,
            backend='mturk',
            hit_id='test-hit-123',
            status='created',
            sandbox=True
        )
        original_updated = assignment.updated_at
        assignment.touch()
        assert assignment.updated_at > original_updated
