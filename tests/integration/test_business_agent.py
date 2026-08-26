from fastapi.testclient import TestClient


def test_sales_question_runs_complete_business_data_chain(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/agent/query",
        json={"question": "7月份营业额是多少？"},
        headers={"X-Request-ID": "sales-demo"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["request_id"] == "sales-demo"
    assert payload["tenant_id"] == "dev_tenant"
    assert payload["route"] == "BUSINESS_DATA"
    assert payload["answer"] == "2026年7月营业额为 151572.00 元。"
    assert payload["evidence"][0]["value"]["total_sales"] == 151572.0
    assert payload["evidence"][0]["confidence"] is None
    assert payload["evidence"][0]["evidence_type"] == "FACT"


def test_store_question_returns_verified_top_store(client: TestClient) -> None:
    response = client.post(
        "/api/v1/agent/query",
        json={"question": "最近哪个门店表现最好？"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == (
        "表现最好的门店是 Super Tetsudo，营业额为 32301.00 元。"
    )
    assert payload["evidence"][0]["value"]["store_id"] == "S05"
    assert payload["evidence"][0]["value"]["total_sales"] == 32301.0


def test_product_question_returns_verified_quantity(client: TestClient) -> None:
    response = client.post(
        "/api/v1/agent/query",
        json={"question": "六月可乐销量怎么样？"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "可乐销量为 310 份。"
    assert payload["evidence"][0]["value"]["total_sales"] == 1550.0
    assert payload["evidence"][0]["value"]["total_quantity"] == 310


def test_recent_sales_comparison_uses_july_and_june(client: TestClient) -> None:
    response = client.post(
        "/api/v1/agent/query",
        json={"question": "最近营业额变化怎么样？"},
    )

    assert response.status_code == 200
    value = response.json()["evidence"][0]["value"]
    assert value["current"]["total_sales"] == 151572.0
    assert value["previous"]["total_sales"] == 132820.0
    assert value["sales_change_rate"] == 14.12


def test_out_of_range_question_returns_no_evidence(client: TestClient) -> None:
    response = client.post(
        "/api/v1/agent/query",
        json={"question": "四月份营业额是多少？"},
    )

    assert response.status_code == 200
    assert response.json()["evidence"] == []
    assert response.json()["warnings"] == ["查询时间超出当前经营数据范围"]


def test_client_cannot_supply_tenant_identity(client: TestClient) -> None:
    response = client.post(
        "/api/v1/agent/query",
        json={"question": "7月份营业额是多少？", "tenant_id": "other_tenant"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_unimplemented_domain_stops_at_fast_router(client: TestClient) -> None:
    response = client.post(
        "/api/v1/agent/query",
        json={"question": "明天天气怎么样？"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNSUPPORTED_QUERY"
