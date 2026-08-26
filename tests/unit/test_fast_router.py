from app.contracts.evidence import EvidenceDomain
from app.routing.fast_router import FastRouter


def test_fast_router_selects_business_data_short_path() -> None:
    assert (
        FastRouter().route("7月份营业额是多少？")
        is EvidenceDomain.BUSINESS_DATA
    )


def test_fast_router_rejects_unimplemented_domain() -> None:
    assert (
        FastRouter().route("明天天气怎么样？")
        is EvidenceDomain.EXTERNAL_FACTOR
    )


def test_fast_router_returns_structured_multi_domain_decision() -> None:
    decision = FastRouter().decide("明天下雨会不会影响营业额？")

    assert decision.is_multi_domain is True
    assert decision.domain is None
    assert decision.selected_domains == [
        EvidenceDomain.BUSINESS_DATA,
        EvidenceDomain.EXTERNAL_FACTOR,
    ]


def test_fast_router_selects_knowledge_operation() -> None:
    assert (
        FastRouter().route("会员折扣和满减可以同时使用吗？")
        is EvidenceDomain.KNOWLEDGE_OPERATION
    )
