from typing import get_type_hints

import pytest
from pydantic import JsonValue, ValidationError

from app.contracts.api import ClientRequestContext, TenantContext
from app.contracts.providers import DatabaseBackend
from app.contracts.state import AgentState
from app.core.config import Settings
from app.core.tenant import resolve_default_tenant_context


def test_default_tenant_context_comes_from_server_configuration() -> None:
    settings = Settings(
        _env_file=None,
        environment="development",
        default_tenant_id="dev_tenant",
    )

    context = resolve_default_tenant_context(settings)

    assert context == TenantContext(tenant_id="dev_tenant")


def test_client_request_context_rejects_tenant_identity() -> None:
    with pytest.raises(ValidationError):
        ClientRequestContext.model_validate(
            {"session_id": "session-1", "tenant_id": "untrusted_tenant"}
        )


def test_database_backend_exposes_session_boundary_not_raw_sql() -> None:
    assert "session" in DatabaseBackend.__dict__
    assert "execute" not in DatabaseBackend.__dict__


def test_agent_state_trace_metadata_is_json_safe() -> None:
    trace_type = get_type_hints(AgentState)["trace_metadata"]

    assert trace_type == dict[str, JsonValue]
