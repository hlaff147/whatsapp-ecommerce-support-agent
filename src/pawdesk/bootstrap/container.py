"""Composition root: conecta portas da aplicação aos adaptadores concretos."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass

from google.adk.agents import LlmAgent
from google.adk.models.base_llm import BaseLlm
from google.adk.sessions import BaseSessionService
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from pawdesk.adapters.agentic.agents.case_summarizer import build_case_summarizer_agent
from pawdesk.adapters.agentic.agents.factory import build_agent_tree
from pawdesk.adapters.agentic.agents.guards import GuardCallbacks
from pawdesk.adapters.agentic.callbacks.input_guard import make_before_model_callback
from pawdesk.adapters.agentic.callbacks.output_guard import make_after_model_callback
from pawdesk.adapters.agentic.callbacks.tool_audit import make_after_tool_callback
from pawdesk.adapters.agentic.callbacks.tool_authz import make_before_tool_callback
from pawdesk.adapters.agentic.constants import ADK_APP_NAME, AgentName, ModelRole, ToolName
from pawdesk.adapters.agentic.model_factory import ModelFactory
from pawdesk.adapters.agentic.runtime import AdkAgentRuntime
from pawdesk.adapters.agentic.session_factory import make_session_service
from pawdesk.adapters.agentic.summarizer import AdkCaseSummarizer
from pawdesk.adapters.agentic.tools.control_tools import build_control_tools
from pawdesk.adapters.agentic.tools.identity_tools import build_identity_tools
from pawdesk.adapters.agentic.tools.order_tools import build_order_tools
from pawdesk.adapters.agentic.tools.registry import ToolRegistry, ToolSpec
from pawdesk.adapters.inbound.http.deps import HttpDependencies
from pawdesk.adapters.outbound.cache.redis.conversation_lock import RedisConversationLock
from pawdesk.adapters.outbound.cache.redis.rate_limiter import RedisRateLimiter
from pawdesk.adapters.outbound.channels.console_channel import ConsoleChannel
from pawdesk.adapters.outbound.channels.whatsapp_cloud import WhatsAppCloudChannel
from pawdesk.adapters.outbound.clock import SystemClock
from pawdesk.adapters.outbound.gateways.carrier_fake import CarrierFakeGateway
from pawdesk.adapters.outbound.gateways.catalog_mysql import MySqlCatalogGateway
from pawdesk.adapters.outbound.gateways.helpdesk_fake import FakeHelpdeskGateway
from pawdesk.adapters.outbound.gateways.helpdesk_http import HttpHelpdeskGateway
from pawdesk.adapters.outbound.observability.metrics import InMemoryTelemetry
from pawdesk.adapters.outbound.persistence.memory.infra import (
    InMemoryConversationLock,
    InMemoryRateLimiter,
    RecordingTurnScheduler,
)
from pawdesk.adapters.outbound.persistence.memory.stores import (
    InMemoryCatalogGateway,
    InMemoryConversationRepository,
    InMemoryCustomerRepository,
    InMemoryHandoffRepository,
    InMemoryOrderRepository,
    InMemoryOutboxRepository,
    InMemoryShipmentRepository,
    InMemoryUnitOfWork,
    MemoryDatabase,
)
from pawdesk.adapters.outbound.persistence.mysql.engine import (
    create_mysql_engine,
    create_session_factory,
)
from pawdesk.adapters.outbound.persistence.mysql.repositories.conversations import (
    MySqlConversationRepository,
)
from pawdesk.adapters.outbound.persistence.mysql.repositories.customers import (
    MySqlCustomerRepository,
)
from pawdesk.adapters.outbound.persistence.mysql.repositories.handoffs import (
    MySqlHandoffRepository,
)
from pawdesk.adapters.outbound.persistence.mysql.repositories.orders import MySqlOrderRepository
from pawdesk.adapters.outbound.persistence.mysql.repositories.outbox import MySqlOutboxRepository
from pawdesk.adapters.outbound.persistence.mysql.repositories.shipments import (
    MySqlShipmentRepository,
)
from pawdesk.adapters.outbound.persistence.mysql.uow import MySqlUnitOfWork
from pawdesk.adapters.outbound.queue.celery_turn_scheduler import CeleryTurnScheduler
from pawdesk.adapters.outbound.security.fernet_cipher import FernetSecretCipher
from pawdesk.application.messages import Messages
from pawdesk.application.ports.outbound.channel import MessageChannel
from pawdesk.application.ports.outbound.gateways import (
    CarrierGateway,
    CatalogGateway,
    HelpdeskGateway,
)
from pawdesk.application.ports.outbound.infra import (
    Clock,
    ConversationLock,
    RateLimiter,
    TurnScheduler,
    UnitOfWork,
)
from pawdesk.application.ports.outbound.repositories import (
    ConversationRepository,
    CustomerRepository,
    HandoffRepository,
    OrderRepository,
    OutboxRepository,
    ShipmentRepository,
)
from pawdesk.application.services.conversation_service import ConversationService
from pawdesk.application.services.cost_service import CostService
from pawdesk.application.services.handoff_service import HandoffService
from pawdesk.application.services.identity_service import IdentityService
from pawdesk.application.services.pii_redaction_service import PiiRedactionService
from pawdesk.application.use_cases.anonymize_customer_data import AnonymizeCustomerData
from pawdesk.application.use_cases.dispatch_outbox_message import DispatchOutboxMessage
from pawdesk.application.use_cases.estimate_delivery_by_zip import EstimateDeliveryByZip
from pawdesk.application.use_cases.get_order_status import GetOrderStatus
from pawdesk.application.use_cases.list_customer_orders import ListCustomerOrders
from pawdesk.application.use_cases.process_conversation_turn import ProcessConversationTurn
from pawdesk.application.use_cases.receive_incoming_message import ReceiveIncomingMessage
from pawdesk.application.use_cases.resume_after_handoff import ResumeAfterHandoff
from pawdesk.application.use_cases.start_human_handoff import StartHumanHandoff
from pawdesk.application.use_cases.track_shipment import TrackShipment
from pawdesk.application.use_cases.verify_customer_identity import VerifyCustomerIdentity
from pawdesk.bootstrap.seed_data import build_seed_dataset
from pawdesk.bootstrap.settings import Settings
from pawdesk.domain.constants import VerificationLevel
from pawdesk.domain.services.content_policy import ContentPolicy
from pawdesk.domain.services.delivery_eta_calculator import DeliveryEtaCalculator
from pawdesk.domain.services.handoff_policy import HandoffPolicy
from pawdesk.domain.services.identity_verification_policy import IdentityVerificationPolicy
from pawdesk.shared.constants.limits import (
    DEBOUNCE_WINDOW_MS,
    MAX_FALLBACKS_BEFORE_HANDOFF,
    MAX_TOOL_ERRORS_BEFORE_HANDOFF,
    MAX_VERIFICATION_ATTEMPTS,
    SESSION_IDLE_CLOSE_HOURS,
    VERIFICATION_LOCK_MINUTES,
)


@dataclass
class WiredApp:
    settings: Settings
    clock: Clock
    customers: CustomerRepository
    orders: OrderRepository
    shipments: ShipmentRepository
    conversations: ConversationRepository
    outbox: OutboxRepository
    handoffs: HandoffRepository
    scheduler: TurnScheduler
    channel: MessageChannel
    helpdesk: HelpdeskGateway
    telemetry: InMemoryTelemetry
    conversation_service: ConversationService
    receive_incoming_message: ReceiveIncomingMessage
    process_conversation_turn: ProcessConversationTurn
    dispatch_outbox_message: DispatchOutboxMessage
    start_human_handoff: StartHumanHandoff
    resume_after_handoff: ResumeAfterHandoff
    anonymize_customer_data: AnonymizeCustomerData
    root_agent: LlmAgent
    health_check: Callable[[], Awaitable[dict[str, bool]]]
    console_channel: ConsoleChannel | None = None
    fake_helpdesk: FakeHelpdeskGateway | None = None
    memory_db: MemoryDatabase | None = None

    def http_dependencies(self) -> HttpDependencies:
        inbox_reader = None
        if self.console_channel is not None:
            console = self.console_channel

            def _read_inbox(phone: str) -> list[dict[str, object]]:
                return [
                    {
                        "provider_message_id": m.provider_message_id,
                        "text": m.text,
                        "ui_hint": m.ui_hint,
                    }
                    for m in console.messages_for(phone)
                ]

            inbox_reader = _read_inbox

        tickets_reader = None
        if self.fake_helpdesk is not None:
            hd = self.fake_helpdesk

            def _read_tickets() -> list[dict[str, object]]:
                return [
                    {
                        "external_ticket_id": entry.external_ticket_id,
                        "conversation_id": entry.package.conversation_id,
                        "reason": entry.package.reason.value,
                        "priority": entry.package.priority.value,
                        "urgent": entry.package.urgent,
                        "summary": entry.package.summary,
                        "forwarded_messages": list(entry.forwarded_messages),
                    }
                    for entry in hd.list_tickets()
                ]

            tickets_reader = _read_tickets

        return HttpDependencies(
            receive_incoming_message=self.receive_incoming_message,
            process_conversation_turn=self.process_conversation_turn,
            dispatch_outbox_message=self.dispatch_outbox_message,
            resume_after_handoff=self.resume_after_handoff,
            anonymize_customer_data=self.anonymize_customer_data,
            conversations=self.conversations,
            outbox=self.outbox,
            handoffs=self.handoffs,
            telemetry=self.telemetry,
            health_check=self.health_check,
            whatsapp_verify_token=self.settings.whatsapp_verify_token,
            whatsapp_app_secret=self.settings.whatsapp_app_secret,
            admin_api_token=self.settings.admin_api_token,
            helpdesk_webhook_secret=self.settings.helpdesk_webhook_secret,
            pseudonym_secret=self.settings.pseudonym_secret,
            enable_simulator=self.settings.enable_simulator,
            simulator_inbox_reader=inbox_reader,
            simulator_tickets_reader=tickets_reader,
        )


class Container:
    """Composition root para criação de grafos de dependências em prod, dev ou teste."""

    def __init__(
        self,
        settings: Settings,
        *,
        model_overrides: dict[ModelRole, BaseLlm] | None = None,
        telemetry: InMemoryTelemetry | None = None,
    ) -> None:
        self._s = settings
        self._model_overrides = model_overrides
        self._telemetry = telemetry or InMemoryTelemetry()

    def build_wired_from_parts(
        self,
        *,
        clock: Clock,
        customers: CustomerRepository,
        orders: OrderRepository,
        shipments: ShipmentRepository,
        conversations: ConversationRepository,
        outbox: OutboxRepository,
        handoffs: HandoffRepository,
        catalog: CatalogGateway,
        uow_factory: Callable[[], UnitOfWork],
        lock: ConversationLock,
        scheduler: TurnScheduler,
        rate_limiter: RateLimiter,
        channel: MessageChannel,
        helpdesk: HelpdeskGateway,
        session_service: BaseSessionService,
        health_check: Callable[[], Awaitable[dict[str, bool]]],
        console_channel: ConsoleChannel | None = None,
        fake_helpdesk: FakeHelpdeskGateway | None = None,
        memory_db: MemoryDatabase | None = None,
    ) -> WiredApp:
        messages = Messages()
        redaction = PiiRedactionService()
        cost_service = CostService()

        eta_calc = DeliveryEtaCalculator(self._s.late_order_handoff_business_days)
        verif_policy = IdentityVerificationPolicy(
            max_attempts=MAX_VERIFICATION_ATTEMPTS,
            lock_minutes=VERIFICATION_LOCK_MINUTES,
        )
        handoff_policy = HandoffPolicy(
            max_fallbacks=MAX_FALLBACKS_BEFORE_HANDOFF,
            max_tool_errors=MAX_TOOL_ERRORS_BEFORE_HANDOFF,
            max_verif_attempts=MAX_VERIFICATION_ATTEMPTS,
        )
        content_policy = ContentPolicy()

        carrier: CarrierGateway = CarrierFakeGateway(shipments)

        identity_service = IdentityService(
            customers=customers,
            orders=orders,
            conversations=conversations,
            policy=verif_policy,
            clock=clock,
        )
        conversation_service = ConversationService(
            conversations=conversations,
            clock=clock,
            idle_close_hours=SESSION_IDLE_CLOSE_HOURS,
        )

        # Use cases de leitura e identidade (usados pelas tools)
        list_orders_uc = ListCustomerOrders(orders)
        get_order_status_uc = GetOrderStatus(orders, eta_calc, clock)
        track_shipment_uc = TrackShipment(orders, carrier, eta_calc, clock)
        estimate_delivery_uc = EstimateDeliveryByZip(catalog, carrier, clock)
        verify_identity_uc = VerifyCustomerIdentity(identity_service)

        order_tools = build_order_tools(
            list_orders_uc=list_orders_uc,
            get_order_status_uc=get_order_status_uc,
            track_shipment_uc=track_shipment_uc,
            estimate_delivery_uc=estimate_delivery_uc,
        )
        identity_tools = build_identity_tools(verify_identity_uc=verify_identity_uc)
        control_tools = build_control_tools()

        registry = ToolRegistry(
            [
                ToolSpec(
                    name=ToolName.VERIFY_IDENTITY,
                    fn=identity_tools["verify_customer_identity"],
                    min_level=VerificationLevel.NONE,
                    agents=(AgentName.IDENTITY,),
                ),
                ToolSpec(
                    name=ToolName.GET_MY_ORDERS,
                    fn=order_tools["get_my_orders"],
                    min_level=VerificationLevel.PHONE_MATCH,
                    agents=(AgentName.ORDER,),
                ),
                ToolSpec(
                    name=ToolName.GET_ORDER_STATUS,
                    fn=order_tools["get_order_status"],
                    min_level=VerificationLevel.PHONE_MATCH,
                    agents=(AgentName.ORDER,),
                ),
                ToolSpec(
                    name=ToolName.TRACK_SHIPMENT,
                    fn=order_tools["track_shipment"],
                    min_level=VerificationLevel.PHONE_MATCH,
                    agents=(AgentName.ORDER,),
                ),
                ToolSpec(
                    name=ToolName.ESTIMATE_DELIVERY_BY_ZIP,
                    fn=order_tools["estimate_delivery_by_zip"],
                    min_level=VerificationLevel.NONE,
                    agents=(AgentName.ORDER,),
                ),
                ToolSpec(
                    name=ToolName.REQUEST_HANDOFF,
                    fn=control_tools["request_human_handoff"],
                    min_level=VerificationLevel.NONE,
                    agents=(AgentName.CONCIERGE, AgentName.ORDER, AgentName.IDENTITY),
                ),
            ]
        )

        guards = GuardCallbacks(
            before_model=make_before_model_callback(
                content_policy=content_policy,
                messages=messages,
                telemetry=self._telemetry,
                vet_channel_available=self._s.vet_channel_available,
            ),
            after_model=make_after_model_callback(
                content_policy=content_policy,
                messages=messages,
                telemetry=self._telemetry,
            ),
            before_tool=make_before_tool_callback(registry),
            after_tool=make_after_tool_callback(redaction),
        )

        models = ModelFactory(
            model_router=self._s.model_router,
            model_specialist=self._s.model_specialist,
            model_judge=self._s.model_judge,
            overrides=self._model_overrides,
        )
        root_agent = build_agent_tree(models, registry, guards)
        summarizer_agent = build_case_summarizer_agent(models)

        case_summarizer = AdkCaseSummarizer(summarizer_agent)
        agent_runtime = AdkAgentRuntime(
            root_agent=root_agent,
            session_service=session_service,
            app_name=ADK_APP_NAME,
            default_model_name=models.model_name(ModelRole.ROUTER),
        )

        handoff_service = HandoffService(
            summarizer=case_summarizer,
            helpdesk=helpdesk,
            redaction=redaction,
            clock=clock,
            messages=messages,
        )

        receive_uc = ReceiveIncomingMessage(
            conversations=conversations,
            scheduler=scheduler,
            redaction=redaction,
            rate_limiter=rate_limiter,
            debounce_window_ms=DEBOUNCE_WINDOW_MS,
            idle_hours=SESSION_IDLE_CLOSE_HOURS,
        )
        process_turn_uc = ProcessConversationTurn(
            lock=lock,
            conversations=conversations,
            uow_factory=uow_factory,
            identity=identity_service,
            agent=agent_runtime,
            handoff=handoff_service,
            scheduler=scheduler,
            telemetry=self._telemetry,
            cost_calculator=cost_service,
            handoff_policy=handoff_policy,
            clock=clock,
            messages=messages,
            vet_channel_available=self._s.vet_channel_available,
        )
        dispatch_uc = DispatchOutboxMessage(
            uow_factory=uow_factory,
            channel=channel,
            clock=clock,
            telemetry=self._telemetry,
        )
        start_handoff_uc = StartHumanHandoff(
            uow_factory=uow_factory,
            handoff=handoff_service,
            scheduler=scheduler,
            clock=clock,
            messages=messages,
        )
        resume_uc = ResumeAfterHandoff(
            uow_factory=uow_factory,
            handoff=handoff_service,
            scheduler=scheduler,
        )
        anonymize_uc = AnonymizeCustomerData(
            uow_factory=uow_factory,
            clock=clock,
            pseudonym_secret=self._s.pseudonym_secret,
        )

        return WiredApp(
            settings=self._s,
            clock=clock,
            customers=customers,
            orders=orders,
            shipments=shipments,
            conversations=conversations,
            outbox=outbox,
            handoffs=handoffs,
            scheduler=scheduler,
            channel=channel,
            helpdesk=helpdesk,
            telemetry=self._telemetry,
            conversation_service=conversation_service,
            receive_incoming_message=receive_uc,
            process_conversation_turn=process_turn_uc,
            dispatch_outbox_message=dispatch_uc,
            start_human_handoff=start_handoff_uc,
            resume_after_handoff=resume_uc,
            anonymize_customer_data=anonymize_uc,
            root_agent=root_agent,
            health_check=health_check,
            console_channel=console_channel,
            fake_helpdesk=fake_helpdesk,
            memory_db=memory_db,
        )

    def build_for_dev(self, *, clock: Clock | None = None) -> WiredApp:
        """Constrói instância completa em memória (sem MySQL/Redis) para dev, adk web e E2E."""
        effective_clock = clock or SystemClock()
        db = MemoryDatabase()
        dataset = build_seed_dataset(effective_clock.now(), self._s.pseudonym_secret)
        for c in dataset.customers:
            db.customers[c.id.value] = c
        for o in dataset.orders:
            db.orders[o.number.value] = o
        for s in dataset.shipments:
            db.shipments[s.order_number.value] = s
        for p in dataset.products:
            db.products[p.sku] = p

        console = ConsoleChannel()
        fake_hd = FakeHelpdeskGateway()

        async def _health() -> dict[str, bool]:
            return {"memory_db": True}

        return self.build_wired_from_parts(
            clock=effective_clock,
            customers=InMemoryCustomerRepository(db),
            orders=InMemoryOrderRepository(db),
            shipments=InMemoryShipmentRepository(db),
            conversations=InMemoryConversationRepository(db),
            outbox=InMemoryOutboxRepository(db),
            handoffs=InMemoryHandoffRepository(db),
            catalog=InMemoryCatalogGateway(db),
            uow_factory=lambda: InMemoryUnitOfWork(db),
            lock=InMemoryConversationLock(),
            scheduler=RecordingTurnScheduler(),
            rate_limiter=InMemoryRateLimiter(),
            channel=console,
            helpdesk=fake_hd,
            session_service=make_session_service(backend="memory"),
            health_check=_health,
            console_channel=console,
            fake_helpdesk=fake_hd,
            memory_db=db,
        )

    @asynccontextmanager
    async def scope(self, *, null_pool: bool = False) -> AsyncIterator[WiredApp]:
        """Escopo com MySQL + Redis reais (para FastAPI ou tasks Celery isoladas)."""
        engine: AsyncEngine = create_mysql_engine(self._s.mysql_dsn, null_pool=null_pool)
        session_factory = create_session_factory(engine)
        redis: Redis = Redis.from_url(self._s.redis_url, decode_responses=False)
        cipher = FernetSecretCipher(self._s.phone_encryption_key)
        clock = SystemClock()

        console_channel: ConsoleChannel | None = None
        channel: MessageChannel
        if self._s.channel_mode == "whatsapp_cloud":
            channel = WhatsAppCloudChannel(
                access_token=self._s.whatsapp_access_token,
                phone_number_id=self._s.whatsapp_phone_number_id,
                api_version=self._s.whatsapp_api_version,
            )
        else:
            console_channel = ConsoleChannel()
            channel = console_channel

        fake_helpdesk: FakeHelpdeskGateway | None = None
        helpdesk: HelpdeskGateway
        if self._s.helpdesk_mode == "http":
            helpdesk = HttpHelpdeskGateway(
                base_url=self._s.helpdesk_base_url,
                api_token=self._s.helpdesk_api_token,
            )
        else:
            fake_helpdesk = FakeHelpdeskGateway()
            helpdesk = fake_helpdesk

        session_service = make_session_service(
            backend=self._s.adk_session_backend,
            adk_sessions_dsn=self._s.adk_sessions_dsn,
            null_pool=null_pool,
        )

        async def _health() -> dict[str, bool]:
            mysql_ok = False
            redis_ok = False
            try:
                async with engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                    mysql_ok = True
            except Exception:
                mysql_ok = False
            try:
                redis_ok = bool(await redis.ping())
            except Exception:
                redis_ok = False
            return {"mysql": mysql_ok, "redis": redis_ok}

        try:
            yield self.build_wired_from_parts(
                clock=clock,
                customers=MySqlCustomerRepository(session_factory=session_factory),
                orders=MySqlOrderRepository(session_factory=session_factory),
                shipments=MySqlShipmentRepository(session_factory=session_factory),
                conversations=MySqlConversationRepository(
                    cipher=cipher, session_factory=session_factory
                ),
                outbox=MySqlOutboxRepository(cipher=cipher, session_factory=session_factory),
                handoffs=MySqlHandoffRepository(session_factory=session_factory),
                catalog=MySqlCatalogGateway(session_factory=session_factory),
                uow_factory=lambda: MySqlUnitOfWork(session_factory, cipher),
                lock=RedisConversationLock(redis),
                scheduler=CeleryTurnScheduler(self._s.redis_url),
                rate_limiter=RedisRateLimiter(redis),
                channel=channel,
                helpdesk=helpdesk,
                session_service=session_service,
                health_check=_health,
                console_channel=console_channel,
                fake_helpdesk=fake_helpdesk,
            )
        finally:
            await redis.aclose()
            await engine.dispose()
