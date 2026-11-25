"""Gateway de helpdesk em memória/log para ambiente local e portfólio."""

from dataclasses import dataclass, field
from threading import Lock

import structlog

from pawdesk.application.dto.results import HandoffPackage
from pawdesk.application.ports.outbound.gateways import HelpdeskTicketCreated
from pawdesk.shared.utils.ids import new_ulid

log = structlog.get_logger("pawdesk.helpdesk.fake")


@dataclass
class FakeHelpdeskEntry:
    external_ticket_id: str
    package: HandoffPackage
    forwarded_messages: list[str] = field(default_factory=list)


class FakeHelpdeskGateway:
    """Simula integração com painel de helpdesk mantendo tickets em memória."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._tickets: dict[str, FakeHelpdeskEntry] = {}

    async def create_ticket(self, package: HandoffPackage) -> HelpdeskTicketCreated:
        ext_id = f"HD-{new_ulid()[:10]}"
        with self._lock:
            self._tickets[ext_id] = FakeHelpdeskEntry(external_ticket_id=ext_id, package=package)
        log.info(
            "helpdesk_ticket_created",
            external_ticket_id=ext_id,
            conversation_id=package.conversation_id,
            reason=package.reason.value,
            priority=package.priority.value,
        )
        return HelpdeskTicketCreated(external_ticket_id=ext_id)

    async def forward_message(
        self,
        *,
        conversation_id: str,
        external_ticket_id: str | None,
        text_redacted: str,
    ) -> None:
        with self._lock:
            if external_ticket_id and external_ticket_id in self._tickets:
                self._tickets[external_ticket_id].forwarded_messages.append(text_redacted)
        log.info(
            "helpdesk_message_forwarded",
            conversation_id=conversation_id,
            external_ticket_id=external_ticket_id,
        )

    def list_tickets(self) -> list[FakeHelpdeskEntry]:
        with self._lock:
            return list(self._tickets.values())
