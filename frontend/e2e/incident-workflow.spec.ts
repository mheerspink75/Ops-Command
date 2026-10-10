import { test, expect } from '@playwright/test'

/**
 * End-to-end coverage of the core incident-response workflow (spec §13):
 *
 *   1. Sign in.
 *   2. Declare an incident.
 *   3. Attach an impacted service.
 *   4. Assign an incident commander.
 *   5. Add a timeline update.
 *   6. Run a playbook.
 *   7. Observe progress.
 *   8. Resolve the incident.
 *   9. Generate a post-incident report.
 *
 * These tests drive the real frontend against the real backend. The full stack
 * (Postgres, Redis, backend API, Celery worker) must be running; the frontend
 * dev server is started by Playwright's `webServer` config.
 *
 * Demonstration credentials are intentionally non-production and are created by
 * the seed command (`make seed`). See docs/testing.md.
 */

const API_BASE = process.env.E2E_API_BASE_URL || 'http://localhost:8000'
const EMAIL = 'owner@acme-ops.io'
const PASSWORD = 'Demo-Password-123!'

/** Log in via the API and return the authenticated user's id (a valid org member). */
async function getUserId(request: import('@playwright/test').APIRequestContext): Promise<string> {
  const loginResp = await request.post(`${API_BASE}/api/v1/auth/login`, {
    data: { email: EMAIL, password: PASSWORD },
  })
  expect(loginResp.ok(), `login should succeed, got ${loginResp.status()}`).toBeTruthy()
  const { access_token } = await loginResp.json()
  const meResp = await request.get(`${API_BASE}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${access_token}` },
  })
  expect(meResp.ok()).toBeTruthy()
  const me = await meResp.json()
  return me.id as string
}

test.describe('Incident response workflow', () => {
  test('sign in → declare → attach service → assign IC → timeline → playbook → progress → resolve → report', async ({
    page,
    request,
  }) => {
    const userId = await getUserId(request)

    // 1. Sign in.
    await page.goto('/login')
    await page.fill('#email', EMAIL)
    await page.fill('#password', PASSWORD)
    await page.locator('button[type="submit"]').click()
    await page.waitForURL('/')
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()

    // 2. Declare an incident.
    const title = `E2E incident ${Date.now()}`
    await page.goto('/incidents')
    await page.getByRole('button', { name: /Declare incident/ }).click()
    const dialog = page.getByRole('dialog', { name: 'Create new incident' })
    await dialog.locator('#ni-title').fill(title)
    await dialog.locator('#ni-summary').fill('Automated end-to-end incident.')
    await dialog.locator('#ni-severity').selectOption('SEV2')

    // 3. Attach an impacted service (select the first available service).
    const serviceLabel = dialog.locator('label:has(input[type="checkbox"])').first()
    const serviceText = (await serviceLabel.textContent())?.trim() ?? ''
    const serviceName = serviceText.replace(/\(.*\)/, '').trim()
    await serviceLabel.click()

    await dialog.getByRole('button', { name: 'Declare incident' }).click()
    await page.waitForURL(/\/incidents\/[0-9a-f-]+/)
    await expect(page.getByRole('heading', { name: title })).toBeVisible()

    // 3 (verify). The impacted service is attached and shown on the detail page.
    await expect(page.getByText('Affected Services')).toBeVisible()
    await expect(page.getByText(serviceName, { exact: true })).toBeVisible()

    // 4. Assign an incident commander.
    await page.locator('input[placeholder="User ID"]').fill(userId)
    await page.locator('input[placeholder="Role (e.g. IC)"]').fill('commander')
    await page.getByRole('button', { name: 'Assign' }).click()
    await expect(page.getByText('commander', { exact: true })).toBeVisible()

    // 5. Add a timeline update.
    const timelineCard = page.locator('.card', { has: page.getByRole('heading', { name: 'Timeline' }) })
    const timelineMessage = `E2E timeline update ${Date.now()}`
    await timelineCard.locator('input[placeholder="Add timeline event…"]').fill(timelineMessage)
    await timelineCard.getByRole('button', { name: 'Add' }).click()
    await expect(page.getByText(timelineMessage)).toBeVisible()

    // 6. Run a playbook.
    const playbooksCard = page.locator('.card', { has: page.getByRole('heading', { name: 'Playbooks' }) })
    await playbooksCard.locator('select').selectOption({ label: 'Standard escalation' })
    await playbooksCard.getByRole('button', { name: 'Run Playbook' }).click()

    // 7. Observe progress (the worker executes the run; poll until it succeeds).
    await expect(page.getByText('Status: succeeded')).toBeVisible({ timeout: 30_000 })

    // 8. Resolve the incident (advance the status until it reaches "resolved").
    // The playbook may have already advanced the status, so reload to sync UI state.
    await page.reload()
    await expect(page.getByRole('heading', { name: title })).toBeVisible()
    for (let i = 0; i < 6; i++) {
      if (await page.getByRole('status', { name: 'Status: Resolved' }).isVisible()) break
      const nextBtn = page.getByRole('button', { name: /→$/ })
      if ((await nextBtn.count()) === 0) break
      const btnText = (await nextBtn.textContent())?.trim() ?? ''
      const target = btnText.replace('→', '').trim()
      const label = target.charAt(0).toUpperCase() + target.slice(1)
      // Skip if the status is already at the target (e.g. playbook advanced it).
      if (await page.getByRole('status', { name: `Status: ${label}` }).isVisible()) continue
      await nextBtn.click()
      await expect(page.getByRole('status', { name: `Status: ${label}` })).toBeVisible({ timeout: 10_000 })
    }
    await expect(page.getByRole('status', { name: 'Status: Resolved' })).toBeVisible()

    // 9. Generate a post-incident report (download the markdown report).
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: 'Export Report' }).click(),
    ])
    expect(download.suggestedFilename()).toMatch(/report\.md$/)
  })

  test('shows an error when sign in fails', async ({ page }) => {
    await page.goto('/login')
    await page.fill('#email', 'nobody@acme-ops.io')
    await page.fill('#password', 'wrong-password')
    await page.locator('button[type="submit"]').click()
    await expect(page.getByRole('alert')).toBeVisible()
    // Still on the login page.
    await expect(page).toHaveURL(/\/login/)
  })
})
