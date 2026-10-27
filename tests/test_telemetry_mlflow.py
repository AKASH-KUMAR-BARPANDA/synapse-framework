"""Tests for MLflow tracking and telemetry integration in Synapse."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from synapse import BaseApp
from synapse.telemetry import MLflowTracker, get_tracker, track_run


def test_mlflow_tracker_no_op_when_disabled():
    """Verifies that MLflowTracker acts as a safe, clean no-op when disabled or uninstalled."""
    tracker = MLflowTracker(experiment_name="test_exp", enabled=False)
    assert not tracker.is_available()

    # Operations should execute without throwing exceptions
    with tracker.start_run(run_name="test_run"):
        tracker.log_param("test_key", "test_val")
        tracker.log_params({"p1": 1, "p2": 2})
        tracker.log_metric("latency_ms", 12.5)
        tracker.log_metrics({"m1": 1.0, "m2": 2.0})
        tracker.log_artifact("README.md")
        tracker.log_dict({"test": "data"}, "test.json")

    tracker.log_chat_turn(
        message="Hello",
        response="Hi there",
        latency_ms=10.0,
        model="test_model",
    )

    # Test global helpers
    assert get_tracker() is not None
    with track_run("global_run"):
        pass


def test_mlflow_tracker_decorator():
    """Verifies the @tracker.track decorator behavior."""
    tracker = MLflowTracker(experiment_name="test_exp", enabled=False)

    @tracker.track(name="sample_operation")
    def calculate(x: int, y: int) -> int:
        return x + y

    result = calculate(3, 7)
    assert result == 10


def test_base_app_mlflow_initialization():
    """Verifies that BaseApp correctly initializes MLflow tracker attributes."""
    app = BaseApp(
        title="Telemetry Test App",
        mlflow_tracking=False,
        mlflow_experiment="custom_eval",
    )
    assert hasattr(app, "mlflow_tracker")
    assert isinstance(app.mlflow_tracker, MLflowTracker)
    assert app.mlflow_tracker.experiment_name == "custom_eval"


def test_mlflow_tracker_mocked_calls():
    """Verifies that MLflow API methods are invoked when enabled and mocked."""
    with patch("synapse.telemetry.mlflow_tracker.mlflow") as mock_mlflow:
        mock_exp = MagicMock()
        mock_exp.experiment_id = "exp_123"
        mock_mlflow.get_experiment_by_name.return_value = mock_exp

        tracker = MLflowTracker(experiment_name="mocked_exp", enabled=True)
        assert tracker.is_available()

        with tracker.start_run("mocked_run"):
            tracker.log_param("param_a", 42)
            tracker.log_metric("metric_b", 99.5)

        mock_mlflow.set_experiment.assert_called_with("mocked_exp")
        mock_mlflow.log_param.assert_called_with("param_a", 42)
        mock_mlflow.log_metric.assert_called_with("metric_b", 99.5, step=None)
