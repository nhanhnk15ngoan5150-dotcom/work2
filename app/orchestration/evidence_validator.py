from pydantic import ValidationError

from app.contracts.evidence import Evidence
from app.contracts.orchestration import (
    DomainExecutionResult,
    EvidenceValidationResult,
    ExecutionPlan,
)


class EvidenceValidator:
    # 1. 校验并行分支提交的 Evidence 边界
    def validate(
        self,
        *,
        tenant_id: str,
        plan: ExecutionPlan,
        domain_results: list[DomainExecutionResult],
    ) -> EvidenceValidationResult:
        planned_domains = set(plan.selected_domains)
        validated: list[Evidence] = []
        errors: list[str] = []

        for domain_result in domain_results:
            for evidence in domain_result.evidence:
                if evidence.tenant_id != tenant_id:
                    errors.append(
                        f"EVIDENCE_TENANT_MISMATCH:{domain_result.domain.value}"
                    )
                    continue
                if evidence.domain not in planned_domains:
                    errors.append(f"EVIDENCE_DOMAIN_NOT_PLANNED:{evidence.domain.value}")
                    continue
                if evidence.domain is not domain_result.domain:
                    errors.append(
                        f"EVIDENCE_BRANCH_DOMAIN_MISMATCH:{domain_result.domain.value}"
                    )
                    continue
                try:
                    validated.append(
                        Evidence.model_validate(evidence.model_dump(mode="python"))
                    )
                except ValidationError:
                    errors.append(
                        f"EVIDENCE_CONTRACT_INVALID:{domain_result.domain.value}"
                    )

        return EvidenceValidationResult(evidence=validated, errors=errors)
