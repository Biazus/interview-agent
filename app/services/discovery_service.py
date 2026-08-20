from app.core.domain.registry import (
    DomainEnum,
    DomainNotRegisteredError,
    get_cached_domain,
    list_registered_domains,
)
from app.core.exceptions import DomainRequired, InvalidDomain


class DiscoveryService:
    def list_domains(self) -> list[str]:
        return list_registered_domains()

    def list_topics(self, domain: str | None) -> list[str]:
        if domain is None:
            raise DomainRequired()

        try:
            domain_enum = DomainEnum(domain)
        except ValueError as exc:
            raise InvalidDomain() from exc

        try:
            module = get_cached_domain(domain_enum)
        except DomainNotRegisteredError as exc:
            raise InvalidDomain("Domínio não registrado.") from exc

        return module.question_bank.topics()
