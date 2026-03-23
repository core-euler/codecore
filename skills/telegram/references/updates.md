# Telegram Update Flow

Model update handling as deterministic state transitions.
Validate callback payloads and command arguments before mutating chat state.
Assume duplicate or delayed updates can happen.
