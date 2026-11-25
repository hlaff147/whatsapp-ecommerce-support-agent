"""Decorator de guarda para tools: timeout, tradução de erros e contagem de falhas."""

import asyncio
import functools
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from pawdesk.adapters.agentic.constants import StateKey
from pawdesk.adapters.agentic.tools._result import ToolResult
from pawdesk.application.constants import ErrorCode
from pawdesk.application.errors import (
    ExternalServiceUnavailable,
    NotFound,
    VerificationBlocked,
    VerificationRequired,
)
from pawdesk.domain.errors import DomainError
from pawdesk.shared.constants.limits import TOOL_TIMEOUT_S

log = logging.getLogger(__name__)


def guarded_tool(
    fn: Callable[..., Awaitable[dict[str, object]]],
) -> Callable[..., Awaitable[dict[str, object]]]:
    """Preserva assinatura e docstring para o ADK enquanto aplica timeout e captura exceções."""

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> dict[str, object]:
        tool_context = kwargs.get("tool_context")
        try:
            return await asyncio.wait_for(fn(*args, **kwargs), timeout=TOOL_TIMEOUT_S)
        except VerificationRequired:
            return ToolResult.fail(
                ErrorCode.VERIFICATION_REQUIRED,
                "Verificação de identidade necessária para acessar essa informação.",
            )
        except VerificationBlocked as exc:
            return ToolResult.fail(ErrorCode.VERIFICATION_BLOCKED, str(exc))
        except NotFound:
            return ToolResult.fail(
                ErrorCode.NOT_FOUND,
                "Não encontrei esse registro para este cliente.",
            )
        except DomainError as exc:
            return ToolResult.fail(ErrorCode.BUSINESS_RULE, exc.user_message)
        except (TimeoutError, ExternalServiceUnavailable):
            _bump_errors(tool_context)
            return ToolResult.fail(
                ErrorCode.SERVICE_UNAVAILABLE,
                "O sistema está indisponível no momento.",
            )
        except Exception:
            log.exception("tool_failed", extra={"tool": fn.__name__})
            _bump_errors(tool_context)
            return ToolResult.fail(
                ErrorCode.INTERNAL,
                "Não consegui concluir essa consulta agora.",
            )

    return wrapper


def _bump_errors(tool_context: Any) -> None:
    if tool_context is not None:
        state = tool_context.state
        state[StateKey.TOOL_ERROR_COUNT.value] = (
            int(state.get(StateKey.TOOL_ERROR_COUNT.value, 0)) + 1
        )
