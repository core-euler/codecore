"""Static command help text and metadata."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CommandSpec:
    name: str
    usage: str
    description: str


COMMAND_SPECS: tuple[CommandSpec, ...] = (
    CommandSpec("help", "/help", "Show this help"),
    CommandSpec("status", "/status", "Show current runtime status"),
    CommandSpec("stats", "/stats", "Show telemetry and memory analytics"),
    CommandSpec("run", "/run [--verify] <command>", "Run a shell command through policy/approval gates"),
    CommandSpec("apply", "/apply", "Turn the last user request into a structured code edit on active files"),
    CommandSpec(
        "delegate",
        "/delegate [--pipeline <id>] [--verify] [--apply] <instruction>",
        "Run a multi-agent pipeline and optionally request apply-back to the main workspace",
    ),
    CommandSpec(
        "benchmark",
        "/benchmark [--models a,b] [--pipeline <id>] [--verify] <instruction>",
        "Run the same multi-agent task against multiple model aliases and compare outcomes",
    ),
    CommandSpec("pipelines", "/pipelines", "Show known agent pipelines and the active selection"),
    CommandSpec("autoedit", "/autoedit [--verify] <instruction>", "Ask the active model for structured edits"),
    CommandSpec("replace", "/replace [--verify] <path> <old> <new>", "Replace one exact text match in a workspace file"),
    CommandSpec("rollback", "/rollback [path|latest]", "Restore the latest snapshot-backed patch without git"),
    CommandSpec("retry", "/retry", "Retry the last failed /run or /verify command"),
    CommandSpec("approvals", "/approvals", "Show pending approval requests"),
    CommandSpec("approve", "/approve <id|latest|1|2>", "Approve a pending risky command or allow its action type"),
    CommandSpec("dismiss", "/dismiss <id|latest|3>", "Dismiss a pending approval request"),
    CommandSpec("verify", "/verify [command]", "Run verification using default or explicit test command"),
    CommandSpec("diff", "/diff [paths]", "Show git status and diff for the workspace or active files"),
    CommandSpec("undo", "/undo [paths]", "Restore tracked files from HEAD when available"),
    CommandSpec("model", "/model <alias>", "Pin a model alias for the session"),
    CommandSpec("skill", "/skill [name]", "Show, pin, or unpin skills"),
    CommandSpec("tag", "/tag [type]", "Show or change the task tag"),
    CommandSpec("rate", "/rate <1-5>", "Rate the last response"),
    CommandSpec("ping", "/ping", "Refresh provider health snapshot"),
    CommandSpec("add", "/add <file...>", "Add files to active context"),
    CommandSpec("drop", "/drop <file...>", "Remove files from active context"),
    CommandSpec("pin", "/pin <file...>", "Alias for /add"),
    CommandSpec("unpin", "/unpin <file...>", "Alias for /drop"),
    CommandSpec("clear", "/clear", "Clear active files and model pin"),
    CommandSpec("exit", "/exit", "End the session"),
)


HELP_TEXT = "Available commands:\n" + "\n".join(
    f"  {spec.usage:<34} {spec.description}" for spec in COMMAND_SPECS
) + (
    "\n\nInput:\n"
    "  Enter submits the prompt\n"
    "  Ctrl+J inserts a newline\n"
    "  Type `/` to open command completion and move with arrow keys\n"
    "  If CodeCore offers to start implementation, press `1` or use `/apply`\n"
)
