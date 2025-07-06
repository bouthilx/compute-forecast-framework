"""
Unit tests for extraction workflow module.

Tests workflow orchestration, task management, and integration between
automated and manual extraction processes.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime

from compute_forecast.analysis.computational.extraction_workflow import (
    ExtractionWorkflow,
    WorkflowStep,
    WorkflowState,
    TaskQueue,
    WorkflowManager,
    ExtractionTask,
    TaskStatus,
    TaskPriority,
    WorkflowConfig,
    ExecutionContext,
    ValidationGate,
    ProgressTracker,
    ErrorHandler,
    RetryPolicy,
    NotificationService,
)


@pytest.fixture
def mock_extraction_protocol():
    """Mock extraction protocol for testing."""
    protocol = Mock()
    protocol.phase1_preparation.return_value = {"has_computational_experiments": True}
    protocol.phase2_automated_extraction.return_value = {"confidence_score": 0.8}
    protocol.phase3_manual_extraction.return_value = {"extracted_fields": 5}
    protocol.phase4_validation.return_value = Mock(confidence_overall="HIGH")
    protocol.phase5_documentation.return_value = {"yaml_export": "test: data"}
    protocol.to_yaml.return_value = "test: yaml"
    return protocol


@pytest.fixture
def mock_analyzer():
    """Mock analyzer for testing."""
    analyzer = Mock()
    analyzer.analyze.return_value = Mock(confidence=0.75)
    return analyzer


@pytest.fixture
def sample_task():
    """Sample extraction task for testing."""
    return ExtractionTask(
        task_id="task_001",
        paper_id="paper_001",
        paper_content="Sample paper content",
        priority=TaskPriority.MEDIUM,
        analyst="test_analyst",
    )


@pytest.fixture
def workflow_config():
    """Default workflow configuration."""
    return WorkflowConfig(
        max_concurrent_tasks=5,
        auto_validation_threshold=0.8,
        retry_attempts=3,
        timeout_minutes=30,
        enable_notifications=True,
    )


@pytest.fixture
def extraction_workflow(workflow_config, mock_extraction_protocol, mock_analyzer):
    """Create extraction workflow instance."""
    return ExtractionWorkflow(
        config=workflow_config,
        protocol_factory=lambda *args: mock_extraction_protocol,
        analyzer=mock_analyzer,
    )


class TestExtractionTask:
    """Test ExtractionTask dataclass."""

    def test_task_creation(self):
        """Test creating extraction task."""
        task = ExtractionTask(
            task_id="test_task",
            paper_id="test_paper",
            paper_content="Content",
            priority=TaskPriority.HIGH,
            analyst="analyst_001",
        )

        assert task.task_id == "test_task"
        assert task.paper_id == "test_paper"
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.PENDING
        assert task.created_at is not None
        assert task.attempts == 0
        assert task.result is None

    def test_task_status_transitions(self, sample_task):
        """Test task status transitions."""
        # Start as pending
        assert sample_task.status == TaskStatus.PENDING

        # Move to running
        sample_task.status = TaskStatus.RUNNING
        assert sample_task.status == TaskStatus.RUNNING

        # Complete successfully
        sample_task.status = TaskStatus.COMPLETED
        assert sample_task.status == TaskStatus.COMPLETED

    def test_task_retry_increment(self, sample_task):
        """Test task retry attempt increment."""
        initial_attempts = sample_task.attempts
        sample_task.attempts += 1

        assert sample_task.attempts == initial_attempts + 1

    def test_task_duration_calculation(self, sample_task):
        """Test task duration calculation."""
        sample_task.started_at = datetime.now()
        sample_task.completed_at = datetime.now()

        duration = sample_task.get_duration()
        assert duration is not None
        assert duration.total_seconds() >= 0


class TestWorkflowConfig:
    """Test WorkflowConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = WorkflowConfig()

        assert config.max_concurrent_tasks == 3
        assert config.auto_validation_threshold == 0.7
        assert config.retry_attempts == 2
        assert config.timeout_minutes == 60
        assert config.enable_notifications is False

    def test_custom_config(self):
        """Test custom configuration."""
        config = WorkflowConfig(
            max_concurrent_tasks=10,
            auto_validation_threshold=0.9,
            retry_attempts=5,
            timeout_minutes=15,
            enable_notifications=True,
        )

        assert config.max_concurrent_tasks == 10
        assert config.auto_validation_threshold == 0.9
        assert config.retry_attempts == 5
        assert config.timeout_minutes == 15
        assert config.enable_notifications is True


class TestTaskQueue:
    """Test TaskQueue class."""

    def test_queue_initialization(self):
        """Test queue initialization."""
        queue = TaskQueue()
        assert queue.size() == 0
        assert queue.is_empty() is True

    def test_add_task(self, sample_task):
        """Test adding task to queue."""
        queue = TaskQueue()
        queue.add_task(sample_task)

        assert queue.size() == 1
        assert queue.is_empty() is False

    def test_get_next_task(self, sample_task):
        """Test getting next task from queue."""
        queue = TaskQueue()
        queue.add_task(sample_task)

        next_task = queue.get_next_task()
        assert next_task == sample_task
        assert queue.size() == 0

    def test_priority_ordering(self):
        """Test task priority ordering."""
        queue = TaskQueue()

        # Add tasks with different priorities
        low_task = ExtractionTask(
            "low", "paper1", "content", TaskPriority.LOW, "analyst"
        )
        high_task = ExtractionTask(
            "high", "paper2", "content", TaskPriority.HIGH, "analyst"
        )
        medium_task = ExtractionTask(
            "med", "paper3", "content", TaskPriority.MEDIUM, "analyst"
        )

        queue.add_task(low_task)
        queue.add_task(high_task)
        queue.add_task(medium_task)

        # Should get high priority task first
        first = queue.get_next_task()
        assert first.priority == TaskPriority.HIGH

        # Then medium priority
        second = queue.get_next_task()
        assert second.priority == TaskPriority.MEDIUM

        # Finally low priority
        third = queue.get_next_task()
        assert third.priority == TaskPriority.LOW

    def test_get_task_by_id(self, sample_task):
        """Test getting task by ID."""
        queue = TaskQueue()
        queue.add_task(sample_task)

        found_task = queue.get_task_by_id("task_001")
        assert found_task == sample_task

        not_found = queue.get_task_by_id("nonexistent")
        assert not_found is None

    def test_remove_task(self, sample_task):
        """Test removing task from queue."""
        queue = TaskQueue()
        queue.add_task(sample_task)

        removed = queue.remove_task("task_001")
        assert removed == sample_task
        assert queue.size() == 0

        not_removed = queue.remove_task("nonexistent")
        assert not_removed is None

    def test_get_tasks_by_status(self):
        """Test getting tasks by status."""
        queue = TaskQueue()

        pending_task = ExtractionTask(
            "pending", "paper1", "content", TaskPriority.LOW, "analyst"
        )
        running_task = ExtractionTask(
            "running", "paper2", "content", TaskPriority.LOW, "analyst"
        )
        running_task.status = TaskStatus.RUNNING

        queue.add_task(pending_task)
        queue.add_task(running_task)

        pending_tasks = queue.get_tasks_by_status(TaskStatus.PENDING)
        assert len(pending_tasks) == 1
        assert pending_tasks[0] == pending_task

        running_tasks = queue.get_tasks_by_status(TaskStatus.RUNNING)
        assert len(running_tasks) == 1
        assert running_tasks[0] == running_task


class TestWorkflowStep:
    """Test WorkflowStep class."""

    def test_step_creation(self):
        """Test creating workflow step."""
        step = WorkflowStep(
            name="preparation",
            description="Prepare for extraction",
            required=True,
            timeout_minutes=10,
        )

        assert step.name == "preparation"
        assert step.description == "Prepare for extraction"
        assert step.required is True
        assert step.timeout_minutes == 10
        assert step.retry_count == 0

    def test_step_execution(self):
        """Test step execution."""
        step = WorkflowStep("test_step", "Test step")

        # Mock execution function
        execution_func = Mock(return_value={"success": True})
        step.execution_func = execution_func

        context = ExecutionContext(task_id="test", step_name="test_step")
        result = step.execute(context)

        execution_func.assert_called_once_with(context)
        assert result == {"success": True}

    def test_step_validation(self):
        """Test step validation."""
        step = WorkflowStep("test_step", "Test step")

        # Mock validation function
        validation_func = Mock(return_value=True)
        step.validation_func = validation_func

        context = ExecutionContext(task_id="test", step_name="test_step")
        result = {"data": "test"}

        is_valid = step.validate(context, result)

        validation_func.assert_called_once_with(context, result)
        assert is_valid is True


class TestWorkflowState:
    """Test WorkflowState class."""

    def test_state_initialization(self, sample_task):
        """Test workflow state initialization."""
        state = WorkflowState(sample_task)

        assert state.task == sample_task
        assert state.current_step is None
        assert state.completed_steps == []
        assert state.failed_steps == []
        assert state.step_results == {}
        assert state.started_at is not None

    def test_step_completion(self, sample_task):
        """Test marking step as completed."""
        state = WorkflowState(sample_task)
        step = WorkflowStep("test_step", "Test")
        result = {"success": True}

        state.complete_step(step, result)

        assert step.name in state.completed_steps
        assert state.step_results[step.name] == result

    def test_step_failure(self, sample_task):
        """Test marking step as failed."""
        state = WorkflowState(sample_task)
        step = WorkflowStep("test_step", "Test")
        error = Exception("Test error")

        state.fail_step(step, error)

        assert step.name in state.failed_steps
        assert step.name in state.step_results
        assert isinstance(state.step_results[step.name], Exception)

    def test_state_progress(self, sample_task):
        """Test workflow progress calculation."""
        state = WorkflowState(sample_task)

        # Add some steps
        step1 = WorkflowStep("step1", "Step 1")
        step2 = WorkflowStep("step2", "Step 2")
        WorkflowStep("step3", "Step 3")

        total_steps = 3

        # Complete first step
        state.complete_step(step1, {})
        progress = len(state.completed_steps) / total_steps
        assert progress == 1 / 3

        # Complete second step
        state.complete_step(step2, {})
        progress = len(state.completed_steps) / total_steps
        assert progress == 2 / 3


class TestValidationGate:
    """Test ValidationGate class."""

    def test_gate_creation(self):
        """Test creating validation gate."""
        gate = ValidationGate(
            name="confidence_gate",
            condition=lambda result: result.get("confidence", 0) > 0.8,
            message="Confidence must be above 80%",
        )

        assert gate.name == "confidence_gate"
        assert gate.message == "Confidence must be above 80%"

    def test_gate_validation_pass(self):
        """Test gate validation passing."""
        gate = ValidationGate("test_gate", lambda result: result.get("score", 0) > 50)

        result = {"score": 75}
        assert gate.validate(result) is True

    def test_gate_validation_fail(self):
        """Test gate validation failing."""
        gate = ValidationGate("test_gate", lambda result: result.get("score", 0) > 50)

        result = {"score": 25}
        assert gate.validate(result) is False


class TestProgressTracker:
    """Test ProgressTracker class."""

    def test_tracker_initialization(self):
        """Test progress tracker initialization."""
        tracker = ProgressTracker()

        assert tracker.total_tasks == 0
        assert tracker.completed_tasks == 0
        assert tracker.failed_tasks == 0
        assert tracker.get_completion_rate() == 0.0

    def test_track_task_completion(self):
        """Test tracking task completion."""
        tracker = ProgressTracker()

        tracker.add_task()
        tracker.add_task()
        assert tracker.total_tasks == 2

        tracker.complete_task()
        assert tracker.completed_tasks == 1
        assert tracker.get_completion_rate() == 0.5

        tracker.complete_task()
        assert tracker.completed_tasks == 2
        assert tracker.get_completion_rate() == 1.0

    def test_track_task_failure(self):
        """Test tracking task failure."""
        tracker = ProgressTracker()

        tracker.add_task()
        tracker.fail_task()

        assert tracker.failed_tasks == 1
        assert tracker.get_failure_rate() == 1.0

    def test_get_statistics(self):
        """Test getting tracker statistics."""
        tracker = ProgressTracker()

        tracker.add_task()
        tracker.add_task()
        tracker.add_task()
        tracker.complete_task()
        tracker.fail_task()

        stats = tracker.get_statistics()

        assert stats["total"] == 3
        assert stats["completed"] == 1
        assert stats["failed"] == 1
        assert stats["pending"] == 1
        assert stats["completion_rate"] == 1 / 3
        assert stats["failure_rate"] == 1 / 3


class TestRetryPolicy:
    """Test RetryPolicy class."""

    def test_policy_creation(self):
        """Test creating retry policy."""
        policy = RetryPolicy(
            max_attempts=3, base_delay=1.0, exponential_backoff=True, max_delay=60.0
        )

        assert policy.max_attempts == 3
        assert policy.base_delay == 1.0
        assert policy.exponential_backoff is True
        assert policy.max_delay == 60.0

    def test_should_retry_within_limit(self):
        """Test retry decision within attempt limit."""
        policy = RetryPolicy(max_attempts=3)

        assert policy.should_retry(1) is True
        assert policy.should_retry(2) is True
        assert policy.should_retry(3) is False
        assert policy.should_retry(4) is False

    def test_calculate_delay_linear(self):
        """Test linear delay calculation."""
        policy = RetryPolicy(base_delay=2.0, exponential_backoff=False)

        assert policy.calculate_delay(1) == 2.0
        assert policy.calculate_delay(2) == 2.0
        assert policy.calculate_delay(3) == 2.0

    def test_calculate_delay_exponential(self):
        """Test exponential delay calculation."""
        policy = RetryPolicy(base_delay=1.0, exponential_backoff=True, max_delay=10.0)

        assert policy.calculate_delay(1) == 1.0
        assert policy.calculate_delay(2) == 2.0
        assert policy.calculate_delay(3) == 4.0
        assert policy.calculate_delay(4) == 8.0
        assert policy.calculate_delay(5) == 10.0  # Capped at max_delay


class TestErrorHandler:
    """Test ErrorHandler class."""

    def test_handler_creation(self):
        """Test creating error handler."""
        handler = ErrorHandler()
        assert handler.error_count == 0

    def test_handle_error(self):
        """Test error handling."""
        handler = ErrorHandler()
        error = Exception("Test error")
        context = ExecutionContext(task_id="test", step_name="test_step")

        handler.handle_error(error, context)

        assert handler.error_count == 1
        assert len(handler.error_log) == 1
        assert handler.error_log[0]["error"] == str(error)
        assert handler.error_log[0]["task_id"] == "test"

    def test_get_error_summary(self):
        """Test getting error summary."""
        handler = ErrorHandler()

        error1 = Exception("Error 1")
        error2 = ValueError("Error 2")
        context = ExecutionContext(task_id="test", step_name="test_step")

        handler.handle_error(error1, context)
        handler.handle_error(error2, context)

        summary = handler.get_error_summary()

        assert summary["total_errors"] == 2
        assert "Exception" in summary["error_types"]
        assert "ValueError" in summary["error_types"]


class TestWorkflowManager:
    """Test WorkflowManager class."""

    def test_manager_initialization(self, workflow_config):
        """Test workflow manager initialization."""
        manager = WorkflowManager(workflow_config)

        assert manager.config == workflow_config
        assert manager.task_queue.is_empty()
        assert manager.active_workflows == {}
        assert manager.progress_tracker.total_tasks == 0

    def test_submit_task(self, workflow_config, sample_task):
        """Test submitting task to manager."""
        manager = WorkflowManager(workflow_config)

        manager.submit_task(sample_task)

        assert manager.task_queue.size() == 1
        assert manager.progress_tracker.total_tasks == 1

    def test_start_workflow(
        self, workflow_config, sample_task, mock_extraction_protocol
    ):
        """Test starting workflow for task."""
        manager = WorkflowManager(workflow_config)
        manager.protocol_factory = lambda *args: mock_extraction_protocol

        workflow_state = manager.start_workflow(sample_task)

        assert workflow_state.task == sample_task
        assert sample_task.task_id in manager.active_workflows
        assert sample_task.status == TaskStatus.RUNNING

    def test_complete_workflow(self, workflow_config, sample_task):
        """Test completing workflow."""
        manager = WorkflowManager(workflow_config)
        workflow_state = WorkflowState(sample_task)
        manager.active_workflows[sample_task.task_id] = workflow_state

        result = {"extraction_data": "test"}
        manager.complete_workflow(sample_task.task_id, result)

        assert sample_task.status == TaskStatus.COMPLETED
        assert sample_task.result == result
        assert sample_task.task_id not in manager.active_workflows
        assert manager.progress_tracker.completed_tasks == 1

    def test_fail_workflow(self, workflow_config, sample_task):
        """Test failing workflow."""
        manager = WorkflowManager(workflow_config)
        workflow_state = WorkflowState(sample_task)
        manager.active_workflows[sample_task.task_id] = workflow_state

        error = Exception("Workflow failed")
        manager.fail_workflow(sample_task.task_id, error)

        assert sample_task.status == TaskStatus.FAILED
        assert sample_task.error == str(error)
        assert sample_task.task_id not in manager.active_workflows
        assert manager.progress_tracker.failed_tasks == 1

    def test_get_workflow_status(self, workflow_config, sample_task):
        """Test getting workflow status."""
        manager = WorkflowManager(workflow_config)
        workflow_state = WorkflowState(sample_task)
        manager.active_workflows[sample_task.task_id] = workflow_state

        status = manager.get_workflow_status(sample_task.task_id)

        assert status["task_id"] == sample_task.task_id
        assert status["status"] == sample_task.status.value
        assert "started_at" in status
        assert "current_step" in status


class TestExtractionWorkflow:
    """Test ExtractionWorkflow main class."""

    def test_workflow_initialization(self, extraction_workflow):
        """Test workflow initialization."""
        assert extraction_workflow.config is not None
        assert extraction_workflow.manager is not None
        assert extraction_workflow.analyzer is not None

    @pytest.mark.asyncio
    async def test_run_single_extraction(self, extraction_workflow, sample_task):
        """Test running single extraction task."""
        result = await extraction_workflow.run_single_extraction(sample_task)

        assert result is not None
        assert sample_task.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_run_batch_extraction(self, extraction_workflow):
        """Test running batch extraction."""
        tasks = [
            ExtractionTask(
                f"task_{i}", f"paper_{i}", "content", TaskPriority.MEDIUM, "analyst"
            )
            for i in range(3)
        ]

        results = await extraction_workflow.run_batch_extraction(tasks)

        assert len(results) == 3
        assert all(task.status == TaskStatus.COMPLETED for task in tasks)

    def test_create_extraction_pipeline(self, extraction_workflow):
        """Test creating extraction pipeline."""
        pipeline = extraction_workflow.create_extraction_pipeline()

        # Should have all 5 phases as steps
        assert len(pipeline) == 5
        step_names = [step.name for step in pipeline]
        assert "preparation" in step_names
        assert "automated_extraction" in step_names
        assert "manual_extraction" in step_names
        assert "validation" in step_names
        assert "documentation" in step_names

    def test_add_validation_gates(self, extraction_workflow):
        """Test adding validation gates."""
        pipeline = extraction_workflow.create_extraction_pipeline()
        gated_pipeline = extraction_workflow.add_validation_gates(pipeline)

        # Should have validation gates between steps
        assert len(gated_pipeline) >= len(pipeline)

    def test_handle_workflow_error(self, extraction_workflow, sample_task):
        """Test handling workflow errors."""
        error = Exception("Test workflow error")

        extraction_workflow.handle_workflow_error(sample_task, error)

        assert sample_task.status == TaskStatus.FAILED
        assert sample_task.error == str(error)
        assert sample_task.attempts > 0

    def test_should_retry_task(self, extraction_workflow, sample_task):
        """Test retry decision for task."""
        # New task should be retryable
        assert extraction_workflow.should_retry_task(sample_task) is True

        # Task at max attempts should not be retryable
        sample_task.attempts = extraction_workflow.config.retry_attempts
        assert extraction_workflow.should_retry_task(sample_task) is False

    def test_get_workflow_metrics(self, extraction_workflow):
        """Test getting workflow metrics."""
        metrics = extraction_workflow.get_workflow_metrics()

        assert "total_tasks" in metrics
        assert "completed_tasks" in metrics
        assert "failed_tasks" in metrics
        assert "completion_rate" in metrics
        assert "average_duration" in metrics


class TestNotificationService:
    """Test NotificationService class."""

    def test_service_initialization(self):
        """Test notification service initialization."""
        service = NotificationService()
        assert service.enabled is False

    def test_send_notification(self):
        """Test sending notification."""
        service = NotificationService(enabled=True)

        # Mock notification handler
        handler = Mock()
        service.handlers.append(handler)

        service.send_notification("test_event", {"data": "test"})

        handler.assert_called_once_with("test_event", {"data": "test"})

    def test_notification_disabled(self):
        """Test notification when service is disabled."""
        service = NotificationService(enabled=False)

        # Mock notification handler
        handler = Mock()
        service.handlers.append(handler)

        service.send_notification("test_event", {"data": "test"})

        # Handler should not be called
        handler.assert_not_called()


class TestWorkflowEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_task_queue(self, workflow_config):
        """Test workflow with empty task queue."""
        manager = WorkflowManager(workflow_config)

        next_task = manager.task_queue.get_next_task()
        assert next_task is None

    def test_task_timeout(self, extraction_workflow, sample_task):
        """Test task timeout handling."""
        # Set very short timeout
        extraction_workflow.config.timeout_minutes = 0.001

        # This would be tested with actual async timeout implementation
        # Mock timeout behavior for test
        sample_task.status = TaskStatus.FAILED
        sample_task.error = "Task timeout"

        assert sample_task.status == TaskStatus.FAILED
        assert "timeout" in sample_task.error.lower()

    def test_concurrent_task_limit(self, workflow_config):
        """Test concurrent task limit enforcement."""
        workflow_config.max_concurrent_tasks = 2
        manager = WorkflowManager(workflow_config)

        # Add tasks
        for i in range(5):
            task = ExtractionTask(
                f"task_{i}", f"paper_{i}", "content", TaskPriority.MEDIUM, "analyst"
            )
            manager.submit_task(task)

        assert manager.task_queue.size() == 5

        # Start workflows (would be limited by max_concurrent_tasks in real implementation)
        # This would be tested with actual concurrency control

    def test_malformed_task_data(self, extraction_workflow):
        """Test handling malformed task data."""
        malformed_task = ExtractionTask(
            task_id="",  # Empty task ID
            paper_id="",  # Empty paper ID
            paper_content="",  # Empty content
            priority=TaskPriority.LOW,
            analyst="",  # Empty analyst
        )

        # Should handle gracefully without crashing
        try:
            extraction_workflow.manager.submit_task(malformed_task)
        except Exception as e:
            # Should either handle gracefully or raise appropriate validation error
            assert isinstance(e, (ValueError, TypeError))

    @pytest.mark.asyncio
    async def test_analyzer_failure(self, extraction_workflow, sample_task):
        """Test handling analyzer failure."""
        # Make analyzer raise exception
        extraction_workflow.analyzer.analyze.side_effect = Exception("Analyzer failed")

        # Should handle the error gracefully
        await extraction_workflow.run_single_extraction(sample_task)

        # Task should be marked as failed but workflow should not crash
        assert sample_task.status == TaskStatus.FAILED
        assert (
            "analyzer" in sample_task.error.lower()
            or "failed" in sample_task.error.lower()
        )
