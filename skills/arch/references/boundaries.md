# Boundary Review

Check whether responsibilities are split across domain, orchestration, and infrastructure.
Prefer contract edges that are stable under provider or runtime changes.
If one module reaches through another to grab internal state, treat that as a boundary smell.
