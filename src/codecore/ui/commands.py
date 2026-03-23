"""Static command help text."""

HELP_TEXT = """Available commands:
  /help              Show this help
  /status            Show current runtime status
  /stats             Show telemetry and memory analytics
  /run [--verify] <command> Run a shell command through policy/approval gates
  /apply             Turn the last user request into a structured code edit on active files
  /delegate [--pipeline <id>] [--verify] [--apply] <instruction>
                    Run a multi-agent pipeline and optionally request apply-back to the main workspace
  /benchmark [--models a,b] [--pipeline <id>] [--verify] <instruction>
                    Run the same multi-agent task against multiple model aliases and compare outcomes
  /pipelines         Show known agent pipelines and the active selection
  /autoedit [--verify] <instruction>
                    Ask the active model for structured edits on active files
  /replace [--verify] <path> <old> <new>
                    Replace one exact text match in a workspace file
  /rollback [path|latest]
                    Restore the latest snapshot-backed patch without git
  /retry            Retry the last failed /run or /verify command
  /approvals        Show pending approval requests
  /approve <id|latest|1|2>
                    Approve a pending risky command once, or allow its action type for this session
  /dismiss <id|latest|3>
                    Dismiss a pending approval request
  /verify [command]  Run verification using default or explicit test command
  /diff [paths]      Show git status and diff for the workspace or active files
  /undo [paths]      Restore tracked files from HEAD when available
  /model <alias>     Pin a model alias for the session
  /skill [name]      Show, pin, or unpin skills
  /tag [type]        Show or change the task tag
  /rate <1-5>        Rate the last response
  /ping              Refresh provider health snapshot
  /add <file...>     Add files to active context
  /drop <file...>    Remove files from active context
  /pin <file...>     Alias for /add
  /unpin <file...>   Alias for /drop
  /clear             Clear active files and model pin
  /exit              End the session

Input:
  Enter submits the prompt
  Ctrl+J inserts a newline
  If CodeCore offers to start implementation, press `1` or use `/apply`
"""
