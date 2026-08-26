import asyncio
from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.contracts.evidence import EvidenceDomain
from app.contracts.knowledge import Document, KnowledgeMetadata
from app.contracts.weather import WeatherForecast, WeatherLocation, WeatherSnapshot
from app.domains.knowledge.chunker import KnowledgeChunker
from app.domains.knowledge.embedding_service import EmbeddingService
from app.domains.knowledge.indexer import KnowledgeIndexer
from app.domains.knowledge.retriever import KnowledgeRetriever
from app.domains.knowledge.service import KnowledgeService
from app.domains.weather.service import WeatherService
from app.infrastructure.knowledge.local_vector_store import LocalVectorStore
from app.workflows.external_factor import ExternalFactorWorkflow
from app.workflows.knowledge_operation import KnowledgeOperationWorkflow


class FakeWeatherProvider:
    async def current(self, location: str) -> WeatherSnapshot:
        return WeatherSnapshot(
            location=self._location(location),
            date=date(2026, 8, 26),
            weather_type="partly_cloudy",
            temperature=29.0,
            source="fake-weather",
        )

    async def forecast(self, location: str, days: int) -> list[WeatherForecast]:
        assert days == 2
        resolved = self._location(location)
        return [
            WeatherForecast(
                location=resolved,
                date=date(2026, 8, 26),
                source="fake-weather",
            ),
            WeatherForecast(
                location=resolved,
                date=date(2026, 8, 27),
                weather_type="moderate_rain",
                temperature_min=24.0,
                temperature_max=30.0,
                precipitation=6.0,
                source="fake-weather",
            ),
        ]

    @staticmethod
    def _location(name: str) -> WeatherLocation:
        return WeatherLocation(
            name=name,
            latitude=31.23,
            longitude=121.47,
            timezone="Asia/Shanghai",
        )


class FakeEmbeddingProvider:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [
            [1.0, 0.0]
            if any(keyword in text for keyword in ("会员", "折扣", "满减"))
            else [0.0, 1.0]
            for text in texts
        ]


def _install_knowledge_workflow(application: FastAPI) -> None:
    embedding_service = EmbeddingService(FakeEmbeddingProvider())
    vector_store = LocalVectorStore()
    metadata = KnowledgeMetadata(
        tenant_id="dev_tenant",
        domains=[EvidenceDomain.KNOWLEDGE_OPERATION],
        knowledge_base_id="demo-operations",
        document_id="membership-rules",
        source="data/demo_knowledge/membership_rules.md",
        version="1.0",
    )
    document = Document(
        title="会员优惠规则（演示）",
        content="会员折扣与满减优惠不能同时使用。",
        metadata=metadata,
    )
    asyncio.run(
        KnowledgeIndexer(
            KnowledgeChunker(),
            embedding_service,
            vector_store,
        ).index([document])
    )
    application.state.domain_workflows[EvidenceDomain.KNOWLEDGE_OPERATION] = (
        KnowledgeOperationWorkflow(
            KnowledgeService(
                KnowledgeRetriever(
                    embedding_service,
                    vector_store,
                    threshold=0.8,
                )
            )
        )
    )


def test_weather_api_runs_external_factor_branch(application: FastAPI) -> None:
    application.state.domain_workflows[EvidenceDomain.EXTERNAL_FACTOR] = (
        ExternalFactorWorkflow(WeatherService(FakeWeatherProvider()))
    )

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/agent/query",
            json={"question": "上海明天天气怎么样？"},
        )

    payload = response.json()
    assert response.status_code == 200
    assert payload["route"] == "EXTERNAL_FACTOR"
    assert payload["evidence"][0]["evidence_type"] == "PREDICTION"
    assert payload["evidence"][0]["confidence"] is None
    assert payload["evidence"][0]["value"]["date"] == "2026-08-27"


def test_knowledge_api_returns_cited_demo_rule(application: FastAPI) -> None:
    _install_knowledge_workflow(application)

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/agent/query",
            json={"question": "会员折扣和满减可以同时使用吗？"},
        )

    payload = response.json()
    assert response.status_code == 200
    assert payload["route"] == "KNOWLEDGE_OPERATION"
    assert payload["evidence"][0]["value"]["citation"]["document_id"] == (
        "membership-rules"
    )
    assert "不能同时使用" in payload["answer"]


def test_knowledge_api_returns_no_knowledge(application: FastAPI) -> None:
    _install_knowledge_workflow(application)

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/agent/query",
            json={"question": "公司春节奖金规则是什么？"},
        )

    payload = response.json()
    assert response.status_code == 200
    assert payload["route"] == "KNOWLEDGE_OPERATION"
    assert payload["evidence"] == []
    assert payload["warnings"] == ["NO_KNOWLEDGE"]
