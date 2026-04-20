"""Static command help text and metadata."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CommandSpec:
    name: str
    usage: str
    description: str


COMMAND_SPECS: tuple[CommandSpec, ...] = (
    CommandSpec("add", "/add <file...>", "Add files to active context"),
    CommandSpec("ap", '/ap "traceback/details" | /ap list | /ap search <query>', "Track repeated execution antipatterns"),
    CommandSpec("apply", "/apply", "Turn the last user request into a structured code edit on active files"),
    CommandSpec("approvals", "/approvals", "Show pending approval requests"),
    CommandSpec("approve", "/approve <id|latest|1|2>", "Approve a pending risky command or allow its action type"),
    CommandSpec(
        "autoedit",
        "/autoedit [--verify] <instruction>",
        "Ask the active model for structured edits",
    ),
    CommandSpec("benchmark", "/benchmark [--models a,b] [--pipeline <id>] [--verify] <instruction>", "Run the same multi-agent task against multiple model aliases and compare outcomes"),
    CommandSpec("clear", "/clear", "Clear active files and model pin"),
    CommandSpec("complete", "/complete <phase-name>", "Create a result marker for a completed phase and reindex knowledge"),
    CommandSpec("ctx", "/ctx <show|edit|trim|clear|save|load>", "Inspect, edit, trim, and snapshot transcript context"),
    CommandSpec("delegate", "/delegate [--pipeline <id>] [--verify] [--apply] <instruction>", "Run a multi-agent pipeline and optionally request apply-back to the main workspace"),
    CommandSpec("deps", "/deps", "Compare project dependencies against latest PyPI versions"),
    CommandSpec("diff", "/diff [paths]", "Show git status and diff for the workspace or active files"),
    CommandSpec("dismiss", "/dismiss <id|latest|3>", "Dismiss a pending approval request"),
    CommandSpec("docs", "/docs <package>", "Resolve the latest package version and documentation URL"),
    CommandSpec("drop", "/drop <file...>", "Remove files from active context"),
    CommandSpec("exit", "/exit", "End the session"),
    CommandSpec("help", "/help", "Show this help"),
    CommandSpec("issue", '/issue "description" | /issue list | /issue close <id> [resolution]', "Track logical and architectural issues"),
    CommandSpec("kb", "/kb <init|add|index|show|edit|lookup>", "Manage and query the markdown knowledge base under docs/"),
    CommandSpec("mcp", "/mcp <list|status|add|disable|enable>", "Inspect and manage configured MCP servers"),
    CommandSpec("model", "/model <alias>", "Pin a model alias for the session"),
    CommandSpec("pin", "/pin <file...>", "Alias for /add"),
    CommandSpec("ping", "/ping", "Refresh provider health snapshot"),
    CommandSpec("pipelines", "/pipelines", "Show known agent pipelines and the active selection"),
    CommandSpec("proofs", "/proofs", "Show proof records gathered in this session"),
    CommandSpec("rate", "/rate <1-5>", "Rate the last response"),
    CommandSpec("replace", "/replace [--verify] <path> <old> <new>", "Replace one exact text match in a workspace file"),
    CommandSpec("retry", "/retry", "Retry the last failed /run or /verify command"),
    CommandSpec("rollback", "/rollback [path|latest]", "Restore the latest snapshot-backed patch without git"),
    CommandSpec("run", "/run [--verify] <command>", "Run a shell command through policy/approval gates"),
    CommandSpec("search", "/search <query>", "Run a lightweight web search"),
    CommandSpec("skill", "/skill <list|load|edit|new|clear|name>", "List, pin, edit, or create skills"),
    CommandSpec("stats", "/stats", "Show telemetry and memory analytics"),
    CommandSpec("status", "/status", "Show current runtime status"),
    CommandSpec("tag", "/tag [type]", "Show or change the task tag"),
    CommandSpec("undo", "/undo [paths]", "Restore tracked files from HEAD when available"),
    CommandSpec("unpin", "/unpin <file...>", "Alias for /drop"),
    CommandSpec("verify", "/verify [command]", "Run verification using default or explicit test command"),
)


HELP_TEXT = "Available commands:\n" + "\n".join(
    f"  {spec.usage:<34} {spec.description}" for spec in COMMAND_SPECS
) + (
    "\n\nInput:\n"
    "  Enter submits the prompt\n"
    "  Ctrl+J inserts a newline\n"
    "  Type `/` to open command completion and move with arrow keys\n"
    "  Use `/ctx edit` to rewrite transcript context in $EDITOR\n"
    "  If CodeCore offers to start implementation, press `1` or use `/apply`\n"
)
