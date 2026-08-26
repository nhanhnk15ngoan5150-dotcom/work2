from app.contracts.evidence import EvidenceDomain
from app.routing.fast_router import FastRouter


def test_fast_router_selects_business_data_short_path() -> None:
    assert (
        FastRouter().route("7月份营业额是多少？")
        is EvidenceDomain.BUSINESS_DATA
    )


def test_fast_router_rejects_unimplemented_domain() -> None:
    assert FastRouter().route("明天天气怎么样？") is None
