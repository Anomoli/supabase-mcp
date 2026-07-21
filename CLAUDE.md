# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is the **Supabase MCP Server** monorepo — it implements [Model Context Protocol](https://modelcontextprotocol.io) (MCP) servers that connect AI assistants (Cursor, Claude, Windsurf, etc.) to Supabase. The servers are published to npm and executed by MCP clients via `npx`.

It is an npm-workspaces monorepo with three packages under `packages/`:

| Package | npm name | Purpose |
| --- | --- | --- |
| `packages/mcp-server-supabase` | `@supabase/mcp-server-supabase` | The main MCP server. Exposes tools for managing Supabase projects (database, migrations, edge functions, branching, logs, etc.) via the Supabase Management API. |
| `packages/mcp-server-postgrest` | `@supabase/mcp-server-postgrest` | A secondary MCP server for querying any PostgREST endpoint (`postgrestRequest`, `sqlToRest` tools). |
| `packages/mcp-utils` | `@supabase/mcp-utils` | Shared MCP utilities: the `createMcpServer` wrapper, `tool`/`resource` helpers, and an in-memory `StreamTransport`. Used by both servers. |

The `supabase/` directory at the root is a local Supabase project (config, `todos` migrations, seed data) used as a development/test fixture, not part of the published packages.

Note: these packages are pre-1.0 — breaking changes between versions are acceptable and expected.

## Commands

Requires the latest LTS version of Node.js and npm.

```shell
# Install (from repo root). --ignore-scripts is required: the transient
# libpg-query dependency fails to build its native scripts on recent macOS.
npm install --ignore-scripts

# Build all publishable packages (mcp-utils + mcp-server-supabase, via tsup)
npm run build

# After building, recreate bin links so integration tests can spawn the CLI via npx
npm rebuild

# Run tests for mcp-utils + mcp-server-supabase
npm test

# Run tests with coverage (what CI runs)
npm run test:coverage
```

Within `packages/mcp-server-supabase/`, tests are split into three vitest workspace projects (see `vitest.workspace.ts`):

```shell
npm run test:unit          # src/**/*.test.ts — pure unit tests, no external services
npm run test:e2e           # test/**/*.e2e.ts — drives the server with a real LLM (needs ANTHROPIC_API_KEY)
npm run test:integration   # test/**/*.integration.ts — spawns the built CLI via npx (build + npm rebuild first)

# Run a single test file
npx vitest run src/server.test.ts

# Run tests matching a name
npx vitest run -t "list_tables"
```

Testing environment notes:

- `vitest.setup.ts` loads `.env.local` from the package directory when not on CI and **fails if the file does not exist** — create `packages/mcp-server-supabase/.env.local` (it can be empty; add `ANTHROPIC_API_KEY=...` to run the LLM e2e tests).
- Unit and e2e tests do **not** hit real Supabase: the Management API is fully mocked with `msw` (see `test/mocks.ts`), and SQL sent to the mocked query endpoint is executed against an in-memory Postgres via `@electric-sql/pglite`.
- Default test timeout is 30s (PGlite startup is slow); e2e tests get 60s.

Other useful commands:

```shell
# Regenerate typed Management API client types from the live OpenAPI spec
# (run inside packages/mcp-server-supabase)
npm run generate:management-api-types

# Check the CLI version / run the server locally
npx tsx packages/mcp-server-supabase/src/stdio.ts --access-token=<pat>
```

CI (`.github/workflows/tests.yml`) runs: `npm ci --ignore-scripts` → `npm run build` → `npm rebuild` → `npm run test:coverage`, then uploads coverage to Coveralls (base path `packages/mcp-server-supabase`).

## Architecture

### How a tool call flows (mcp-server-supabase)

1. **`src/stdio.ts`** — CLI entrypoint (the package `bin`). Parses `--access-token`, `--project-ref`, `--read-only`, `--api-url` flags (or `SUPABASE_ACCESS_TOKEN` env var) and connects the server over stdio.
2. **`src/server.ts`** — `createSupabaseMcpServer()` assembles the server. On MCP `initialize` it creates the Management API client (embedding the client name/version in the `User-Agent`). Tools are gathered from category modules in `src/tools/`:
   - `project-management-tools.ts` — account-level tools (list/create/pause/restore projects, orgs, costs). **Omitted entirely when `--project-ref` is set** (project-scoped mode).
   - `database-operation-tools.ts` — `list_tables`, `list_extensions`, `list_migrations`, `apply_migration`, `execute_sql`.
   - `edge-function-tools.ts`, `debugging-tools.ts` (logs), `development-tools.ts` (project URL, anon key, TypeScript type generation), `branching-tools.ts`.
3. **`src/management-api/`** — a typed `openapi-fetch` client. `types.ts` is **generated** from the Supabase Management API OpenAPI spec (`npm run generate:management-api-types`) — do not hand-edit it. Use `assertSuccess(response, message)` after each call.
4. All database access goes through the Management API's `/v1/projects/{ref}/database/query` endpoint — the server never connects to Postgres directly.

### Key patterns and conventions

- **`injectableTool`** (`src/tools/util.ts`): every project-level tool declares a `project_id` parameter, but wraps itself with `inject: { project_id }`. When the server is scoped via `--project-ref`, the parameter is removed from the tool's schema and injected statically; otherwise the LLM must supply it. Follow this pattern for any new project-level tool.
- **Read-only mode**: `--read-only` is enforced by passing `read_only: true` to the database query endpoint (executes SQL as a read-only Postgres user). It only applies to `execute_sql` / `apply_migration`, not to Management API operations.
- **Raw SQL as modules**: `src/pg-meta/` contains `.sql` files (borrowed pg-meta introspection queries) imported as strings. Both `tsup.config.ts` and `vitest.config.ts` register a small `sql-loader` plugin to make `import sql from './tables.sql'` work — keep them in sync if you touch either config.
- **Edge functions & eszip**: deployed edge functions are stored as eszip archives. `src/eszip.ts` bundles/extracts them (recovering original TypeScript via source maps), and `src/edge-function.ts` computes deployment IDs and the `/tmp/user_fn_<deploymentId>/` path prefix used to normalize file paths. Use posix path helpers (`node:path/posix`) here — a past bug broke path parsing on Windows.
- **Cost confirmation**: creating projects or branches requires the LLM to call `get_cost` then `confirm_cost` first; the confirmation ID is a required parameter of `create_project` / `create_branch`.
- **Zod everywhere**: tool parameters and API response shapes are validated with zod schemas (e.g. `src/pg-meta/types.ts` parses rows returned by introspection SQL).
- **Text templates**: multi-line SQL/prompt strings use `codeBlock` from `common-tags`.

### mcp-utils

`createMcpServer({ name, version, onInitialize, tools, resources })` wraps the raw `@modelcontextprotocol/sdk` `Server`, converting zod parameter schemas to JSON schema, validating incoming arguments, and serializing results. `StreamTransport` provides an in-memory duplex transport — this is how tests connect a client and server directly without stdio (pipe two transports' readable/writable streams into each other; see `test/llm.e2e.ts` for the pattern).

Changes to `mcp-utils` affect both servers. Note that `mcp-server-supabase` depends on a **published version** of `@supabase/mcp-utils` (pinned, e.g. `0.2.0`), while `mcp-server-postgrest` uses `*` — within the workspace npm links the local copy, but version bumps to mcp-utils must be published before dependent packages can be released.

### Build output

All packages build with `tsup` to dual ESM/CJS (`dist/index.js` + `dist/index.cjs`) plus type declarations. Server packages additionally emit `dist/stdio.js` with a shebang as the CLI `bin`. Source is ESM TypeScript (`"type": "module"`) using the `@total-typescript/tsconfig` strict config — **relative imports must use `.js` extensions** (e.g. `import { x } from './util.js'`).

## Workflow conventions

- Commit messages follow Conventional Commits (`fix:`, `feat:`, `docs:`, `chore:`), as seen in the git history; PRs merge into `main`.
- Formatting is Prettier (default config); match existing style.
- When adding, removing, or renaming tools in `mcp-server-supabase`, update the tools list in the root `README.md` — it documents every tool by category.
- `docs/production.md` documents the recommended development-branch → merge-to-production workflow built on the branching tools; keep it consistent with branching tool behavior.
