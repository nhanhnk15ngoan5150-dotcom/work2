import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.agent import router as agent_router
from app.api.routes.health import router as health_router
from app.core.config import (
    DEMO_KNOWLEDGE_DIR,
    KNOWLEDGE_INDEX_PATH,
    PROJECT_ROOT,
    Settings,
    get_settings,
)
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.contracts.domains import DomainWorkflow
from app.contracts.evidence import EvidenceDomain
from app.contracts.knowledge import KnowledgeMetadata
from app.contracts.providers import EmbeddingProvider, LLMProvider
from app.middleware.request_id import RequestIDMiddleware
from app.domains.business.product_service import ProductService
from app.domains.business.repository import BusinessDataRepository
from app.domains.business.sales_service import SalesService
from app.domains.business.store_service import StoreService
from app.domains.business.time_service import TimeRangeService
from app.infrastructure.database.sqlite import SQLiteBackend
from app.domains.knowledge.chunker import KnowledgeChunker
from app.domains.knowledge.embedding_service import EmbeddingService
from app.domains.knowledge.indexer import KnowledgeIndexer
from app.domains.knowledge.parser import TextDocumentParser
from app.domains.knowledge.retriever import KnowledgeRetriever
from app.domains.knowledge.service import KnowledgeService
from app.domains.llm.service import LLMService
from app.domains.weather.service import WeatherService
from app.infrastructure.knowledge.local_vector_store import LocalVectorStore
from app.infrastructure.knowledge.openai_embeddings import (
    OpenAICompatibleEmbeddingProvider,
)
from app.infrastructure.llm.openai_compatible import OpenAICompatibleLLMProvider
from app.infrastructure.weather.open_meteo import OpenMeteoWeatherProvider
from app.orchestration.aggregator import EvidenceAggregator
from app.orchestration.evidence_validator import EvidenceValidator
from app.orchestration.multi_domain import MultiDomainOrchestrator
from app.orchestration.planner import DeterministicPlanner
from app.routing.fast_router import FastRouter
from app.workflows.business_data import BusinessDataWorkflow
from app.workflows.external_factor import ExternalFactorWorkflow
from app.workflows.knowledge_operation import KnowledgeOperationWorkflow

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    *,
    embedding_provider_override: EmbeddingProvider | None = None,
    llm_provider_override: LLMProvider | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""
    # 1. 加载应用配置
    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)

    # 2. 初始化经营数据依赖
    database_backend = SQLiteBackend(app_settings.database_url)
    repository = BusinessDataRepository(database_backend)
    workflow = BusinessDataWorkflow(
        TimeRangeService(repository),
        SalesService(repository),
        StoreService(repository),
        ProductService(repository),
    )

    # 3. 初始化天气与知识领域依赖
    weather_provider = OpenMeteoWeatherProvider()
    external_factor_workflow = ExternalFactorWorkflow(
        WeatherService(weather_provider)
    )
    domain_workflows: dict[EvidenceDomain, DomainWorkflow] = {
        EvidenceDomain.BUSINESS_DATA: workflow,
        EvidenceDomain.EXTERNAL_FACTOR: external_factor_workflow,
    }

    embedding_provider: EmbeddingProvider | None = embedding_provider_override
    owned_embedding_provider: OpenAICompatibleEmbeddingProvider | None = None
    knowledge_indexer: KnowledgeIndexer | None = None
    if embedding_provider is None and (
        app_settings.embedding_provider == "openai_compatible"
        and app_settings.embedding_api_key
    ):
        owned_embedding_provider = OpenAICompatibleEmbeddingProvider(
            base_url=app_settings.embedding_base_url,
            api_key=app_settings.embedding_api_key,
            model=app_settings.embedding_model,
        )
        embedding_provider = owned_embedding_provider

    if embedding_provider is not None:
        embedding_service = EmbeddingService(embedding_provider)
        vector_store = LocalVectorStore(KNOWLEDGE_INDEX_PATH)
        knowledge_indexer = KnowledgeIndexer(
            KnowledgeChunker(),
            embedding_service,
            vector_store,
        )
        domain_workflows[EvidenceDomain.KNOWLEDGE_OPERATION] = (
            KnowledgeOperationWorkflow(
                KnowledgeService(
                    KnowledgeRetriever(embedding_service, vector_store)
                )
            )
        )

    # 4. 初始化可选 Multi-Domain 聚合依赖
    llm_provider: LLMProvider | None = llm_provider_override
    owned_llm_provider: OpenAICompatibleLLMProvider | None = None
    if llm_provider is None and (
        app_settings.llm_provider == "openai_compatible"
        and app_settings.llm_api_key
    ):
        owned_llm_provider = OpenAICompatibleLLMProvider(
            base_url=app_settings.llm_base_url,
            api_key=app_settings.llm_api_key,
            model=app_settings.llm_model,
        )
        llm_provider = owned_llm_provider

    multi_domain_orchestrator: MultiDomainOrchestrator | None = None
    if llm_provider is not None:
        multi_domain_orchestrator = MultiDomainOrchestrator(
            DeterministicPlanner(),
            domain_workflows,
            EvidenceValidator(),
            EvidenceAggregator(LLMService(llm_provider)),
        )

    demo_documents = []
    if knowledge_indexer is not None:
        parser = TextDocumentParser()
        for document_id, filename in (
            ("membership-rules", "membership_rules.md"),
            ("rainy-day-sop", "rainy_day_sop.md"),
        ):
            path = DEMO_KNOWLEDGE_DIR / filename
            demo_documents.append(
                parser.parse(
                    path,
                    KnowledgeMetadata(
                        tenant_id=app_settings.default_tenant_id,
                        domains=[EvidenceDomain.KNOWLEDGE_OPERATION],
                        knowledge_base_id="demo-operations",
                        document_id=document_id,
                        source=path.relative_to(PROJECT_ROOT).as_posix(),
                        version="1.0",
                    ),
                )
            )

    @asynccontextmanager
    async def lifespan(lifespan_app: FastAPI):
        if knowledge_indexer is not None:
            try:
                await knowledge_indexer.index(demo_documents)
            except Exception as exc:
                domain_workflows.pop(EvidenceDomain.KNOWLEDGE_OPERATION, None)
                lifespan_app.state.knowledge_ready = False
                lifespan_app.state.knowledge_bootstrap_error = (
                    f"{type(exc).__name__}: {exc}"
                )
                logger.exception("knowledge_bootstrap_failed")
            else:
                lifespan_app.state.knowledge_ready = True
        try:
            yield
        finally:
            database_backend.dispose()
            await weather_provider.close()
            if owned_embedding_provider is not None:
                await owned_embedding_provider.close()
            if owned_llm_provider is not None:
                await owned_llm_provider.close()

    # 5. 创建应用并注册基础设施
    application = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        debug=app_settings.debug,
        lifespan=lifespan,
    )
    application.state.settings = app_settings
    application.state.fast_router = FastRouter()
    application.state.business_data_workflow = workflow
    application.state.external_factor_workflow = external_factor_workflow
    application.state.domain_workflows = domain_workflows
    application.state.multi_domain_orchestrator = multi_domain_orchestrator
    application.state.knowledge_ready = False
    application.state.knowledge_bootstrap_error = None
    application.state.knowledge_index_path = KNOWLEDGE_INDEX_PATH
    application.state.demo_knowledge_dir = DEMO_KNOWLEDGE_DIR
    application.add_middleware(RequestIDMiddleware)
    register_exception_handlers(application)

    # 6. 注册基础路由
    application.include_router(health_router)
    application.include_router(agent_router)
    return application


app = create_app()
