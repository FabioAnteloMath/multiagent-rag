import logging
import json
import time
from functools import wraps
from typing import Any


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        return json.dumps(log_data)


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("multiagent_rag")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

    return logger


logger = setup_logging()


def log_request(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        request_id = f"{int(start_time * 1000)}"

        logger.info(
            f"Request started",
            extra={
                "extra_data": {
                    "request_id": request_id,
                    "function": func.__name__,
                }
            },
        )

        try:
            result = func(*args, **kwargs)
            elapsed_ms = (time.time() - start_time) * 1000

            logger.info(
                f"Request completed",
                extra={
                    "extra_data": {
                        "request_id": request_id,
                        "function": func.__name__,
                        "latency_ms": round(elapsed_ms, 2),
                        "success": True,
                    }
                },
            )

            return result
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000

            logger.error(
                f"Request failed: {str(e)}",
                extra={
                    "extra_data": {
                        "request_id": request_id,
                        "function": func.__name__,
                        "latency_ms": round(elapsed_ms, 2),
                        "success": False,
                        "error": str(e),
                    }
                },
            )
            raise

    return wrapper


def log_pipeline_step(step_name: str, metadata: dict[str, Any] | None = None):
    logger.info(
        f"Pipeline step: {step_name}",
        extra={"extra_data": metadata or {}},
    )