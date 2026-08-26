from app.contracts.domains import RouteDecision
from app.contracts.evidence import EvidenceDomain

BUSINESS_KEYWORDS = (
    "营业额",
    "销售额",
    "订单",
    "客单价",
    "门店",
    "商品",
    "销量",
    "卖了",
)

EXTERNAL_FACTOR_KEYWORDS = (
    "天气",
    "下雨",
    "降雨",
    "温度",
)

KNOWLEDGE_OPERATION_KEYWORDS = (
    "会员",
    "折扣",
    "满减",
    "制度",
    "规则",
    "规范",
    "SOP",
)

DOMAIN_KEYWORDS = {
    EvidenceDomain.BUSINESS_DATA: BUSINESS_KEYWORDS,
    EvidenceDomain.EXTERNAL_FACTOR: EXTERNAL_FACTOR_KEYWORDS,
    EvidenceDomain.KNOWLEDGE_OPERATION: KNOWLEDGE_OPERATION_KEYWORDS,
}


class FastRouter:
    """Deterministic classifier for single-domain and multi-domain queries."""

    def decide(self, question: str) -> RouteDecision:
        normalized = question.strip()
        selected_domains = [
            domain
            for domain, keywords in DOMAIN_KEYWORDS.items()
            if any(keyword in normalized for keyword in keywords)
        ]
        return RouteDecision(selected_domains=selected_domains)

    def route(self, question: str) -> EvidenceDomain | None:
        """Compatibility wrapper for callers expecting a single domain."""
        return self.decide(question).domain
