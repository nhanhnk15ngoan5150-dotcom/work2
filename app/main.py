from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.middleware.request_id import RequestIDMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    # 1. 加载应用配置
    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)

    # 2. 创建应用并注册基础设施
    application = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        debug=app_settings.debug,
    )
    application.state.settings = app_settings
    application.add_middleware(RequestIDMiddleware)
    register_exception_handlers(application)

    # 3. 注册基础路由
    application.include_router(health_router)
    return application


app = create_app()

