"""Textos padronizados ao cliente (pt-BR), alinhados ao tom de voz do PawDesk."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Messages:
    agent_error: str = (
        "Tive uma instabilidade por aqui agora, mas não vou te deixar esperando. "
        "Vou encaminhar sua conversa para um atendente humano com todo o histórico."
    )
    pet_emergency_base: str = (
        "🐾 Sinto muito por essa situação. Por segurança do seu pet, eu não posso fazer "
        "diagnósticos ou indicar medicamentos ou dosagens. Por favor, procure um médico "
        "veterinário ou pronto-socorro veterinário imediatamente."
    )
    pet_emergency_with_vet_channel: str = (
        "🐾 Sinto muito por essa situação. Por segurança do seu pet, eu não posso fazer "
        "diagnósticos ou indicar medicamentos ou dosagens. Procure um veterinário "
        "imediatamente; também já acionei nosso canal veterinário de emergência para "
        "priorizar o seu atendimento."
    )
    handoff_in_business_hours: str = (
        "Já passei seu caso e o resumo da conversa para um atendente humano. "
        "Em poucos minutos nossa equipe continua por aqui sem você precisar repetir nada."
    )
    handoff_out_of_hours: str = (
        "Já registrei seu atendimento com o resumo completo da conversa. "
        "Nossa equipe humana atende em horário comercial (segunda a sexta, das 09h às 18h) "
        "e responderá assim que o expediente iniciar."
    )
    handoff_urgent_notice: str = (
        "Entendo sua insatisfação e vou priorizar seu caso com nossa equipe humana agora mesmo."
    )
    handoff_resumed: str = (
        "🐾 Seu atendimento com nossa equipe foi concluído! Se precisar de mais alguma "
        "ajuda com seus pedidos ou prazos, é só me chamar por aqui."
    )
    out_of_scope: str = (
        "No momento eu ajudo com status e rastreio de pedidos, prazos de entrega e "
        "encaminhamento para a equipe. Quer que eu te transfira para um atendente humano?"
    )
    verification_blocked: str = (
        "Por segurança, atingimos o limite de tentativas de confirmação. "
        "Vou encaminhar você para um atendente humano continuar seu atendimento."
    )
    output_guard_fallback: str = (
        "Não consigo confirmar essa informação por aqui sem verificação no sistema. "
        "Posso te ajudar consultando seu pedido ou transferindo para um atendente humano?"
    )
    prompt_injection_deflection: str = (
        "Consigo ajudar apenas com consultas de pedidos, prazos de entrega e "
        "encaminhamento para nossa equipe seguindo as políticas da loja."
    )
