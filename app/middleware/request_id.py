from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import request_id_context

REQUEST_ID_HEADER = b"x-request-id"
MAX_REQUEST_ID_LENGTH = 128


class RequestIDMiddleware:
    """Attach a stable request identifier to request state, logs, and response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 1. 读取或生成请求标识
        headers = dict(scope.get("headers", []))
        incoming = headers.get(REQUEST_ID_HEADER, b"").decode("latin-1").strip()
        request_id = (
            incoming
            if incoming and len(incoming) <= MAX_REQUEST_ID_LENGTH
            else str(uuid4())
        )
        scope.setdefault("state", {})["request_id"] = request_id
        token = request_id_context.set(request_id)

        # 2. 将请求标识写入响应头
        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = list(message.get("headers", []))
                response_headers.append((REQUEST_ID_HEADER, request_id.encode("latin-1")))
                message["headers"] = response_headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            request_id_context.reset(token)

