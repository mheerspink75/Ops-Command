import { request } from '@playwright/test'

/**
 * Global setup: fail fast with an actionable message if the backend is not
 * reachable. The e2e suite requires the full stack (Postgres, Redis, backend
 * API, Celery worker) to be running. The frontend dev server is started by
 * Playwright's `webServer` config, so only the backend is verified here.
 */
export default async function globalSetup() {
  const apiBase = process.env.E2E_API_BASE_URL || 'http://localhost:8000'

  let ctx
  try {
    ctx = await request.newContext()
    const resp = await ctx.get(`${apiBase}/health`, { timeout: 5000 })
    if (!resp.ok()) {
      throw new Error(`backend returned HTTP ${resp.status()}`)
    }
  } catch (err) {
    throw new Error(
      `Backend is not reachable at ${apiBase}/health. ` +
        `Start the full stack before running e2e tests: ` +
        `Postgres + Redis (docker compose up -d postgres redis), ` +
        `the backend API (uvicorn app.main:app --port 8000), and ` +
        `the Celery worker (celery -A app.worker.broker:celery_app worker). ` +
        `See docs/testing.md for the exact commands. ` +
        `(${(err as Error).message})`,
    )
  } finally {
    await ctx?.dispose()
  }
}
