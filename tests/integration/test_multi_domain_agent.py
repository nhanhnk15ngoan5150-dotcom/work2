import asyncio
from collections.abc import Sequence
from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.contracts.evidence import EvidenceDomain, EvidenceType
from app.contracts.knowledge import Document, KnowledgeMetadata
from app.contracts.llm import LLMMessage, LLMResponse
from app.contracts.weather import WeatherForecast, WeatherLocation, WeatherSnapshot
from app.core.config import Settings
from app.domains.knowledge.chunker import KnowledgeChunker
from app.domains.knowledge.embedding_service import EmbeddingService
from app.domains.knowledge.indexer import KnowledgeIndexer
from app.domains.knowledge.retriever import KnowledgeRetriever
from app.domains.knowledge.service import KnowledgeService
from app.domains.weather.exceptions import WeatherProviderError
from app.domains.weather.service import WeatherService
from app.infrastructure.knowledge.local_vector_store import LocalVectorStore
from app.main import create_app
from app.workflows.external_factor import ExternalFactorWorkflow
from app.workflows.knowledge_operation import KnowledgeOperationWorkflow

DEMO_4_QUESTION = "明天成都下雨，结合最近营业额和公司的雨天运营规范应该注意什么？"


class FakeLLMProvider:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.calls: list[Sequence[LLMMessage]] = []

    async def complete(self, messages: Sequence[LLMMessage]) -> LLMResponse:
        self.calls.append(messages)
        return LLMResponse(
            content=self.answer,
            model="fake-aggregator",
            input_tokens=120,
            output_tokens=60,
            total_tokens=180,
            latency_ms=8.0,
        )


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
            latitude=30.67,
            longitude=104.07,
            timezone="Asia/Shanghai",
        )


class FailingWeatherProvider(FakeWeatherProvider):
    async def forecast(self, location: str, days: int) -> list[WeatherForecast]:
        raise WeatherProviderError("weather unavailable")


class FakeEmbeddingProvider:
    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [
            [1.0, 0.0]
            if any(keyword in text for keyword in ("雨天", "下雨", "降雨"))
            else [0.0, 1.0]
            for text in texts
        ]


def _install_test_domains(
    application: FastAPI,
    weather_provider: FakeWeatherProvider,
) -> None:
    application.state.domain_workflows[EvidenceDomain.EXTERNAL_FACTOR] = (
        ExternalFactorWorkflow(WeatherService(weather_provider))
    )

    embedding_service = EmbeddingService(FakeEmbeddingProvider())
    vector_store = LocalVectorStore()
    metadata_base = {
        "tenant_id": "dev_tenant",
        "domains": [EvidenceDomain.KNOWLEDGE_OPERATION],
        "knowledge_base_id": "demo-operations",
        "version": "1.0",
    }
    documents = [
        Document(
            title="雨天运营规范（演示）",
            content="雨天应检查防滑垫，并根据客流情况安排外卖打包岗位。",
            metadata=KnowledgeMetadata(
                **metadata_base,
                document_id="rainy-day-sop",
                source="data/demo_knowledge/rainy_day_sop.md",
            ),
        ),
        Document(
            title="会员优惠规则（演示）",
            content="会员折扣与满减优惠不能同时使用。",
            metadata=KnowledgeMetadata(
                **metadata_base,
                document_id="membership-rules",
                source="data/demo_knowledge/membership_rules.md",
            ),
        ),
    ]
    asyncio.run(
        KnowledgeIndexer(
            KnowledgeChunker(),
            embedding_service,
            vector_store,
        ).index(documents)
    )
    application.state.domain_workflows[EvidenceDomain.KNOWLEDGE_OPERATION] = (
        KnowledgeOperationWorkflow(
            KnowledgeService(
                KnowledgeRetriever(embedding_service, vector_store, threshold=0.8)
            )
        )
    )


def _create_test_app(
    settings: Settings,
    weather_provider: FakeWeatherProvider,
    llm_provider: FakeLLMProvider,
) -> FastAPI:
    application = create_app(settings, llm_provider_override=llm_provider)
    _install_test_domains(application, weather_provider)
    return application


def test_demo_4_runs_three_domain_fan_out_and_aggregation(
    settings: Settings,
) -> None:
    llm = FakeLLMProvider(
        "天气预报、经营事实和雨天规范已综合。限制：缺少历史天气与营业额联合样本，无法判断因果。"
    )
    application = _create_test_app(settings, FakeWeatherProvider(), llm)

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/agent/query",
            json={"question": DEMO_4_QUESTION},
        )

    payload = response.json()
    domains = {item["domain"] for item in payload["evidence"]}
    assert response.status_code == 200
    assert payload["route"] == "MULTI_DOMAIN"
    assert set(payload["selected_domains"]) == {
        "BUSINESS_DATA",
        "EXTERNAL_FACTOR",
        "KNOWLEDGE_OPERATION",
    }
    assert domains == set(payload["selected_domains"])
    assert next(
        item for item in payload["evidence"] if item["domain"] == "EXTERNAL_FACTOR"
    )["evidence_type"] == EvidenceType.PREDICTION.value
    assert "无法判断因果" in payload["answer"]
    assert len(llm.calls) == 1
    llm_payload = llm.calls[0][1].content
    assert all(domain in llm_payload for domain in domains)
    assert payload["trace_metadata"]["execution_mode"] == "MULTI_DOMAIN"
    assert set(payload["trace_metadata"]["completed_domains"]) == domains
    assert payload["trace_metadata"]["failed_domains"] == []
    assert payload["trace_metadata"]["evidence_count"] == 3
    assert payload["trace_metadata"]["aggregation_mode"] == "llm"


def test_multi_domain_weather_failure_keeps_other_evidence(
    settings: Settings,
) -> None:
    llm = FakeLLMProvider(
        "已基于经营与知识证据给出建议；天气数据暂不可用，因此不能判断天气影响。"
    )
    application = _create_test_app(settings, FailingWeatherProvider(), llm)

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/agent/query",
            json={"question": DEMO_4_QUESTION},
        )

    payload = response.json()
    domains = {item["domain"] for item in payload["evidence"]}
    assert response.status_code == 200
    assert domains == {"BUSINESS_DATA", "KNOWLEDGE_OPERATION"}
    assert "EXTERNAL_FACTOR" not in domains
    assert any("EXTERNAL_FACTOR" in warning for warning in payload["warnings"])
    assert payload["trace_metadata"]["failed_domains"] == ["EXTERNAL_FACTOR"]
    assert "天气数据暂不可用" in payload["answer"]
    assert "天气服务暂时不可用" in llm.calls[0][1].content


def test_single_domain_short_paths_do_not_call_llm(settings: Settings) -> None:
    llm = FakeLLMProvider("不应调用")
    application = _create_test_app(settings, FakeWeatherProvider(), llm)

    with TestClient(application) as client:
        business = client.post(
            "/api/v1/agent/query",
            json={"question": "7月份营业额是多少？"},
        )
        weather = client.post(
            "/api/v1/agent/query",
            json={"question": "成都明天天气怎么样？"},
        )
        knowledge = client.post(
            "/api/v1/agent/query",
            json={"question": "会员折扣和满减可以同时使用吗？"},
        )

    assert [business.status_code, weather.status_code, knowledge.status_code] == [
        200,
        200,
        200,
    ]
    assert business.json()["route"] == "BUSINESS_DATA"
    assert weather.json()["route"] == "EXTERNAL_FACTOR"
    assert knowledge.json()["route"] == "KNOWLEDGE_OPERATION"
    assert llm.calls == []
