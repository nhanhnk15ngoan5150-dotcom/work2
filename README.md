# Restaurant Business AI

餐饮经营数据分析与经营决策 SaaS Agent。当前版本已完成 **Batch 2: Business Data**，提供一条基于 LangGraph、SQLAlchemy 和 SQLite 的可运行经营数据纵向链路。

## 当前能力

- FastAPI 应用与 `GET /health`
- 基于环境变量和 `.env` 的配置
- 统一应用异常与参数校验错误响应
- JSON 日志基础配置
- `X-Request-ID` 请求链路标识
- 多租户请求、Evidence、Agent State 基础契约
- SQLAlchemy Session 生命周期与 SQLiteBackend
- 数据驱动的月份、越界范围及“最近”时间语义
- 营业额、订单量、客单价及月度对比
- 门店经营排名和商品销售额、销量、排名
- 确定性 Fast Router 与 Business Data LangGraph Workflow
- 统一 `Evidence[]` 输出，事实证据不伪造 confidence

## 目录

```text
app/
├── api/routes/          # HTTP 路由
├── contracts/           # Evidence、State、Provider、Domain 契约
├── core/                # 配置、异常、日志
├── domains/business/    # 经营数据 Repository 与 Service
├── infrastructure/      # SQLite 与 SQLAlchemy 适配器
├── middleware/          # Request ID 中间件
├── routing/             # 确定性 Fast Router
├── workflows/           # LangGraph 领域工作流
└── main.py              # FastAPI 应用工厂
tests/
├── golden/              # work1 Verified Baseline 对齐测试
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

## Business Data 查询

```powershell
$body = @{ question = "7月份营业额是多少？" } | ConvertTo-Json
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/agent/query `
  -ContentType application/json `
  -Body $body
```

当前可测试问题：

- `7月份营业额是多少？`
- `最近营业额变化怎么样？`
- `最近哪个门店表现最好？`
- `六月可乐销量怎么样？`

客户端请求不接受可信 `tenant_id`。开发租户由服务端配置解析，默认使用 `dev_tenant`。

## 测试

```powershell
python -m pytest -q -p no:cacheprovider
```

测试不访问互联网，不要求 LLM、天气 API、PostgreSQL、MySQL 或向量数据库。

## 架构边界

运行链路：

```text
FastAPI
→ Fast Router
→ Business Data Workflow
→ Service
→ Repository
→ DatabaseBackend
→ SQLAlchemy Session
→ SQLite
→ Evidence
→ Response
```

Repository 使用 SQLAlchemy Expression，不依赖 raw SQL string。当前只真实实现 SQLite；PostgreSQL 和 MySQL 仅保留 DatabaseBackend 扩展边界。天气、RAG、Planner、Aggregator 和 Multi-Agent 不属于 Batch 2，尚未实现。
