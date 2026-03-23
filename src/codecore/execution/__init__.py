"""Execution primitives."""

from .audit import FileChangeAudit, FileChangeRecord
from .approvals import ApprovalManager, ApprovalRequest
from .changesets import ChangeSet, ChangeSetApplier, ChangeSetApplyResult, ChangeSetBuilder, ChangeSetEntry
from .editing import EditOperation, EditPlan, StructuredEditParser
from .files import FileSnapshot, WorkspaceFiles
from .git import GitWorkspace
from .native_tools import NativeRepositoryTools, NativeToolCall
from .patches import PatchApplication, PatchService
from .shell import ShellToolExecutor, summarize_output
from .sandbox import SandboxProfile
from .tests import VerificationPlan, VerificationPlanner, VerificationRunner
from .worktrees import WorktreeHandle, WorktreeManager

__all__ = [
    "ApprovalManager",
    "ApprovalRequest",
    "ChangeSet",
    "ChangeSetApplier",
    "ChangeSetApplyResult",
    "ChangeSetBuilder",
    "ChangeSetEntry",
    "EditOperation",
    "EditPlan",
    "FileChangeAudit",
    "FileChangeRecord",
    "FileSnapshot",
    "GitWorkspace",
    "NativeRepositoryTools",
    "NativeToolCall",
    "PatchApplication",
    "PatchService",
    "SandboxProfile",
    "ShellToolExecutor",
    "StructuredEditParser",
    "VerificationPlan",
    "VerificationPlanner",
    "VerificationRunner",
    "WorktreeHandle",
    "WorktreeManager",
    "WorkspaceFiles",
    "summarize_output",
]
