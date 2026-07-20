# Project Guidelines

## Architecture

This is a **Home Assistant configuration** repo with several custom subsystems. `configuration.yaml` is the primary entrypoint.

| Area | Description | Key Files |
|------|-------------|-----------|
| **PlayBee** | NFC-tag-driven music player (see [`playbee/docs.md`](./playbee/docs.md)) | `automations.yaml`, `scripts.yaml`, `custom_templates/`, `scripts/`, `esphome/` |
| **Custom integrations** | Third-party & local HA components (generally not git-tracked) | `custom_components/` |
| **ESPHome firmware** | NFC reader firmware (ESP8266 + PN532) | `esphome/playbee-tagreader*.yaml` |
| **Zigbee2MQTT** | Zigbee coordinator and device config | `zigbee2mqtt/configuration.yaml` |
| **Jinja templates** | Shared PlayBee helpers | `custom_templates/playbee.jinja`, `playbee_fn.jinja` |
| **Python scripts** | DB + queue management | `scripts/playbee_db.py`, `scripts/playbee_queue.py` |
| **Blueprints** | Reusable automations/scripts/templates | `blueprints/` |

Goal: make **small, correct, task-scoped changes** that respect HA conventions, preserve valid YAML, and avoid unnecessary risk.

---

## Code Style

### YAML & Home Assistant

- Follow patterns in `configuration.yaml`, `automations.yaml`, `scripts.yaml` — match their indentation, Jinja2 style, and action/condition ordering.
- Keep `mode:` explicit (`single` / `parallel` / `queued` / `restart`).
- Use `alias:` on every automation/script step for readable logs and traces.
- Add or correct `description:` / notes on steps your task touches. Do not sweep unrelated items.
- Prefer Jinja2 filters (`| default()`, `| trim`, `| int(0)`) over inline `{% if %}` blocks. Document non-obvious expressions with `{# #}` comments.
- Import shared macros from `custom_templates/` instead of duplicating logic.

---

## Build and Test

No project-specific validation command is currently established for this repo. Options (ask before assuming an environment):

- `hass --script check_config --config /config` — HA standalone config check
- `ha core check` — HA OS / Supervisor CLI
- `esphome config <file>` — ESPHome validation
- Zigbee2MQTT — per its own procedures

If validation cannot be run, state that clearly in the task summary.

---

## Conventions

### Git and file safety

- This repo uses a **deny-by-default** `.gitignore`: `*` at the top ignores everything; files are only tracked when explicitly allowed with `!` negation rules. Never add a broad pattern like `!*/**` that defeats this approach.
- Only git-tracked files are safe to edit by default. Verify before editing. If a file is not tracked, ask for explicit approval. This applies to `secrets.yaml` too.
- Agents may create new files when clearly in scope and writable in one pass. Before creating, check whether `.gitignore` covers it. Adjust `.gitignore` if needed (with care for the deny-by-default strategy).
- Do not commit, stage, push, rebase, or merge unless asked.
- After creating a new file, do not re-edit it until the user has committed it.

### Secrets

- Never inline secrets. Always use `!secret` references in `secrets.yaml`.
- Current known secrets: `playbee_ma_api_url`, `playbee_ma_token`, any Zigbee2MQTT credentials.

### PlayBee guardrails

PlayBee is the most complex subsystem — see [`playbee/docs.md`](./playbee/docs.md) for full architecture.

- **Database**: only access via `shell_command.playbee_db_*` wrappers. Never query SQLite directly from YAML.
- **Resume guard**: `input_text.playbee_active_tag_uid` prevents concurrent playback. Never clear it outside `playbee_stop_media` (the stale-tag-cleanup automation is the only exception — preserve the invariant).
- **MA API**: `rest_command.playbee_ma_*` calls use `!secret playbee_ma_token`. Never inline the token.
- **Consistency**: after editing a PlayBee script/automation, verify the corresponding `shell_command` and `rest_command` definitions still match.
- **Dev tag**: `04-3D-AA-EA-40-59-80` remaps `PlayBee - ` → `Dev - ` for testing. Be aware when debugging.

### MCP usage

An MCP server is available at `https://github.com/homeassistant-ai/ha-mcp`. Prefer it when the task depends on live HA state, entity inspection, or runtime context. Do not use it for purely static edits that can be completed from version-controlled files.

### Change style

- Keep changes scoped and minimal. One change per automation/script block.
- Do not refactor, reorganize, rename, or clean up unrelated configuration.
- When in doubt, reference existing PlayBee patterns in `automations.yaml` / `scripts.yaml`.
- Flag uncertainty early instead of guessing about the live system.

### Task summaries

After completing a task, report:
1. Which files were changed.
2. Whether validation was run (and the result).
3. Any change blocked by the tracked-file policy or missing approval.
4. Whether this `AGENTS.md` was updated.
