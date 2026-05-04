# Project Rules

## Commands
- Install: `pnpm install`
- Dev: `pnpm dev`
- Typecheck: `pnpm typecheck`
- Test: `pnpm test`
- Render smoke test: `pnpm video:smoke`

## Architecture
- Human editor and AI agent must use the same EDL/project JSON schema.
- All AI edits must be expressed as typed JSON.
- Rendering must be deterministic through Remotion and ffmpeg.
- Analysis artifacts live under `analysis/`.
- Render outputs live under `renders/`.
- Uploads are never executed.

## Review Requirements
- Schema changes require tests and migration notes.
- Video render changes require sample output and QA notes.
- Upload, file path, auth, webhook, and public endpoint changes require security review.

## Agent Rules
- Orchestrator routes. Specialists execute. Reviewer critiques. Fabric remembers.
- Video QA inspects before publish.
- GitHub enforces PR reviews.
