# AGENTS.md

## Purpose

This repository contains a Home Assistant configuration with `configuration.yaml` as the primary configuration entrypoint.

The goal of an agent working here is to make small, correct, task-scoped changes that respect Home Assistant conventions, preserve valid YAML, and avoid any unnecessary risk.

## Core rules

- Keep changes strictly within the requested scope.
- Do not refactor, reorganize, rename, or clean up unrelated parts of the configuration unless explicitly asked.
- Preserve existing structure and style unless the task requires a targeted change.
- If a task reveals a repo-specific convention that should be preserved in future work, update this `AGENTS.md` as part of the task.

## Git and file safety

- Never commit, stage, push, rebase, merge, or otherwise create or modify git history unless explicitly asked.
- Only tracked files are safe to edit by default.
- Before editing any file, verify whether it is tracked by git.
- If a file is not tracked, clearly say that it is outside the safe-to-edit set and ask for explicit approval before editing it.
- This rule also applies to `secrets.yaml`.
- Agents may create new files when they are useful, clearly in scope, and can be written in one complete pass.
- Before creating a new file, check whether it would be tracked under the current `.gitignore` rules.
- If the new file would not be tracked, first check whether `.gitignore` can be adjusted safely and without undesirable side effects so the file can become tracked.
- Agents are allowed to change `.gitignore` for that purpose.
- This repository follows an `.gitignore` strategy that excludes everything not explicitly included. Be careful with negation/include rules and avoid broad patterns that accidentally expose files that should remain untracked.
- After creating a new file, do not edit that file again until the user has committed it.

## Home Assistant rules

- Treat `configuration.yaml` as the main source of truth for static configuration in this repository.
- Keep YAML valid for Home Assistant.
- Use valid Home Assistant YAML structure, indentation, keys, and list formats.
- Do not invent configuration patterns that do not match Home Assistant requirements.
- Prefer minimal, localized edits over broad rewrites.
- Do not move configuration into packages, split files, or other structural patterns unless explicitly asked.
- When changing automations, scripts, sensors, helpers, or integrations, preserve surrounding behavior unless the task explicitly requires behavioral changes.
- When a task is in scope for an automation, add missing notes or correct inaccurate notes on relevant automation steps when doing so improves clarity and can be done without expanding scope.
- When a task is in scope for a script, add missing notes or correct inaccurate notes where the relevant script editor or configuration supports them.
- Treat automation and script notes as task-scoped documentation: update them when the current task touches that logic, but do not sweep unrelated automations or scripts just to add notes.

## Secrets

- Never inline secrets, tokens, passwords, API keys, or similar sensitive values into `configuration.yaml` or other tracked files.
- Use `secrets.yaml` when a Home Assistant secret reference is appropriate.
- If editing `secrets.yaml` is necessary, first check whether it is tracked.
- If `secrets.yaml` is not tracked, clearly warn the user and ask for explicit approval before editing it.
- Do not replace an existing `!secret` reference with a literal sensitive value.

## Validation

- After changing Home Assistant YAML, validate the configuration when a project-specific validation command is documented or already established in the repository.
- If no validation command is documented, say so explicitly.
- Do not guess the runtime environment.
- Ask before assuming an environment-specific validation command such as `ha core check` or `hass --script check_config`.
- If validation cannot be run, state that clearly in the final task summary.

## MCP usage

- An MCP server is available: `https://github.com/homeassistant-ai/ha-mcp`.
- Prefer MCP when the task depends on live Home Assistant state, entity inspection, service behavior, device details, areas, runtime context, or other information that cannot be safely inferred from repository files alone.
- Do not use MCP when the task is purely a static edit that can be completed safely from version-controlled files.
- Use MCP to reduce guessing, not to expand scope.

## Change style

- Make the smallest change that fully solves the requested task.
- Keep comments and additions concise.
- Do not introduce new dependencies, tools, or structural conventions unless they are required for the task.
- Flag uncertainty early instead of making assumptions about the live system or the intended behavior.

## Task summaries

- Clearly state which files were changed.
- Clearly state whether validation was run.
- Clearly state whether any requested change was blocked by the tracked-file policy or by missing approval.
- Clearly state whether `AGENTS.md` was updated.