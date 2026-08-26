from collections.abc import Sequence

from fastapi.testclient import TestClient

from app.contracts.evidence import EvidenceDomain
from app.core.config import Settings
from app.domains.knowledge.exceptions import KnowledgeProviderError
from app.main import create_app


class FailingEmbeddingProvider:
    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        raise KnowledgeProviderError("mock bootstrap failure")


def test_knowledge_bootstrap_failure_does_not_stop_other_domains() -> None:
    application = create_app(
        Settings(
            _env_file=None,
            environment="test",
            log_level="CRITICAL",
        ),
        embedding_provider_override=FailingEmbeddingProvider(),
    )

    with TestClient(application) as client:
        business_response = client.post(
            "/api/v1/agent/query",
            json={"question": "7月份营业额是多少？"},
        )
        knowledge_response = client.post(
            "/api/v1/agent/query",
            json={"question": "会员折扣规则是什么？"},
        )

    assert business_response.status_code == 200
    assert business_response.json()["route"] == "BUSINESS_DATA"
    assert EvidenceDomain.EXTERNAL_FACTOR in application.state.domain_workflows
    assert application.state.knowledge_ready is False
    assert "KnowledgeProviderError" in application.state.knowledge_bootstrap_error
    assert knowledge_response.status_code == 503
    assert knowledge_response.json()["error"]["code"] == "KNOWLEDGE_UNAVAILABLE"
