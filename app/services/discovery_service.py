from app.api.errors import APIError
from app.core.domain.registry import DomainEnum, DomainNotRegisteredError, get_domain


class DiscoveryService:
    def list_domains(self) -> list[str]:
        return [member.value for member in DomainEnum]

    def list_topics(self, domain: str | None) -> list[str]:
        if domain is None:
            raise APIError(
                status_code=400,
                detail="Parâmetro domain é obrigatório.",
                code="INVALID_DOMAIN",
            )

        try:
            domain_enum = DomainEnum(domain)
        except ValueError:
            raise APIError(
                status_code=400,
                detail="Domínio inválido.",
                code="INVALID_DOMAIN",
            )

        try:
            module = get_domain(domain_enum)
        except DomainNotRegisteredError:
            raise APIError(
                status_code=400,
                detail="Domínio não registrado.",
                code="INVALID_DOMAIN",
            )

        return module.question_bank.topics()
