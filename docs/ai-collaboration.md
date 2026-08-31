# AI-assisted development workflow

This file gives a coding assistant enough project context to make safe, reviewable changes.

## Roles

| Role | Responsibility | Required output |
| --- | --- | --- |
| Architect | Clarify scope and component boundaries before structural changes | Design note, affected configuration, risks |
| Developer | Implement the smallest coherent change | Code, tests, documentation updates |
| Test engineer | Test normal behavior and failure boundaries without physical hardware | Automated test result and any manual Pi checks |
| Reviewer | Check scope, Pi performance impact, Git hygiene, and deployment instructions | Concise review findings or approval |

One assistant may perform all roles, but should reason through them in this order for non-trivial work.

## Change protocol

1. Read `README.md`, `docs/architecture.md`, `AGENTS.md`, and the affected module.
2. Identify the component owner and avoid crossing boundaries without an explicit reason.
3. State what changes, which YAML keys are affected, how unavailable hardware behaves, and which automated tests cover it.
4. Implement with `uv`; do not manually edit `uv.lock`.
5. Run `uv lock --check`, `uv run ruff format --check .`, `uv run ruff check .`, and `uv run pytest`.
6. Update README when setup or operation changes; update `LOGBOOK.md` for material work.

## Ready-to-use task prompt

```text
Work on Asia Hornet Monitor V0.1. Read AGENTS.md and docs/architecture.md first.
Task: <describe one outcome>
Constraints: Keep camera capture, ROI motion detection, event writing, and web serving separate. Use uv only. Do not add classification/ML unless this task explicitly asks for it. Do not commit runtime data or local configuration.
Completion: Add focused tests, run uv lock --check, ruff format/check, pytest, and update LOGBOOK.md if the change is material. Report changed files, behavior, and verification.
```

## Hardware test checklist

Automated tests cannot verify the USB camera. On the Pi, verify:

- `/dev/video0` exists and the configured resolution/FPS is offered by `v4l2-ctl`.
- The browser loads `/`, `/status`, and `/stream.mjpg` from another device on the network.
- Motion outside the ROI does not create an event.
- Intended motion creates one date/time event directory with the configured burst count.
- Unplugging or blocking the camera produces a visible status error and does not terminate the web process.
