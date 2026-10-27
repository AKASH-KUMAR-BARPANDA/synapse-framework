"""MLflow experiment tracking, RAG telemetry, and evaluation for Synapse."""

from __future__ import annotations

import functools
import json
import logging
import os
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger("synapse.telemetry")

try:
    import mlflow
except ImportError:
    mlflow = None  # type: ignore


class MLflowTracker:
    """Manages MLflow experiment tracking, runs, metrics, and artifact logging for Synapse.

    Automatically tracks model parameters, Hybrid RAG context metrics, tool execution
    latencies, and knowledge graph artifacts.

    Example:
        ```python
        from synapse.telemetry import MLflowTracker

        tracker = MLflowTracker(experiment_name="support_bot")
        with tracker.start_run(run_name="query_eval"):
            tracker.log_params({"model": "qwen2.5:0.5b", "top_k": 3})
            tracker.log_metrics({"latency_ms": 142.5, "chunks_retrieved": 3})
        ```
    """

    def __init__(
        self,
        experiment_name: str = "synapse_experiments",
        tracking_uri: str | None = None,
        enabled: bool = True,
    ) -> None:
        """Initializes the MLflow tracker.

        Args:
            experiment_name: MLflow experiment name. Defaults to 'synapse_experiments'.
            tracking_uri: Optional MLflow server URI (e.g. 'http://localhost:5000' or 'sqlite:///mlflow.db').
                Reads MLFLOW_TRACKING_URI env var if omitted.
            enabled: Whether tracking is active. If False, operations are safe no-ops.
        """
        self.experiment_name = experiment_name
        self.tracking_uri = tracking_uri or os.getenv("MLFLOW_TRACKING_URI")
        self.enabled = enabled and (mlflow is not None)
        self._experiment_id: str | None = None

        if enabled and mlflow is None:
            logger.warning(
                "MLflow tracking was requested, but 'mlflow' is not installed. "
                "Install it with: pip install 'synapse-framework[mlflow]' or pip install mlflow"
            )

        if self.enabled and mlflow is not None:
            if self.tracking_uri:
                mlflow.set_tracking_uri(self.tracking_uri)
            try:
                exp = mlflow.get_experiment_by_name(self.experiment_name)
                if exp is None:
                    self._experiment_id = mlflow.create_experiment(self.experiment_name)
                else:
                    self._experiment_id = exp.experiment_id
                mlflow.set_experiment(self.experiment_name)
            except Exception as e:
                logger.warning(f"Could not initialize MLflow experiment '{self.experiment_name}': {e}")
                self.enabled = False

    def is_available(self) -> bool:
        """Returns True if the MLflow library is installed and tracker is enabled."""
        return self.enabled and (mlflow is not None)

    def start_run(
        self,
        run_name: str | None = None,
        tags: dict[str, Any] | None = None,
        nested: bool = True,
    ) -> Any:
        """Starts an MLflow run context manager."""
        if not self.enabled or mlflow is None:
            return _NoOpContextManager()

        merged_tags = {"framework": "synapse"}
        if tags:
            merged_tags.update({str(k): str(v) for k, v in tags.items()})

        return mlflow.start_run(
            run_name=run_name,
            experiment_id=self._experiment_id,
            tags=merged_tags,
            nested=nested,
        )

    def log_param(self, key: str, value: Any) -> None:
        """Logs a single parameter to the active MLflow run."""
        if not self.enabled or mlflow is None:
            return
        try:
            mlflow.log_param(key, value)
        except Exception as e:
            logger.debug(f"Failed to log parameter '{key}': {e}")

    def log_params(self, params: dict[str, Any]) -> None:
        """Logs multiple parameters to the active MLflow run."""
        if not self.enabled or mlflow is None:
            return
        try:
            mlflow.log_params(params)
        except Exception as e:
            logger.debug(f"Failed to log parameters: {e}")

    def log_metric(self, key: str, value: float, step: int | None = None) -> None:
        """Logs a numeric metric to the active MLflow run."""
        if not self.enabled or mlflow is None:
            return
        try:
            mlflow.log_metric(key, float(value), step=step)
        except Exception as e:
            logger.debug(f"Failed to log metric '{key}': {e}")

    def log_metrics(self, metrics: dict[str, float], step: int | None = None) -> None:
        """Logs multiple metrics to the active MLflow run."""
        if not self.enabled or mlflow is None:
            return
        try:
            clean_metrics = {k: float(v) for k, v in metrics.items()}
            mlflow.log_metrics(clean_metrics, step=step)
        except Exception as e:
            logger.debug(f"Failed to log metrics: {e}")

    def log_artifact(self, local_path: str | Path, artifact_path: str | None = None) -> None:
        """Uploads a local file or directory as an artifact."""
        if not self.enabled or mlflow is None:
            return
        try:
            mlflow.log_artifact(str(local_path), artifact_path=artifact_path)
        except Exception as e:
            logger.debug(f"Failed to log artifact '{local_path}': {e}")

    def log_dict(self, data: dict[str, Any], artifact_file: str) -> None:
        """Logs a Python dictionary as a JSON artifact."""
        if not self.enabled or mlflow is None:
            return
        try:
            if hasattr(mlflow, "log_dict"):
                mlflow.log_dict(data, artifact_file)
                return

            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
                json.dump(data, f, indent=2)
                tmp_path = Path(f.name)
            try:
                mlflow.log_artifact(str(tmp_path), artifact_path=Path(artifact_file).parent.as_posix() if "/" in artifact_file else None)
            finally:
                tmp_path.unlink(missing_ok=True)
        except Exception as e:
            logger.debug(f"Failed to log dict artifact: {e}")

    def log_chat_turn(
        self,
        message: str,
        response: str,
        latency_ms: float,
        model: str,
        chunks_retrieved: int = 0,
        graph_triples: int = 0,
        tools_executed: list[dict[str, Any]] | None = None,
        session_id: str | None = None,
    ) -> None:
        """Records a complete conversation turn with RAG retrieval metrics into MLflow."""
        if not self.enabled or mlflow is None:
            return

        run_name = f"chat_{session_id or 'turn'}_{int(time.time())}"
        with self.start_run(run_name=run_name, tags={"session_id": session_id or "default"}):
            self.log_params({
                "model": model,
                "user_message_length": len(message),
                "response_length": len(response),
            })
            self.log_metrics({
                "latency_ms": latency_ms,
                "chunks_retrieved": chunks_retrieved,
                "graph_triples_retrieved": graph_triples,
                "tools_executed_count": len(tools_executed or []),
            })

            # Save query trace JSON
            self.log_dict({
                "user_message": message,
                "assistant_response": response,
                "chunks_retrieved_count": chunks_retrieved,
                "graph_triples_count": graph_triples,
                "tools_executed": tools_executed or [],
                "latency_ms": latency_ms,
            }, "chat_turn.json")

    def track(self, name: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator to measure and log function execution time and outcomes to MLflow."""
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                run_title = name or func.__name__
                t0 = time.perf_counter()
                success = True
                error_str = None
                with self.start_run(run_name=run_title):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        success = False
                        error_str = str(e)
                        raise
                    finally:
                        t1 = time.perf_counter()
                        latency_ms = (t1 - t0) * 1000.0
                        self.log_metrics({"execution_ms": latency_ms, "success": 1.0 if success else 0.0})
                        if error_str:
                            self.log_param("error", error_str)
            return wrapper
        return decorator


class _NoOpContextManager:
    """Safe no-op context manager when MLflow is disabled or not installed."""

    def __enter__(self) -> _NoOpContextManager:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass


# Global singleton tracker instance
_default_tracker: MLflowTracker | None = None


def get_tracker(experiment_name: str = "synapse_experiments", tracking_uri: str | None = None) -> MLflowTracker:
    """Returns or creates the default MLflowTracker singleton."""
    global _default_tracker
    if _default_tracker is None:
        _default_tracker = MLflowTracker(experiment_name=experiment_name, tracking_uri=tracking_uri)
    return _default_tracker


def track_run(run_name: str | None = None, tags: dict[str, Any] | None = None) -> Any:
    """Convenience context manager to start an MLflow run using the default tracker."""
    tracker = get_tracker()
    return tracker.start_run(run_name=run_name, tags=tags)
