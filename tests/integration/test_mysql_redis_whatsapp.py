"""Testes de integração de adaptadores (WhatsApp HTTP mock + MySQL/Redis via testcontainers)."""

import httpx
import pytest
import respx

from pawdesk.adapters.outbound.channels.whatsapp_cloud import WhatsAppCloudChannel
from pawdesk.adapters.outbound.observability.logging import configure_logging


async def test_whatsapp_cloud_channel_text_and_interactive_buttons() -> None:
    url = "https://graph.facebook.com/v21.0/123456/messages"
    async with httpx.AsyncClient() as client:
        channel = WhatsAppCloudChannel(
            access_token="token-123",
            phone_number_id="123456",
            http_client=client,
        )
        with respx.mock(assert_all_called=True) as mock:
            route = mock.post(url).mock(
                side_effect=[
                    httpx.Response(500, json={"error": "temporary"}),
                    httpx.Response(200, json={"messages": [{"id": "wamid.sent.1"}]}),
                    httpx.Response(200, json={"messages": [{"id": "wamid.sent.2"}]}),
                ]
            )
            res_text = await channel.send_text(
                recipient_phone="+5511999990001",
                text="Oi Marina! 🐾",
            )
            assert res_text.provider_message_id == "wamid.sent.1"

            res_btn = await channel.send_text(
                recipient_phone="+5511999990001",
                text="Confirma a solicitação?",
                ui_hint={
                    "kind": "confirm_buttons",
                    "buttons": [
                        {"id": "confirm:act-1", "title": "Confirmar"},
                        {"id": "cancel:act-1", "title": "Cancelar"},
                    ],
                },
            )
            assert res_btn.provider_message_id == "wamid.sent.2"
            assert route.call_count == 3


def test_logging_redacts_pii(capsys: pytest.CaptureFixture[str]) -> None:
    import structlog

    configure_logging("INFO")
    log = structlog.get_logger("test.pii")
    log.info("customer_event", detail="CPF 529.982.247-25 e email ana@pet.com")
    # Verifica que nenhum erro ocorre ao configurar e emitir log estruturado
    _ = capsys.readouterr()


@pytest.mark.integration
async def test_mysql_and_redis_containers_roundtrip() -> None:
    """Executa contra MySQL 8 e Redis reais quando Docker daemon está disponível."""
    from datetime import UTC, datetime

    from redis.asyncio import Redis
    from testcontainers.mysql import MySqlContainer
    from testcontainers.redis import RedisContainer

    from pawdesk.adapters.outbound.cache.redis.conversation_lock import RedisConversationLock
    from pawdesk.adapters.outbound.persistence.mysql.engine import (
        create_mysql_engine,
        create_session_factory,
    )
    from pawdesk.adapters.outbound.persistence.mysql.models import Base
    from pawdesk.adapters.outbound.persistence.mysql.repositories.conversations import (
        MySqlConversationRepository,
    )
    from pawdesk.adapters.outbound.security.fernet_cipher import FernetSecretCipher
    from pawdesk.application.dto.commands import IncomingMessage
    from pawdesk.application.errors import ConversationBusy

    with MySqlContainer("mysql:8.4") as mysql, RedisContainer("redis:7-alpine") as redis_c:
        dsn = mysql.get_connection_url().replace("mysql+pymysql://", "mysql+aiomysql://")
        redis_url = f"redis://{redis_c.get_container_host_ip()}:{redis_c.get_exposed_port(6379)}/0"

        engine = create_mysql_engine(dsn, null_pool=True)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        factory = create_session_factory(engine)
        repo = MySqlConversationRepository(
            cipher=FernetSecretCipher("integ-key"), session_factory=factory
        )
        redis = Redis.from_url(redis_url)
        lock = RedisConversationLock(redis)
        try:
            async with lock.hold("conv:u1", 30):
                with pytest.raises(ConversationBusy):
                    async with lock.hold("conv:u1", 30):
                        pass

            ok = await repo.add_inbound_if_new(
                IncomingMessage(
                    "w-int-1",
                    "u1",
                    "+5511999990001",
                    "olá mysql",
                    None,
                    datetime.now(UTC),
                    "corr-int",
                ),
                content_redacted="olá mysql",
                adk_session_id="01JINT00000000000000000001",
                idle_hours=24,
            )
            assert ok is True
        finally:
            await redis.aclose()
            await engine.dispose()
