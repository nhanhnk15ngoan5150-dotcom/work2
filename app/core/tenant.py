from app.contracts.api import TenantContext
from app.core.config import Settings


def resolve_default_tenant_context(settings: Settings) -> TenantContext:
    """Resolve the configured development tenant on the server side."""
    return TenantContext(tenant_id=settings.default_tenant_id)
