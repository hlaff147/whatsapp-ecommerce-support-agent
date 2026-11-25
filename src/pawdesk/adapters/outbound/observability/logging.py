"""Logging estruturado JSON com mascaramento automático de PII."""

import logging
from collections.abc import MutableMapping
from typing import Any

import structlog

from pawdesk.shared.utils.masking import redact_pii


def _redact_event_dict(
    _logger: Any, _method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Processador structlog que mascara PII em qualquer campo textual."""
    for key, value in list(event_dict.items()):
        if isinstance(value, str):
            event_dict[key] = redact_pii(value)
        elif isinstance(value, dict):
            event_dict[key] = {
                k: redact_pii(v) if isinstance(v, str) else v for k, v in value.items()
            }
    return event_dict


def configure_logging(level: str = "INFO") -> None:
    """Configura structlog com saída JSON e redação de PII."""
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, level.upper(), logging.INFO),
    )
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.add_log_level,
            _redact_event_dict,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )
