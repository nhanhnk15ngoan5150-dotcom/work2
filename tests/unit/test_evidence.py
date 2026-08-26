from datetime import timezone

import pytest
from pydantic import ValidationError

from app.contracts.evidence import Evidence, EvidenceDomain, EvidenceType


def test_evidence_contains_tenant_source_and_type() -> None:
    evidence = Evidence(
        tenant_id="dev_tenant",
        domain=EvidenceDomain.BUSINESS_DATA,
        evidence_type=EvidenceType.FACT,
        claim="Revenue is 100 yuan",
        value=100,
        unit="CNY",
        source_type="database",
        source_id="sales-query-1",
        confidence=1.0,
        sample_size=5,
    )

    assert evidence.tenant_id == "dev_tenant"
    assert evidence.evidence_type is EvidenceType.FACT
    assert evidence.created_at.tzinfo is timezone.utc


def test_evidence_allows_omitted_confidence() -> None:
    evidence = Evidence(
        tenant_id="dev_tenant",
        domain=EvidenceDomain.BUSINESS_DATA,
        evidence_type=EvidenceType.FACT,
        claim="Revenue is 100 yuan",
        value=100,
        source_type="database",
        source_id="sales-query-1",
    )

    assert evidence.confidence is None


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_evidence_rejects_invalid_confidence(confidence: float) -> None:
    with pytest.raises(ValidationError):
        Evidence(
            tenant_id="dev_tenant",
            domain=EvidenceDomain.EXTERNAL_FACTOR,
            evidence_type=EvidenceType.PREDICTION,
            claim="Rain is forecast",
            source_type="weather_api",
            source_id="forecast-1",
            confidence=confidence,
        )


def test_prediction_is_not_equal_to_fact() -> None:
    assert EvidenceType.PREDICTION != EvidenceType.FACT


@pytest.mark.parametrize(
    "value",
    [
        100,
        "rain",
        [1, "two", True, None],
        {"amount": 100, "tags": ["lunch", "weekday"]},
    ],
)
def test_evidence_accepts_json_safe_values(value) -> None:
    evidence = Evidence(
        tenant_id="dev_tenant",
        domain=EvidenceDomain.BUSINESS_DATA,
        evidence_type=EvidenceType.FACT,
        claim="JSON-safe value",
        value=value,
        source_type="database",
        source_id="query-1",
    )

    assert evidence.value == value
    evidence.model_dump_json()


def test_evidence_rejects_custom_object_value() -> None:
    class UnsafeValue:
        pass

    with pytest.raises(ValidationError):
        Evidence(
            tenant_id="dev_tenant",
            domain=EvidenceDomain.BUSINESS_DATA,
            evidence_type=EvidenceType.FACT,
            claim="Unsafe value",
            value=UnsafeValue(),
            source_type="database",
            source_id="query-1",
        )
