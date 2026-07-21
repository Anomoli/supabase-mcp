# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is an npm-workspaces monorepo containing MCP (Model Context Protocol) servers for Supabase:

- `packages/mcp-server-supabase` — the main MCP server (`@supabase/mcp-server-supabase`). Connects AI assistants to the Supabase Management API for managing projects, executing SQL, deploying edge functions, branching, etc.
- `packages/mcp-server-postgrest` — MCP server that proxies a PostgREST API (`@supabase/mcp-server-postgrest`), translating SQL to REST via `@supabase/sql-to-rest`.
- `packages/mcp-utils` — shared library (`@supabase/mcp-utils`) with `createMcpServer`, `tool`, resource helpers, and `StreamTransport` built on top of `@modelcontextprotocol/sdk`.

Requires the latest LTS version of Node.js and npm.

## Commands

```shell
# Install (--ignore-scripts is required; libpg-query's postinstall fails on recent macOS)
npm install --ignore-scripts

# Build all packages (mcp-utils must build before mcp-server-supabase; the root script handles order)
npm run build

# Run all tests (from root, runs mcp-utils + mcp-server-supabase)
npm test

# Tests with coverage (what CI runs; coverage output in packages/mcp-server-supabase/test/coverage)
npm run test:coverage
```

Within `packages/mcp-server-supabase`, tests are split into vitest workspace projects:

```shell
npm run test:unit         # src/**/*.test.ts (unit tests, mocked via MSW + PGlite)
npm run test:integration  # test/**/*.integration.ts (spawns the built stdio binary — run `npm run build` and `npm rebuild` first to create bin links)
npm run test:e2e          # test/**/*.e2e.ts (LLM tests using @ai-sdk/anthropic; requires ANTHROPIC_API_KEY)

# Single test file / single test
npx vitest src/password.test.ts
npx vitest -t 'test name'
```

Test setup (`vitest.setup.ts`) loads `.env.local` when not in CI — a missing `.env.local` throws, so create the file (e.g. with `ANTHROPIC_API_KEY`) before running tests locally.

Regenerate Management API types (in `packages/mcp-server-supabase`):

```shell
npm run generate:management-api-types  # openapi-typescript from https://api.supabase.com/api/v1-json
```

## Architecture

### mcp-server-supabase

- `src/stdio.ts` — CLI entry point (`bin`). Parses `--access-token`, `--project-ref`, `--read-only`, `--api-url` flags and connects the server over stdio. Access token can also come from `SUPABASE_ACCESS_TOKEN`.
- `src/server.ts` — `createSupabaseMcpServer()`. Composes tool groups from `src/tools/*.ts` (project management, database operations, edge functions, debugging, development, branching). Account-level tools (project management) are excluded when `--project-ref` scopes the server to one project.
- `src/management-api/` — typed `openapi-fetch` client for the Supabase Management API. `types.ts` is generated (do not hand-edit; regenerate from the OpenAPI spec). Use `assertSuccess(response, fallbackMessage)` after every call.
- `src/tools/util.ts` — `injectableTool()`: a tool wrapper that can statically inject parameters (e.g. `project_id` when scoped) and remove them from the exposed schema. All project-level tools use this so they work in both scoped and unscoped modes.
- `src/pg-meta/` — raw `.sql` files (imported as text via a tsup/vitest `.sql` loader; typed in `src/types/sql.d.ts`) plus zod schemas for describing tables, columns, and extensions.
- All SQL execution flows through the Management API `POST /v1/projects/{ref}/database/query` endpoint; `--read-only` is enforced server-side by passing `read_only: true` to that endpoint (applies only to `execute_sql` and `apply_migration`).
- Migrations vs queries: `apply_migration` is for DDL/schema changes (tracked in the database); `execute_sql` is for untracked, regular queries.
- Edge function deployment bundles files with eszip (`src/eszip.ts`, `@deno/eszip`).

### Testing approach

- HTTP calls to the Management API are mocked with MSW (`test/mocks.ts`), and the Postgres database is emulated in-process with PGlite, so unit tests hit no real network or database.
- `test/llm.e2e.ts` wires an in-memory MCP client/server pair using `StreamTransport` from mcp-utils and drives it with a real Anthropic model via the `ai` SDK.
- `test/stdio.integration.ts` spawns the actual built binary, so it depends on `dist/` and npm bin links.

### mcp-utils

Defines the shared server abstraction: tools are declared as `{ description, parameters (zod schema), execute }` objects and converted to JSON schema via `zod-to-json-schema`. Resources use `resource()`/`resourceTemplate()` helpers with URI template matching. `StreamTransport` provides an in-memory duplex transport, mainly for tests.

### Repo-level `supabase/` directory

A standard Supabase local-development project (config.toml, migrations, seed) used as a fixture/playground, not part of the published packages.

## Conventions

- ESM-only source (`"type": "module"`) with `.js` extensions on relative imports (TypeScript `NodeNext`-style). Builds via tsup output both ESM and CJS.
- Zod schemas define all tool parameters; parameter descriptions are attached with `.describe()`.
- The server is pre-1.0: breaking changes to tools are acceptable and expected between versions.
- Prettier is the formatter (per-package devDependency, no shared config file).
- CI (`.github/workflows/tests.yml`) runs `npm ci --ignore-scripts`, builds, `npm rebuild` (to create bin links for integration tests), then `npm run test:coverage` and uploads to Coveralls.
