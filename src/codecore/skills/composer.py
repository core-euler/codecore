"""Render resolved skills into a compact system-prompt block."""

from __future__ import annotations

from pathlib import Path

from ..context.token_budget import estimate_text_tokens
from ..domain.models import SkillDescriptor


class SkillPromptComposer:
    def compose(
        self,
        skills: tuple[SkillDescriptor, ...],
        budget_tokens: int,
        *,
        prompt: str = "",
        active_files: tuple[str, ...] = (),
    ) -> tuple[str, tuple[SkillDescriptor, ...]]:
        if budget_tokens <= 0 or not skills:
            return "", ()

        blocks: list[str] = []
        selected: list[SkillDescriptor] = []
        used_tokens = 0
        prompt_lower = prompt.lower()
        file_context = " ".join(active_files).lower()

        for skill in skills:
            block = self._render_skill(skill, compact=False)
            block_tokens = estimate_text_tokens(block)
            if used_tokens + block_tokens > budget_tokens:
                compact_block = self._render_skill(skill, compact=True)
                compact_tokens = estimate_text_tokens(compact_block)
                if selected and used_tokens + compact_tokens > budget_tokens:
                    continue
                if not selected and compact_tokens > budget_tokens:
                    continue
                block = compact_block
                block_tokens = compact_tokens

            reference_block = self._render_reference_block(
                skill,
                budget_tokens=max(0, budget_tokens - used_tokens - block_tokens),
                prompt_lower=prompt_lower,
                file_context=file_context,
            )
            reference_tokens = estimate_text_tokens(reference_block)
            if reference_block and used_tokens + block_tokens + reference_tokens > budget_tokens:
                reference_block = ""
                reference_tokens = 0

            rendered = block if not reference_block else block + "\n\n" + reference_block
            blocks.append(rendered)
            selected.append(skill)
            used_tokens += block_tokens + reference_tokens

        if not blocks:
            return "", ()
        return "Active skills:\n\n" + "\n\n".join(blocks), tuple(selected)

    def _render_skill(self, skill: SkillDescriptor, *, compact: bool) -> str:
        lines = [f"Skill: {skill.skill_id}", f"Purpose: {skill.description}"]
        if skill.summary:
            lines.append(f"Summary: {skill.summary}")
        if skill.constraints:
            lines.append("Constraints:")
            lines.extend(f"- {item}" for item in skill.constraints)
        if skill.reference_paths:
            refs = ", ".join(Path(path).name for path in skill.reference_paths)
            lines.append(f"References: {refs}")
        if compact:
            return "\n".join(lines)
        if skill.stop_conditions:
            lines.append("Stop conditions:")
            lines.extend(f"- {item}" for item in skill.stop_conditions)
        if skill.instructions:
            lines.append("Instructions:")
            lines.append(skill.instructions)
        return "\n".join(lines)

    def _render_reference_block(self, skill: SkillDescriptor, *, budget_tokens: int, prompt_lower: str, file_context: str) -> str:
        if budget_tokens <= 0 or not skill.reference_paths:
            return ""
        blocks: list[str] = []
        used_tokens = 0
        for reference_path in skill.reference_paths:
            stem = Path(reference_path).stem.replace("_", "-").lower()
            keywords = {stem, *stem.split("-")}
            if not any(keyword and (keyword in prompt_lower or keyword in file_context) for keyword in keywords):
                continue
            excerpt = self._reference_excerpt(Path(reference_path))
            if not excerpt:
                continue
            block = f"Reference excerpt: {Path(reference_path).name}\n{excerpt}"
            block_tokens = estimate_text_tokens(block)
            if used_tokens + block_tokens > budget_tokens:
                break
            blocks.append(block)
            used_tokens += block_tokens
        return "\n\n".join(blocks)

    def _reference_excerpt(self, path: Path, max_lines: int = 24) -> str:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            return ""
        return "\n".join(text.splitlines()[:max_lines])
