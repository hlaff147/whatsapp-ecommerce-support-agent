# PawDesk 🐾

Agente conversacional de IA para atendimento ao cliente de e-commerce pet via WhatsApp, construído com **Google ADK**, **Arquitetura Hexagonal** (`import-linter`) e processamento assíncrono (**FastAPI + Celery + Redis + MySQL 8**).

## Documentação

- [Documento de Produto (Negócio)](docs/01-negocio-produto.md)
- [Documento Técnico de Arquitetura](docs/02-tecnico-arquitetura.md)

---

## Escopo Implementado (MVP Fases 0 a 4)

- **UC-01**: Consulta de pedidos recentes, status detalhado, rastreamento e detecção automática de atraso (RN-04: > 3 dias úteis → handoff).
- **UC-02**: Estimativa de prazo e frete por CEP + SKU via catálogo e gateway de transportadora (RN-03: sem estimativa pelo LLM).
- **UC-07**: Handoff humano com política objetiva (`HandoffPolicy`), resumo mascarado (≤ 5 linhas via `case_summarizer_agent`), abertura de ticket no helpdesk, silenciamento automático do bot (`WITH_HUMAN`), encaminhamento de novas mensagens e retomada via webhook do helpdesk.
- **UC-08 & Segurança**: Proteção em dois níveis (RN-01 `PHONE_MATCH` e `STEP_UP`), anti-IDOR no use case (RN-02), guardrails de entrada/saída (`input_guard`, `output_guard`, `tool_authz`, `tool_audit`), resposta segura em emergências veterinárias (RN-14), redação de PII em logs/mensagens e rota administrativa de anonimização LGPD (RN-17).

---

## Arquitetura Hexagonal (Visão de Componentes e Fronteiras)

As dependências entre camadas são verificadas automaticamente no CI via `import-linter` (4 contratos ativos: camadas hexagonais, núcleo livre de frameworks, `shared` folha pura e adaptadores independentes entre si).

```mermaid
flowchart LR
    subgraph IN["Adaptadores de Entrada (adapters/inbound)"]
        WA_WH["FastAPI: /webhooks/whatsapp (HMAC-SHA256)"]
        HD_WH["FastAPI: /webhooks/helpdesk"]
        ADMIN["FastAPI: /admin, /health e /simulator"]
        WORKER["Celery Worker e Beat (process_turn, send_message, sweepers)"]
    end

    subgraph AGENT_IN["ADK Tools — Entrada do LLM (adapters/agentic/tools)"]
        TOOLS["order_tools · identity_tools · control_tools (@guarded_tool)"]
    end

    subgraph CORE["Núcleo Hexagonal (application + domain + shared)"]
        UC["Use Cases (11)"]
        SVC["Application Services (Identity, Handoff, Conversation, PII, Cost)"]
        DOM["Domínio Puro (Entities, VOs e Policies)"]
        PORTS["Portas de Saída (Protocols)"]
    end

    subgraph OUT["Adaptadores de Saída (adapters/outbound e agentic)"]
        ADK["AdkAgentRuntime e AdkCaseSummarizer (Google ADK / LiteLLM)"]
        MYSQL[("MySQL 8 (pawdesk + pawdesk_adk)")]
        REDIS[("Redis 7 (Lock, RateLimit, Broker)")]
        CHAN["WhatsAppCloudChannel / ConsoleChannel"]
        GW["Gateways (CarrierFake, CatalogMySql, Helpdesk)"]
        SEC_OBS["FernetSecretCipher · structlog (PII-safe) · OpenTelemetry"]
    end

    BOOT["Composition Root (bootstrap): Container, Settings, API, Worker, Seed"]

    WA_WH --> UC
    HD_WH --> UC
    ADMIN --> UC
    WORKER --> UC
    TOOLS --> UC

    UC --> SVC
    SVC --> DOM
    UC --> DOM
    UC --> PORTS
    SVC --> PORTS

    PORTS -.-> ADK
    PORTS -.-> MYSQL
    PORTS -.-> REDIS
    PORTS -.-> CHAN
    PORTS -.-> GW
    PORTS -.-> SEC_OBS

    ADK -. "LLM invoca tools" .-> TOOLS
    BOOT -. "injeta dependências" .-> IN
    BOOT -. "injeta dependências" .-> OUT
```

---

## Componentes da Camada Agêntica (Google ADK)

O `AdkAgentRuntime` atua com "dupla face": é chamado pelo núcleo como porta de saída (`AgentRuntime`) e volta ao núcleo pelas *tools* finas (adaptadores de entrada). Todos os agentes da árvore compartilham os mesmos callbacks de segurança e orçamento por turno.

```mermaid
flowchart TD
    RT["AdkAgentRuntime (Runner + SessionService)"]

    subgraph GUARDS["Guardrails Compartilhados (todos os agentes da árvore)"]
        BM["before_model_callback: input_guard (limite chars, injection, emergência pet RN-14, orçamento LLM)"]
        AM["after_model_callback: output_guard (ContentPolicy: sem diagnóstico, promessa ou vazamento PII)"]
        BT["before_tool_callback: tool_authz (nível mínimo de verificação, orçamento tools, transfer_to_agent)"]
        AT["after_tool_callback: tool_audit (auditoria redigida e histórico de tools no estado)"]
    end

    subgraph TREE["Árvore Multiagente ADK"]
        ROOT["concierge_agent (ROUTER): triagem, fora de escopo e delegação"]
        ORD["order_agent (SPECIALIST): status, rastreio, atraso e prazo por CEP"]
        IDN["identity_agent (ROUTER): verificação reforçada Nível 2 (step-up)"]
    end

    subgraph TOOLS_BOX["Tools Finas (sem customer_id nos argumentos)"]
        T_ORD["get_my_orders (L1) · get_order_status (L1) · track_shipment (L1) · estimate_delivery_by_zip (L0)"]
        T_IDN["verify_customer_identity (L0 para L2)"]
        T_CTL["request_human_handoff (L0): sinaliza estado para HandoffPolicy"]
    end

    SUM["AdkCaseSummarizer -> case_summarizer_agent (ROUTER): resumo até 5 linhas com fallback"]

    RT --> ROOT
    GUARDS -. "acoplados em" .-> TREE

    ROOT -->|"transfer_to_agent"| ORD
    ROOT -->|"transfer_to_agent"| IDN
    ORD -->|"devolve se mudar assunto"| ROOT
    IDN -->|"devolve após verificar"| ROOT

    ORD --> T_ORD
    IDN --> T_IDN
    ROOT --> T_CTL
    ORD --> T_CTL
    IDN --> T_CTL
```

---

## Fluxo Assíncrono Ponta a Ponta (Inbox, Debounce, Lock, Outbox e Handoff)

```mermaid
sequenceDiagram
    participant C as Cliente
    participant WA as WhatsApp Cloud API
    participant API as FastAPI Webhook
    participant DB as MySQL 8
    participant R as Redis / Celery
    participant UC as ProcessConversationTurn
    participant ADK as AdkAgentRuntime
    participant HD as Helpdesk

    C->>WA: Envia mensagem (ou rajada)
    WA->>API: POST /webhooks/whatsapp (X-Hub-Signature-256)
    API->>API: Valida assinatura HMAC-SHA256
    API->>DB: Grava mensagem IN (UNIQUE provider_message_id + PII redigida)
    API->>R: Agenda task process_turn (countdown debounce)
    API-->>WA: 200 OK imediato

    R->>UC: Worker executa process_turn(channel_user_hash)
    UC->>R: Adquire lock distribuído (conv:hash)
    UC->>DB: Lê todas as mensagens IN pendentes (consolida rajada)

    alt Conversa em status WITH_HUMAN
        UC->>HD: Encaminha mensagens redigidas ao ticket aberto
        UC->>DB: Marca mensagens como processadas (bot fica em silêncio)
    else Conversa ACTIVE
        UC->>ADK: run_turn(session_id, caller, texto, state_delta)
        ADK->>ADK: concierge delega ao especialista + callbacks + tools
        ADK-->>UC: reply_text, tools_called, usage, sinais de handoff
        UC->>UC: HandoffPolicy avalia sinais objetivos (RN-04, RN-14, frustração, legal)
        UC->>DB: Transação UoW: grava resposta + outbox PENDING + marca IN processadas (+ handoff_ticket)
        UC->>R: Libera lock e agenda send_message(outbox_id)
        R->>WA: Task send_message despacha resposta e marca outbox SENT
        WA-->>C: Entrega resposta no WhatsApp
    end
```

---

## Modelo de Dados (MySQL 8)

```mermaid
erDiagram
    CUSTOMERS ||--o{ ORDERS : faz
    ORDERS ||--|{ ORDER_ITEMS : contem
    ORDERS ||--o| SHIPMENTS : entrega
    SHIPMENTS ||--o{ SHIPMENT_EVENTS : movimenta
    CONVERSATIONS ||--o{ MESSAGES : possui
    CONVERSATIONS ||--o{ HANDOFF_TICKETS : gera
    CONVERSATIONS ||--o{ OUTBOX_MESSAGES : enfileira
    CONVERSATIONS ||--o{ RETURN_REQUESTS : origina
    CONVERSATIONS ||--o{ AUDIT_LOG : registra
```

> As sessões do Google ADK (`DatabaseSessionService`) ficam isoladas em um schema dedicado (`pawdesk_adk`), fora do controle do Alembic, provisionado automaticamente por [init.sql](docker/mysql/init.sql).

---

## Estrutura Principal

```text
src/pawdesk/
├── shared/        # Constantes e utilitários puros (stdlib)
├── domain/        # Entidades, Value Objects e políticas de negócio puras
├── application/   # Use cases, serviços de coordenação, DTOs e portas (Protocols)
├── adapters/
│   ├── inbound/   # FastAPI (webhooks, simulator, admin, health) e Celery worker/beat
│   ├── agentic/   # Google ADK runtime, agentes, prompts, tools finas e callbacks
│   └── outbound/  # MySQL (SQLAlchemy async), Redis, Celery scheduler, canais, gateways e OTel
└── bootstrap/     # Composition root (Container, Settings, API, Worker, Seed)
```

---

## Ambiente Local e Testes (sem chave de API externa)

```bash
cp .env.example .env
uv sync --extra dev

# Lint, tipagem estática e contratos hexagonais
uv run ruff check .
uv run mypy src
uv run lint-imports

# Testes unitários, agentes ADK (ScriptedFakeLlm), contrato (memória + SQLite) e E2E
uv run pytest tests/unit tests/agents tests/e2e tests/contract tests/integration -m "not integration" -v
```

## Stack Completa com Docker Compose (MySQL 8 + Redis + API + Celery + Beat)

```bash
make up
make migrate
make seed
curl http://localhost:8000/health/ready
make chat
```

Personas sintéticas disponíveis após o seed:
- **Marina** (`+5511999990001`, CPF final `456`): pedido `PD-104822` em rota de entrega hoje e `PD-104510` entregue.
- **Carlos** (`+5511999990002`, CPF final `789`): pedido `PD-104901` em separação.
- **Bia** (`+5511999990003`, CPF final `321`): pedido `PD-104300` atrasado > 3 dias úteis (dispara handoff RN-04) e `PD-104750` com atraso leve.

Para subir a UI visual do Google ADK (`adk web`) usando dados em memória (requer chave de API configurada no `.env`):

```bash
make adk-web
```
