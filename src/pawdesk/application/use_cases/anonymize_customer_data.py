"""Caso de uso LGPD: exclusão/anonimização de dados da conversa por titular."""

from collections.abc import Callable

from pawdesk.application.ports.outbound.infra import Clock, UnitOfWork
from pawdesk.domain.constants import MessageAuthor
from pawdesk.shared.utils.hashing import pseudonymize
from pawdesk.shared.utils.phone import to_e164


class AnonymizeCustomerData:
    """Anonimiza mensagens, registros cifrados de telefone e trilha vinculada ao titular."""

    def __init__(
        self,
        *,
        uow_factory: Callable[[], UnitOfWork],
        clock: Clock,
        pseudonym_secret: str,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._secret = pseudonym_secret

    async def execute(
        self,
        *,
        phone_e164: str | None = None,
        channel_user_hash: str | None = None,
        correlation_id: str,
    ) -> int:
        if channel_user_hash:
            target_hash = channel_user_hash
        elif phone_e164:
            target_hash = pseudonymize(to_e164(phone_e164), self._secret)
        else:
            raise ValueError("Informe phone_e164 ou channel_user_hash.")

        now = self._clock.now()
        async with self._uow_factory() as uow:
            affected = await uow.conversations.anonymize_by_user_hash(target_hash, now)
            await uow.audit_logs.record(
                conversation_id=f"hash:{target_hash}",
                actor=MessageAuthor.SYSTEM.value,
                action="LGPD_ANONYMIZED",
                tool=None,
                args_redacted={"conversations_affected": affected},
                result_status="DONE",
                correlation_id=correlation_id,
                created_at=now,
            )
        return affected
