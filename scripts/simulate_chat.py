"""CLI interativa para simular conversas no PawDesk via endpoints /simulator."""

import argparse
import json
import sys

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulador de chat WhatsApp para o PawDesk")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--phone", default="+5511999990001")
    parser.add_argument(
        "--async-mode", action="store_true", help="Enfileira no Celery em vez de sync=true"
    )
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    phone = args.phone
    sync = not args.async_mode

    print(f"PawDesk Simulador | URL={base} | Telefone={phone} | sync={sync}")
    print(
        "Comandos: /phone <num>, /burst msg1 | msg2, /dup <msg>, "
        "/tickets, /resolve <conv_id>, /metrics, /quit"
    )

    last_conv_id: str | None = None
    with httpx.Client(timeout=30.0) as client:
        while True:
            try:
                line = input("\nVocê> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nEncerrando.")
                break
            if not line:
                continue
            if line == "/quit":
                break
            if line.startswith("/phone "):
                phone = line.removeprefix("/phone ").strip()
                print(f"Telefone ativo: {phone}")
                continue
            if line.startswith("/burst "):
                parts = [p.strip() for p in line.removeprefix("/burst ").split("|") if p.strip()]
                resp = client.post(
                    f"{base}/simulator/whatsapp/messages",
                    json={"phone": phone, "burst": parts, "sync": sync},
                )
            elif line.startswith("/dup "):
                txt = line.removeprefix("/dup ").strip()
                fixed_id = "wamid.dup.fixed.001"
                resp = client.post(
                    f"{base}/simulator/whatsapp/messages",
                    json={
                        "phone": phone,
                        "text": txt,
                        "provider_message_id": fixed_id,
                        "sync": sync,
                    },
                )
            elif line == "/tickets":
                resp = client.get(f"{base}/simulator/helpdesk/tickets")
                print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
                continue
            elif line.startswith("/resolve"):
                target = line.removeprefix("/resolve").strip() or (last_conv_id or "")
                if not target:
                    print("Informe o conversation_id.", file=sys.stderr)
                    continue
                resp = client.post(f"{base}/simulator/helpdesk/resolve/{target}")
                print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
                continue
            elif line == "/metrics":
                resp = client.get(
                    f"{base}/admin/metrics",
                    headers={"Authorization": "Bearer dev-admin-token"},
                )
                print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
                continue
            else:
                resp = client.post(
                    f"{base}/simulator/whatsapp/messages",
                    json={"phone": phone, "text": line, "sync": sync},
                )

            data = resp.json()
            if resp.status_code >= 400:
                print(f"[ERRO {resp.status_code}] {data}")
                continue
            last_conv_id = data.get("conversation_id") or last_conv_id
            print(f"[status={data.get('conversation_status')} conv={last_conv_id}]")
            for r in data.get("replies", []):
                print(f"PawDesk> {r.get('text')}")


if __name__ == "__main__":
    main()
