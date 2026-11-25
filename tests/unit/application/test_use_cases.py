"""Testes unitários dos casos de uso com adaptadores fakes em memória."""

from datetime import UTC, datetime

import pytest
from tests.fakes.fake_clock import FakeClock

from pawdesk.application.dto.agent_io import AgentTurnRequest, AgentTurnResult, TokenUsage
from pawdesk.application.dto.commands import HelpdeskResolutionCommand, IncomingMessage
from pawdesk.application.dto.context import CallerContext
from pawdesk.application.errors import AgentRuntimeError, NotFound, VerificationRequired
from pawdesk.bootstrap.container import Container
from pawdesk.bootstrap.settings import Settings
from pawdesk.domain.constants import ConversationStatus, OutboxStatus, VerificationLevel
from pawdesk.domain.value_objects.address import ZipCode
from pawdesk.domain.value_objects.ids import CustomerId, OrderNumber, Sku
from pawdesk.shared.utils.hashing import pseudonymize


def _settings() -> Settings:
    return Settings(storage_backend="memory", adk_session_backend="memory", channel_mode="console")


async def test_get_order_status_ownership_and_idor() -> None:
    clock = FakeClock()
    wired = Container(_settings()).build_for_dev(clock=clock)
    marina_caller = CallerContext(
        customer_id=CustomerId("CUS_MARINA_001"),
        customer_first_name="Marina",
        level=VerificationLevel.PHONE_MATCH,
        conversation_id="conv-1",
        correlation_id="corr-1",
    )

    from pawdesk.application.use_cases.get_order_status import GetOrderStatus
    from pawdesk.domain.services.delivery_eta_calculator import DeliveryEtaCalculator

    uc = GetOrderStatus(wired.orders, DeliveryEtaCalculator(), clock)
    view = await uc.execute(marina_caller, OrderNumber("PD-104822"))
    assert view.order_number == "PD-104822"
    assert view.delay.is_late is False

    # Tentativa de acessar pedido de outra cliente (Bia) -> NotFound idêntico (RN-02)
    with pytest.raises(NotFound):
        await uc.execute(marina_caller, OrderNumber("PD-104300"))

    # Sem verificação de telefone -> VerificationRequired
    anon = CallerContext(None, None, VerificationLevel.NONE, "conv-1", "corr-1")
    with pytest.raises(VerificationRequired):
        await uc.execute(anon, OrderNumber("PD-104822"))


async def test_estimate_delivery_by_zip() -> None:
    clock = FakeClock()
    wired = Container(_settings()).build_for_dev(clock=clock)
    from pawdesk.adapters.outbound.gateways.carrier_fake import CarrierFakeGateway
    from pawdesk.adapters.outbound.persistence.memory.stores import InMemoryCatalogGateway
    from pawdesk.application.use_cases.estimate_delivery_by_zip import EstimateDeliveryByZip

    assert wired.memory_db is not None
    uc = EstimateDeliveryByZip(
        InMemoryCatalogGateway(wired.memory_db),
        CarrierFakeGateway(wired.shipments),
        clock,
    )
    quote = await uc.execute(ZipCode.parse("01310-100"), Sku("RAC-GAT-10KG"))
    assert quote.business_days == 2
    assert quote.carrier_name == "PetLog Express"
    assert quote.shipping_cost_brl == "R$ 18,90"


async def test_receive_incoming_dedup_burst_and_process_turn() -> None:
    clock = FakeClock(datetime(2026, 11, 24, 15, 0, tzinfo=UTC))  # horário comercial
    settings = _settings()
    wired = Container(settings).build_for_dev(clock=clock)
    phone = "+5511999990001"
    user_hash = pseudonymize(phone, settings.pseudonym_secret)

    class _StubAgentRuntime:
        def __init__(self) -> None:
            self.calls: list[AgentTurnRequest] = []

        async def run_turn(self, request: AgentTurnRequest) -> AgentTurnResult:
            self.calls.append(request)
            return AgentTurnResult(
                reply_text="Oi Marina! Seu pedido PD-104822 saiu para entrega hoje.",
                agent_name="order_agent",
                tools_called=("get_order_status",),
                usage=(TokenUsage(model="fake", input_tokens=100, output_tokens=30),),
            )

    stub_agent = _StubAgentRuntime()
    wired.process_conversation_turn._agent = stub_agent  # type: ignore[attr-defined]

    # Rajada de 2 mensagens + 1 duplicada
    msg1 = IncomingMessage("wamid-1", user_hash, phone, "oi", None, clock.now(), "c1")
    msg1_dup = IncomingMessage("wamid-1", user_hash, phone, "oi", None, clock.now(), "c2")
    msg2 = IncomingMessage(
        "wamid-2", user_hash, phone, "cadê meu pedido PD-104822?", None, clock.now(), "c3"
    )
    assert await wired.receive_incoming_message.execute(msg1) is True
    assert await wired.receive_incoming_message.execute(msg1_dup) is False
    assert await wired.receive_incoming_message.execute(msg2) is True

    await wired.process_conversation_turn.execute(user_hash, "turn-1")
    assert len(stub_agent.calls) == 1
    assert stub_agent.calls[0].text == "oi\ncadê meu pedido PD-104822?"
    assert stub_agent.calls[0].caller.customer_first_name == "Marina"
    assert stub_agent.calls[0].caller.level == VerificationLevel.PHONE_MATCH

    conv = await wired.conversations.get_active_by_user_hash(user_hash)
    assert conv is not None
    outbox = await wired.outbox.list_by_conversation(conv.id)
    assert len(outbox) == 1
    assert await wired.dispatch_outbox_message.execute(outbox[0].id) is True
    assert await wired.outbox.get_status(outbox[0].id) == OutboxStatus.SENT
    # Reenvio idempotente não envia de novo
    assert await wired.dispatch_outbox_message.execute(outbox[0].id) is False


async def test_agent_error_triggers_handoff_silence_and_resume() -> None:
    clock = FakeClock(datetime(2026, 11, 24, 23, 0, tzinfo=UTC))  # 20h BRT (fora comercial)
    settings = _settings()
    wired = Container(settings).build_for_dev(clock=clock)
    phone = "+5511999990003"
    user_hash = pseudonymize(phone, settings.pseudonym_secret)

    class _FailingAgent:
        async def run_turn(self, request: AgentTurnRequest) -> AgentTurnResult:
            _ = request
            raise AgentRuntimeError("boom")

    wired.process_conversation_turn._agent = _FailingAgent()  # type: ignore[attr-defined]

    await wired.receive_incoming_message.execute(
        IncomingMessage("w1", user_hash, phone, "preciso de ajuda", None, clock.now(), "c1")
    )
    await wired.process_conversation_turn.execute(user_hash, "t1")

    conv = await wired.conversations.get_active_by_user_hash(user_hash)
    assert conv is not None
    assert conv.status == ConversationStatus.WITH_HUMAN
    outbox = await wired.outbox.list_by_conversation(conv.id)
    assert "horário comercial" in outbox[0].text

    # Nova mensagem enquanto WITH_HUMAN -> bot silencia e encaminha para o helpdesk
    await wired.receive_incoming_message.execute(
        IncomingMessage("w2", user_hash, phone, "meu cpf 52998224725", None, clock.now(), "c2")
    )
    await wired.process_conversation_turn.execute(user_hash, "t2")
    assert len(await wired.outbox.list_by_conversation(conv.id)) == 1
    assert wired.fake_helpdesk is not None
    tickets = wired.fake_helpdesk.list_tickets()
    assert len(tickets) == 1
    assert len(tickets[0].forwarded_messages) == 1
    assert "52998224725" not in tickets[0].forwarded_messages[0]

    # Helpdesk resolve -> conversa volta para ACTIVE
    await wired.resume_after_handoff.execute(
        HelpdeskResolutionCommand(
            conversation_id=conv.id.value,
            helpdesk_ticket_id=tickets[0].external_ticket_id,
            resolution_note="Resolvido",
            resolved_at=clock.now(),
            correlation_id="c3",
        )
    )
    conv_after = await wired.conversations.get_by_id(conv.id)
    assert conv_after is not None
    assert conv_after.status == ConversationStatus.ACTIVE


async def test_lgpd_anonymize_customer_data() -> None:
    clock = FakeClock()
    settings = _settings()
    wired = Container(settings).build_for_dev(clock=clock)
    phone = "+5511999990001"
    user_hash = pseudonymize(phone, settings.pseudonym_secret)

    await wired.receive_incoming_message.execute(
        IncomingMessage("w-lgpd", user_hash, phone, "oi", None, clock.now(), "c1")
    )
    affected = await wired.anonymize_customer_data.execute(
        phone_e164=phone, correlation_id="lgpd-1"
    )
    assert affected == 1
    conv = await wired.conversations.get_active_by_user_hash(user_hash)
    assert conv is None  # fechada após anonimização
    assert wired.memory_db is not None
    stored_conv = next(iter(wired.memory_db.conversations.values()))
    assert stored_conv.channel_user_phone == "[ANONIMIZADO]"
    assert wired.memory_db.messages[0].content_redacted == "[ANONIMIZADO LGPD]"
