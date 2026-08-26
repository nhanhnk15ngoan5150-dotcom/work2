from app.contracts.evidence import Evidence, EvidenceDomain, EvidenceType
from app.contracts.orchestration import (
    DomainExecutionResult,
    ExecutionMode,
    ExecutionPlan,
)
from app.orchestration.evidence_validator import EvidenceValidator


def _evidence(
    domain: EvidenceDomain,
    *,
    tenant_id: str = "dev_tenant",
) -> Evidence:
    return Evidence(
        tenant_id=tenant_id,
        domain=domain,
        evidence_type=EvidenceType.FACT,
        claim="Validated evidence",
        value={"metric": 100},
        source_type="test",
        source_id=f"test:{domain.value}",
    )


def _plan() -> ExecutionPlan:
    return ExecutionPlan(
        selected_domains=[
            EvidenceDomain.BUSINESS_DATA,
            EvidenceDomain.EXTERNAL_FACTOR,
        ],
        execution_mode=ExecutionMode.MULTI_DOMAIN,
    )


def test_validator_accepts_contract_valid_planned_tenant_evidence() -> None:
    evidence = _evidence(EvidenceDomain.BUSINESS_DATA)

    result = EvidenceValidator().validate(
        tenant_id="dev_tenant",
        plan=_plan(),
        domain_results=[
            DomainExecutionResult(
                domain=EvidenceDomain.BUSINESS_DATA,
                evidence=[evidence],
                success=True,
            )
        ],
    )

    assert result.evidence == [evidence]
    assert result.errors == []


def test_validator_rejects_wrong_tenant_and_unplanned_domain() -> None:
    result = EvidenceValidator().validate(
        tenant_id="dev_tenant",
        plan=_plan(),
        domain_results=[
            DomainExecutionResult(
                domain=EvidenceDomain.BUSINESS_DATA,
                evidence=[
                    _evidence(
                        EvidenceDomain.BUSINESS_DATA,
                        tenant_id="other_tenant",
                    )
                ],
                success=True,
            ),
            DomainExecutionResult(
                domain=EvidenceDomain.KNOWLEDGE_OPERATION,
                evidence=[_evidence(EvidenceDomain.KNOWLEDGE_OPERATION)],
                success=True,
            ),
        ],
    )

    assert result.evidence == []
    assert result.errors == [
        "EVIDENCE_TENANT_MISMATCH:BUSINESS_DATA",
        "EVIDENCE_DOMAIN_NOT_PLANNED:KNOWLEDGE_OPERATION",
    ]


def test_validator_rejects_branch_domain_mismatch_and_invalid_contract() -> None:
    invalid = Evidence.model_construct(
        evidence_id="invalid",
        tenant_id="dev_tenant",
        domain=EvidenceDomain.BUSINESS_DATA,
        evidence_type=EvidenceType.FACT,
        claim="",
        value=None,
        source_type="test",
        source_id="invalid",
        confidence=None,
        sample_size=None,
        warnings=[],
    )
    mismatch = _evidence(EvidenceDomain.EXTERNAL_FACTOR)

    result = EvidenceValidator().validate(
        tenant_id="dev_tenant",
        plan=_plan(),
        domain_results=[
            DomainExecutionResult(
                domain=EvidenceDomain.BUSINESS_DATA,
                evidence=[mismatch, invalid],
                success=True,
            )
        ],
    )

    assert result.evidence == []
    assert result.errors == [
        "EVIDENCE_BRANCH_DOMAIN_MISMATCH:BUSINESS_DATA",
        "EVIDENCE_CONTRACT_INVALID:BUSINESS_DATA",
    ]
