# Restaurant Business AI

餐饮经营数据分析与经营决策 SaaS Agent。当前版本为 **Batch 1: Foundation**，只提供后续 Agent 工作流所需的基础设施和契约，不包含经营数据、天气、RAG、Planner 或 Aggregator 的真实实现。

## 当前能力

- FastAPI 应用与 `GET /health`
- 基于环境变量和 `.env` 的配置
- 统一应用异常与参数校验错误响应
- JSON 日志基础配置
- `X-Request-ID` 请求链路标识
- 多租户请求、Evidence、Agent State 基础契约
- Database、LLM、Embedding、Weather、Vector Store Provider 接口草案
- Domain Workflow 接口草案

## 目录

```text
app/
├── api/routes/          # HTTP 路由
├── contracts/           # Evidence、State、Provider、Domain 契约
├── core/                # 配置、异常、日志
├── middleware/          # Request ID 中间件
└── main.py              # FastAPI 应用工厂
tests/
├── integration/         # API 集成测试
└── unit/                # 配置与契约单元测试
```

## Windows / PyCharm 运行

推荐 Python 3.11 或 3.12。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

PyCharm 中可将 `.venv\Scripts\python.exe` 配置为项目解释器，并以 `uvicorn app.main:app --reload` 启动。接口文档位于 `http://127.0.0.1:8000/docs`。

## 健康检查

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

响应示例：

```json
{
  "status": "ok",
  "service": "Restaurant Business AI",
  "version": "0.1.0",
  "environment": "development"
}
```

每个响应都包含 `X-Request-ID`。调用方传入该请求头时服务会复用它，否则服务自动生成 UUID。

## 测试

```powershell
python -m pytest
```

测试不访问互联网，不要求 LLM、天气 API、外部数据库或向量数据库。

## 架构边界

Batch 1 采用 Provider 隔离外部实现，以统一 `Evidence` 作为未来各领域工作流的输出，并用强类型 `AgentState` 约束未来 LangGraph 状态。所有接口目前均为草案；没有提前绑定 SQLite、模型供应商、天气供应商或向量数据库。

Batch 2 在审核通过后才会实现 SQLAlchemy、SQLite Backend、Repository、Business Data Workflow 和 LangGraph 的首条真实链路。

