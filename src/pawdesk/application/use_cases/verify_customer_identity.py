"""Caso de uso: elevação de verificação de identidade para STEP_UP (RN-01)."""

from pawdesk.application.dto.context import CallerContext
from pawdesk.application.dto.results import VerificationView
from pawdesk.application.services.identity_service import IdentityService
from pawdesk.domain.value_objects.ids import OrderNumber
from pawdesk.shared.constants.limits import MAX_VERIFICATION_ATTEMPTS


class VerifyCustomerIdentity:
    """Executa verificação reforçada (nº do pedido + 3 últimos dígitos do CPF)."""

    def __init__(self, identity_service: IdentityService) -> None:
        self._identity = identity_service

    async def execute(
        self,
        caller: CallerContext,
        order_number: OrderNumber,
        cpf_last3: str,
    ) -> VerificationView:
        decision = await self._identity.evaluate_step_up(
            caller=caller,
            order_number=order_number,
            cpf_last3=cpf_last3,
        )
        if decision.verified:
            return VerificationView(
                verified=True,
                verification_level=decision.new_level,
                attempts_remaining=MAX_VERIFICATION_ATTEMPTS,
                blocked=False,
                should_handoff=False,
                message="Identidade confirmada com sucesso.",
            )

        if decision.reason == "BLOCKED":
            return VerificationView(
                verified=False,
                verification_level=decision.new_level,
                attempts_remaining=0,
                blocked=True,
                should_handoff=True,
                message=(
                    "A verificação está temporariamente bloqueada por segurança. "
                    "Vou encaminhar para um atendente humano."
                ),
            )

        if decision.should_handoff:
            return VerificationView(
                verified=False,
                verification_level=decision.new_level,
                attempts_remaining=0,
                blocked=True,
                should_handoff=True,
                message=(
                    "Atingimos o limite de 3 tentativas de confirmação. "
                    "Vou transferir para um atendente humano te ajudar com segurança."
                ),
            )

        remaining = max(0, MAX_VERIFICATION_ATTEMPTS - decision.attempts)
        return VerificationView(
            verified=False,
            verification_level=decision.new_level,
            attempts_remaining=remaining,
            blocked=False,
            should_handoff=False,
            message=(f"Os dados informados não conferem. Você ainda tem {remaining} tentativa(s)."),
        )
