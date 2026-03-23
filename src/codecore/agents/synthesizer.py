"""Final reporting for multi-agent workflow results."""

from __future__ import annotations

from .models import WorkflowResult


class SynthesizerAgent:
    def summarize(self, result: WorkflowResult) -> str:
        lines = [
            f"pipeline={result.pipeline_id}",
            f"classification={result.classification.complexity} ({result.classification.reason})",
            f"workspace={result.workspace_path or '<main>'}",
            f"review_workspace={result.review_workspace_path or '<same>'}",
            f"isolation={'enabled' if result.isolated else 'disabled'}",
            f"retries={result.retry_count}",
            f"merge_ready={'yes' if result.merge_ready else 'no'}",
            f"edits={result.coding.edit_count}",
            f"applied_files={', '.join(result.coding.applied_files) if result.coding.applied_files else '<none>'}",
        ]
        if result.plan.steps:
            lines.append("plan:")
            lines.extend(f"  {index}. {step.title} - {step.detail}" for index, step in enumerate(result.plan.steps, start=1))
        if result.evaluation is not None:
            lines.append(f"evaluation={result.evaluation.status}")
            lines.append("evaluation_summary:\n" + result.evaluation.summary)
        if result.review is not None:
            lines.append(f"review={'approved' if result.review.approved else 'rejected'}")
            lines.append(f"review_summary={result.review.summary}")
            for finding in result.review.findings:
                lines.append(f"finding[{finding.severity}]={finding.message}")
        lines.append("diff:\n" + result.coding.diff_summary)
        return "\n".join(lines)
