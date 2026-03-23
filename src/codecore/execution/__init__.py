"""Execution primitives."""

from .audit import FileChangeAudit, FileChangeRecord
from .approvals import ApprovalManager, ApprovalRequest
from .files import FileSnapshot, WorkspaceFiles
from .git import GitWorkspace
from .patches import PatchApplication, PatchService
from .shell import ShellToolExecutor, summarize_output
from .sandbox import SandboxProfile
from .tests import VerificationPlan, VerificationPlanner, VerificationRunner

__all__ = [
    "ApprovalManager",
    "ApprovalRequest",
    "FileChangeAudit",
    "FileChangeRecord",
    "FileSnapshot",
    "GitWorkspace",
    "PatchApplication",
    "PatchService",
    "SandboxProfile",
    "ShellToolExecutor",
    "VerificationPlan",
    "VerificationPlanner",
    "VerificationRunner",
    "WorkspaceFiles",
    "summarize_output",
]
