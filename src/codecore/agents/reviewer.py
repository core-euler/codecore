"""Reviewer heuristics for isolated coding results."""

from __future__ import annotations

from .models import EvaluationOutput, ReviewFinding, ReviewOutput


class ReviewerAgent:
    def review(
        self,
        *,
        diff_summary: str,
        evaluation: EvaluationOutput | None,
        applied_files: tuple[str, ...],
    ) -> ReviewOutput:
        findings: list[ReviewFinding] = []
        if not applied_files:
            findings.append(ReviewFinding(severity="high", message="Pipeline produced no file changes."))
        if not diff_summary.strip() or diff_summary.strip() == "Working tree is clean.":
            findings.append(ReviewFinding(severity="high", message="No diff was available for review."))
        if evaluation is not None and evaluation.status == "failed":
            findings.append(ReviewFinding(severity="high", message="Verification failed in the isolated workspace."))
        if evaluation is not None and evaluation.status == "skipped":
            findings.append(ReviewFinding(severity="medium", message="Verification was skipped; manual validation is still needed."))

        approved = not any(item.severity == "high" for item in findings)
        summary = "Review approved the isolated result." if approved else "Review rejected the isolated result."
        return ReviewOutput(approved=approved, summary=summary, findings=tuple(findings))
