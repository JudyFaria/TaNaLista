"""Erros de domínio.

A camada de domínio não conhece HTTP: ela sinaliza *o que* deu errado e a
camada de apresentação decide *como* comunicar isso ao cliente.
"""


class DomainError(Exception):
    """Base para todos os erros de regra de negócio."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ValidationError(DomainError):
    """Dados de entrada inválidos."""


class NotFoundError(DomainError):
    """Recurso inexistente (ou invisível para quem pediu)."""


class PermissionDeniedError(DomainError):
    """O usuário não tem permissão para a ação."""


class ConflictError(DomainError):
    """A ação conflita com o estado atual (ex.: duplicidade)."""


class AuthenticationError(DomainError):
    """Credenciais ou token inválidos."""
