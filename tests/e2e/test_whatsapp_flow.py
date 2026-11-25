"""Testes E2E da API FastAPI (webhook WhatsApp, simulador, handoff, LGPD e logs sem PII)."""

import json

from fastapi.testclient import TestClient
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_llm import ScriptedFakeLlm, text_response, tool_call_response

from pawdesk.adapters.agentic.constants import ModelRole
from pawdesk.adapters.inbound.http.app import create_app_from_deps
from pawdesk.bootstrap.container import Container
from pawdesk.bootstrap.settings import Settings
from pawdesk.shared.utils.hashing import hmac_sha256


def _test_settings() -> Settings:
    return Settings(
        storage_backend="memory",
        adk_session_backend="memory",
        channel_mode="console",
        helpdesk_mode="fake",
        whatsapp_verify_token="verify-secret",
        whatsapp_app_secret="app-secret",
        admin_api_token="admin-secret",
        helpdesk_webhook_secret="helpdesk-secret",
        enable_simulator=True,
    )


def test_whatsapp_webhook_verify_and_hmac() -> None:
    settings = _test_settings()
    wired = Container(settings).build_for_dev(clock=FakeClock())
    client = TestClient(create_app_from_deps(wired.http_dependencies()))

    ok_verify = client.get(
        "/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "verify-secret",
            "hub.challenge": "12345",
        },
    )
    assert ok_verify.status_code == 200
    assert ok_verify.text == "12345"

    bad_verify = client.get(
        "/webhooks/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "12345"},
    )
    assert bad_verify.status_code == 403

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": "wamid.meta.1",
                                    "from": "5511999990001",
                                    "type": "text",
                                    "text": {"body": "oi, cadê meu pedido?"},
                                }
                            ]
                        }
                    }
                ]
            }
        ],
    }
    raw = json.dumps(payload).encode("utf-8")

    # Assinatura inválida
    resp_bad = client.post(
        "/webhooks/whatsapp",
        content=raw,
        headers={"X-Hub-Signature-256": "sha256=invalid", "Content-Type": "application/json"},
    )
    assert resp_bad.status_code == 401

    # Assinatura válida -> aceita na primeira e ignora duplicada
    sig = "sha256=" + hmac_sha256(raw, settings.whatsapp_app_secret)
    resp_1 = client.post(
        "/webhooks/whatsapp",
        content=raw,
        headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"},
    )
    assert resp_1.status_code == 200
    assert resp_1.json() == {"status": "ok", "accepted": 1}

    resp_dup = client.post(
        "/webhooks/whatsapp",
        content=raw,
        headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"},
    )
    assert resp_dup.status_code == 200
    assert resp_dup.json() == {"status": "ok", "accepted": 0}


def test_e2e_simulator_burst_dedup_handoff_silence_resume_and_lgpd() -> None:
    settings = _test_settings()
    router_llm = ScriptedFakeLlm(
        [
            tool_call_response("transfer_to_agent", {"agent_name": "order_agent"}),
            # Turno 2 (Bia, atraso crítico -> handoff + sumarizador):
            tool_call_response("transfer_to_agent", {"agent_name": "order_agent"}),
            text_response("Bia consultou PD-104300 com atraso crítico."),
            # Turno 3 (após retomada do helpdesk):
            text_response("Oi Bia! Em que mais posso te ajudar hoje?"),
        ]
    )
    specialist_llm = ScriptedFakeLlm(
        [
            tool_call_response("get_order_status", {"order_number": "PD-104822"}),
            text_response("Oi Marina! Seu pedido PD-104822 saiu para entrega hoje."),
            tool_call_response("get_order_status", {"order_number": "PD-104300"}),
            text_response("Seu pedido PD-104300 está com atraso na rota."),
        ]
    )
    wired = Container(
        settings,
        model_overrides={ModelRole.ROUTER: router_llm, ModelRole.SPECIALIST: specialist_llm},
    ).build_for_dev(clock=FakeClock())
    client = TestClient(create_app_from_deps(wired.http_dependencies()))

    # 1) Rajada da Marina consolida em 1 resposta
    r_burst = client.post(
        "/simulator/whatsapp/messages",
        json={
            "phone": "+5511999990001",
            "burst": ["oi", "cadê meu pedido PD-104822?"],
            "sync": True,
        },
    )
    assert r_burst.status_code == 200
    body_burst = r_burst.json()
    assert body_burst["accepted"] == 2
    assert len(body_burst["replies"]) == 1
    assert "PD-104822" in body_burst["replies"][0]["text"]

    # 2) Mensagem duplicada não gera novo processamento
    r_dup1 = client.post(
        "/simulator/whatsapp/messages",
        json={
            "phone": "+5511999990001",
            "text": "obrigada",
            "provider_message_id": "dup-fixed-1",
            "sync": False,
        },
    )
    r_dup2 = client.post(
        "/simulator/whatsapp/messages",
        json={
            "phone": "+5511999990001",
            "text": "obrigada",
            "provider_message_id": "dup-fixed-1",
            "sync": False,
        },
    )
    assert r_dup1.json()["accepted"] == 1
    assert r_dup2.json()["accepted"] == 0

    # 3) Bia pergunta sobre pedido criticamente atrasado -> handoff + silêncio
    r_bia = client.post(
        "/simulator/whatsapp/messages",
        json={"phone": "+5511999990003", "text": "cadê o PD-104300?", "sync": True},
    )
    assert r_bia.json()["conversation_status"] == "WITH_HUMAN"
    bia_conv_id = r_bia.json()["conversation_id"]

    # Mensagem durante atendimento humano: encaminha ao helpdesk e bot silencia
    r_silence = client.post(
        "/simulator/whatsapp/messages",
        json={"phone": "+5511999990003", "text": "tem alguém aí?", "sync": True},
    )
    assert r_silence.json()["replies"] == []
    tickets = client.get("/simulator/helpdesk/tickets").json()["tickets"]
    assert len(tickets) == 1
    assert tickets[0]["forwarded_messages"] == ["tem alguém aí?"]

    # Helpdesk resolve via webhook autenticado
    r_res = client.post(
        "/webhooks/helpdesk/events",
        json={"conversation_id": bia_conv_id, "event": "resolved", "resolution_note": "ok"},
        headers={"Authorization": "Bearer helpdesk-secret"},
    )
    assert r_res.status_code == 200
    assert r_res.json()["status"] == "resumed"

    # Métricas e saúde
    assert client.get("/health/ready").status_code == 200
    metrics = client.get(
        "/admin/metrics", headers={"Authorization": "Bearer admin-secret"}
    ).json()
    assert metrics["turns_total"] == 2
    assert metrics["handoffs_total"] == 1

    # LGPD anonimização
    r_lgpd = client.post(
        "/admin/lgpd/anonymize",
        json={"phone": "+5511999990001"},
        headers={"Authorization": "Bearer admin-secret"},
    )
    assert r_lgpd.status_code == 200
    assert r_lgpd.json()["conversations_affected"] == 1
