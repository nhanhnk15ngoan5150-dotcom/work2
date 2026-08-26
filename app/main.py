from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.agent import router as agent_router
from app.api.routes.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.middleware.request_id import RequestIDMiddleware
from app.domains.business.product_service import ProductService
from app.domains.business.repository import BusinessDataRepository
from app.domains.business.sales_service import SalesService
from app.domains.business.store_service import StoreService
from app.domains.business.time_service import TimeRangeService
from app.infrastructure.database.sqlite import SQLiteBackend
from app.routing.fast_router import FastRouter
from app.workflows.business_data import BusinessDataWorkflow


def create_app(settings: Settings | None = None) -> FastAPI:
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

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        database_backend.dispose()

    # 3. 创建应用并注册基础设施
    application = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        debug=app_settings.debug,
        lifespan=lifespan,
    )
    application.state.settings = app_settings
    application.state.fast_router = FastRouter()
    application.state.business_data_workflow = workflow
    application.add_middleware(RequestIDMiddleware)
    register_exception_handlers(application)

    # 4. 注册基础路由
    application.include_router(health_router)
    application.include_router(agent_router)
    return application


app = create_app()
