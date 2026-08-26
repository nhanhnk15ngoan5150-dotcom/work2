from datetime import date
from typing import cast

from langgraph.graph import END, START, StateGraph

from app.contracts.evidence import Evidence, EvidenceDomain, EvidenceType
from app.contracts.state import AgentState
from app.domains.business.models import (
    BusinessIntent,
    ResolvedTimeRange,
    TimeRangeMode,
)
from app.domains.business.product_service import ProductService
from app.domains.business.sales_service import SalesService
from app.domains.business.store_service import StoreService
from app.domains.business.time_service import MONTH_MAP, TimeRangeService


def _period_dates(time_range: ResolvedTimeRange) -> tuple[date, date] | None:
    if time_range.mode in {TimeRangeMode.ALL, TimeRangeMode.MONTH}:
        if time_range.start_date is not None and time_range.end_date is not None:
            return time_range.start_date, time_range.end_date
    if time_range.mode is TimeRangeMode.COMPARE:
        if time_range.current_start is not None and time_range.current_end is not None:
            return time_range.current_start, time_range.current_end
    return None


def _period_label(start_date: date, end_date: date) -> str:
    if start_date.day == 1 and end_date.day == 1:
        return f"{start_date.year}年{start_date.month}月"
    return f"{start_date.isoformat()} 至 {end_date.isoformat()}"


class BusinessDataWorkflow:
    """Single-domain LangGraph workflow for deterministic business queries."""

    def __init__(
        self,
        time_service: TimeRangeService,
        sales_service: SalesService,
        store_service: StoreService,
        product_service: ProductService,
    ) -> None:
        self._time_service = time_service
        self._sales_service = sales_service
        self._store_service = store_service
        self._product_service = product_service

        graph = StateGraph(AgentState)
        graph.add_node("analyze_question", self._analyze_question)
        graph.add_node("query_business_data", self._query_business_data)
        graph.add_node("format_answer", self._format_answer)
        graph.add_edge(START, "analyze_question")
        graph.add_edge("analyze_question", "query_business_data")
        graph.add_edge("query_business_data", "format_answer")
        graph.add_edge("format_answer", END)
        self._graph = graph.compile()

    @property
    def domain(self) -> EvidenceDomain:
        return EvidenceDomain.BUSINESS_DATA

    async def execute(self, state: AgentState) -> AgentState:
        return cast(AgentState, await self._graph.ainvoke(state))

    async def run(self, state: AgentState) -> AgentState:
        """Compatibility wrapper for the frozen Batch 2 interface."""
        return await self.execute(state)

    # 1. 识别经营意图和实体
    def _analyze_question(self, state: AgentState) -> dict:
        question = state["question"].strip()
        product_name = self._product_service.find_in_question(question)
        time_expression = self._extract_time_expression(question)

        if "门店" in question:
            intent = BusinessIntent.STORE_RANKING
        elif product_name is not None or "商品" in question or "销量" in question:
            intent = (
                BusinessIntent.PRODUCT_RANKING
                if "排行" in question or "排名" in question
                else BusinessIntent.PRODUCT_PERFORMANCE
            )
        elif any(keyword in question for keyword in ("营业额", "销售额", "订单", "客单价")):
            intent = (
                BusinessIntent.SALES_COMPARISON
                if time_expression == "最近"
                and any(keyword in question for keyword in ("变化", "对比", "环比"))
                else BusinessIntent.SALES_SUMMARY
            )
        else:
            intent = BusinessIntent.UNKNOWN

        return {
            "normalized_question": question.replace(" ", ""),
            "trace_metadata": {
                "business_intent": intent.value,
                "time_expression": time_expression,
                "product_name": product_name,
            },
        }

    # 2. 查询经营数据并转换为 Evidence
    def _query_business_data(self, state: AgentState) -> dict:
        trace = state["trace_metadata"]
        intent = BusinessIntent(str(trace["business_intent"]))
        time_expression = cast(str | None, trace.get("time_expression"))
        time_range = self._time_service.resolve(time_expression)
        updated_trace = dict(trace)
        updated_trace["time_range"] = time_range.model_dump(
            mode="json",
            exclude_none=True,
        )

        if time_range.mode is TimeRangeMode.OUT_OF_RANGE:
            return {
                "trace_metadata": updated_trace,
                "warnings": ["查询时间超出当前经营数据范围"],
            }
        if time_range.mode is TimeRangeMode.INSUFFICIENT_DATA:
            return {
                "trace_metadata": updated_trace,
                "warnings": ["经营数据不足，无法比较最近两个完整月份"],
            }

        if intent is BusinessIntent.SALES_COMPARISON:
            return self._query_sales_comparison(state, time_range, updated_trace)

        period = _period_dates(time_range)
        if period is None:
            return {
                "trace_metadata": updated_trace,
                "warnings": ["无法确定经营数据查询时间"],
            }
        start_date, end_date = period

        if intent is BusinessIntent.SALES_SUMMARY:
            summary = self._sales_service.get_summary(start_date, end_date)
            if summary is None:
                return {"warnings": ["指定时间没有经营数据"]}
            evidence = Evidence(
                tenant_id=state["tenant_id"],
                domain=EvidenceDomain.BUSINESS_DATA,
                evidence_type=EvidenceType.FACT,
                claim=f"{_period_label(start_date, end_date)}经营核心指标",
                value=summary.model_dump(mode="json"),
                source_type="database",
                source_id=f"sales-summary:{start_date}:{end_date}",
                sample_size=summary.order_count,
            )
        elif intent is BusinessIntent.STORE_RANKING:
            ranking = self._store_service.get_ranking(start_date, end_date)
            top_store = next((item for item in ranking if item.total_sales > 0), None)
            if top_store is None:
                return {"warnings": ["指定时间没有门店经营数据"]}
            evidence = Evidence(
                tenant_id=state["tenant_id"],
                domain=EvidenceDomain.BUSINESS_DATA,
                evidence_type=EvidenceType.FACT,
                claim=f"{_period_label(start_date, end_date)}营业额最高门店",
                value=top_store.model_dump(mode="json"),
                unit="CNY",
                source_type="database",
                source_id=f"store-ranking:{start_date}:{end_date}",
                sample_size=len(ranking),
            )
        elif intent is BusinessIntent.PRODUCT_RANKING:
            ranking = self._product_service.get_ranking(start_date, end_date)
            if not ranking:
                return {"warnings": ["指定时间没有商品经营数据"]}
            evidence = Evidence(
                tenant_id=state["tenant_id"],
                domain=EvidenceDomain.BUSINESS_DATA,
                evidence_type=EvidenceType.FACT,
                claim=f"{_period_label(start_date, end_date)}商品销售排行榜第一名",
                value=ranking[0].model_dump(mode="json"),
                source_type="database",
                source_id=f"product-ranking:{start_date}:{end_date}",
                sample_size=len(ranking),
            )
        elif intent is BusinessIntent.PRODUCT_PERFORMANCE:
            product_name = cast(str | None, trace.get("product_name"))
            if product_name is None:
                return {"warnings": ["未识别需要查询的商品名称"]}
            performance = self._product_service.get_performance(
                product_name,
                start_date,
                end_date,
            )
            if performance is None:
                return {"warnings": ["指定时间没有该商品经营数据"]}
            evidence = Evidence(
                tenant_id=state["tenant_id"],
                domain=EvidenceDomain.BUSINESS_DATA,
                evidence_type=EvidenceType.FACT,
                claim=f"{_period_label(start_date, end_date)}{product_name}经营表现",
                value=performance.model_dump(mode="json"),
                source_type="database",
                source_id=f"product:{product_name}:{start_date}:{end_date}",
            )
        else:
            return {"warnings": ["暂不支持该经营数据问题"]}

        return {
            "trace_metadata": updated_trace,
            "evidence": [evidence],
        }

    def _query_sales_comparison(
        self,
        state: AgentState,
        time_range: ResolvedTimeRange,
        trace: dict,
    ) -> dict:
        comparison = self._sales_service.compare(time_range)
        if comparison is None:
            return {
                "trace_metadata": trace,
                "warnings": ["经营数据不足，无法比较最近两个完整月份"],
            }
        evidence = Evidence(
            tenant_id=state["tenant_id"],
            domain=EvidenceDomain.BUSINESS_DATA,
            evidence_type=EvidenceType.FACT,
            claim="最近两个完整月份经营指标对比",
            value=comparison.model_dump(mode="json"),
            source_type="database",
            source_id="sales-comparison:recent",
            sample_size=comparison.current.order_count + comparison.previous.order_count,
        )
        return {"trace_metadata": trace, "evidence": [evidence]}

    # 3. 使用 Evidence 生成确定性回答
    def _format_answer(self, state: AgentState) -> dict:
        if not state["evidence"]:
            message = state["warnings"][0] if state["warnings"] else "没有查询到经营数据"
            return {"final_answer": message}

        evidence = state["evidence"][0]
        value = cast(dict, evidence.value)
        intent = BusinessIntent(str(state["trace_metadata"]["business_intent"]))
        question = state["normalized_question"]

        if intent is BusinessIntent.SALES_SUMMARY:
            start_date = date.fromisoformat(str(value["start_date"]))
            end_date = date.fromisoformat(str(value["end_date"]))
            label = _period_label(start_date, end_date)
            if "订单" in question:
                answer = f"{label}订单量为 {value['order_count']} 单。"
            elif "客单价" in question:
                answer = f"{label}客单价为 {value['avg_order_value']:.2f} 元。"
            else:
                answer = f"{label}营业额为 {value['total_sales']:.2f} 元。"
        elif intent is BusinessIntent.SALES_COMPARISON:
            answer = (
                f"最近完整月营业额为 {value['current']['total_sales']:.2f} 元，"
                f"较上月变化 {value['sales_change_rate']:.2f}%。"
            )
        elif intent is BusinessIntent.STORE_RANKING:
            answer = (
                f"表现最好的门店是 {value['store_name']}，"
                f"营业额为 {value['total_sales']:.2f} 元。"
            )
        elif intent is BusinessIntent.PRODUCT_RANKING:
            answer = (
                f"销售额最高的商品是 {value['product_name']}，"
                f"销售额为 {value['total_sales']:.2f} 元。"
            )
        else:
            metric = "销量" if "销量" in question or "多少份" in question else "销售额"
            metric_value = (
                f"{value['total_quantity']} 份"
                if metric == "销量"
                else f"{value['total_sales']:.2f} 元"
            )
            answer = f"{value['product_name']}{metric}为 {metric_value}。"

        return {"final_answer": answer}

    @staticmethod
    def _extract_time_expression(question: str) -> str | None:
        if "最近" in question:
            return "最近"
        for expression in sorted(MONTH_MAP, key=len, reverse=True):
            if expression in question:
                return expression
        return None
