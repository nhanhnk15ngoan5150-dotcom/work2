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


class FastRouter:
    """Deterministic short-path router for the Batch 2 business domain."""

    def route(self, question: str) -> EvidenceDomain | None:
        normalized = question.strip()
        if any(keyword in normalized for keyword in BUSINESS_KEYWORDS):
            return EvidenceDomain.BUSINESS_DATA
        return None
