import { type APIRequestContext, type Page, expect } from '@playwright/test';

const BASE = new URL(process.env.E2E_BASE_URL ?? 'http://localhost:8200');

/** Collects what would make a reviewer frown: console errors, page errors (CSP violations land here) and third-party calls. */
export function watch(page: Page, { allowStatus = [] as number[] } = {}): string[] {
  const problems: string[] = [];
  page.on('pageerror', (e) => problems.push(`pageerror: ${e.message}`));
  page.on('console', (m) => {
    if (m.type() !== 'error' && m.type() !== 'warning') return;
    // Chromium logs every non-2xx fetch as an error. Allow only the statuses a test provokes on purpose.
    const status = /status of (\d{3})/.exec(m.text());
    if (status && allowStatus.includes(Number(status[1]))) return;
    problems.push(`console ${m.type()}: ${m.text()}`);
  });
  page.on('request', (r) => {
    const url = new URL(r.url());
    if (url.protocol !== 'data:' && url.protocol !== 'blob:' && url.host !== BASE.host) {
      problems.push(`third-party request: ${r.url()}`);
    }
  });
  return problems;
}

export async function leaveSplash(page: Page): Promise<void> {
  await expect(page.locator('#splash')).toHaveCount(0, { timeout: 10_000 });
}

/** Open the lab on a tab and wait until it is there. There is no sign-in: the lab is a local tool. */
export async function openLab(page: Page, name: string): Promise<void> {
  await page.goto(`/lab.html#${name.toLowerCase()}`);
  await leaveSplash(page);
  await expect(page.getByRole('tab', { name })).toHaveAttribute('aria-selected', 'true');
}

export const tab = (page: Page, name: string) => page.getByRole('tab', { name });

/** The tab panel that is open. Panels that were visited and left stay in the page, hidden, so every locator starts here. */
export const active = (page: Page) => page.locator('[role="tabpanel"]:not([hidden])');

/** The decision cards in the open tab, newest first. */
export const cards = (page: Page) => active(page).locator('.box.arrive');

/** The list item whose bold name is exactly `name` (a guard called "no-secrets" must not match a longer title). */
export const named = (page: Page, name: string) =>
  active(page)
    .getByRole('listitem')
    .filter({ has: page.locator('strong', { hasText: new RegExp(`^${name}$`) }) });

/** A box of the open tab, found by the start of its heading ("1 · git-guard"). */
export const section = (page: Page, heading: string) =>
  active(page).locator('section.box').filter({ has: page.locator('h3', { hasText: heading }) });

/** Put the sample back to the template: no break, no authorization line. */
export async function resetLab(request: APIRequestContext): Promise<void> {
  const res = await request.post('/api/lab/reset', { data: {} });
  expect(res.ok(), `resetting the lab answered ${res.status()}`).toBeTruthy();
}
