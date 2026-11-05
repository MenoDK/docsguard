import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';
import { leaveSplash, watch } from './helpers';

test.describe('landing page', () => {
  test('shows the loading stage, then the page, without a single console problem or third-party request', async ({
    page,
  }) => {
    const problems = watch(page);
    await page.goto('/?lang=en');
    await expect(page.locator('#splash')).toBeVisible();
    await leaveSplash(page);
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Documentation that');
    await expect(page.getByRole('link', { name: /Open the lab/ }).first()).toBeVisible();
    expect(problems).toEqual([]);
  });

  test('the tour tabs swap in recorded output that really came from the tool', async ({ page }) => {
    await page.goto('/?lang=en');
    await leaveSplash(page);
    const tabs = page.getByRole('group', { name: 'Explore the product' });
    const output = page.getByRole('region', { name: 'Example output' });

    await tabs.getByRole('button', { name: /Map/ }).click();
    await expect(output).toContainText('docs/runbook.md');
    await expect(output).toContainText("links to 'PLAN.md', which does not exist");
    await expect(output).toContainText('FAILED: 2 problem(s)');

    await tabs.getByRole('button', { name: /Shape/ }).click();
    await expect(output).toContainText("has no '## Rejected alternatives' section");
    await expect(output).toContainText("section 'suite state' carries no number");
    await expect(output).toContainText("description does not say 'Use when");

    await tabs.getByRole('button', { name: /Budget/ }).click();
    await expect(output).toContainText('Session start: paid on every session');
    await expect(output).toContainText('286 lines exceeds the per-file cap of 200');

    await tabs.getByRole('button', { name: /Secrets/ }).click();
    await expect(output).toContainText('looks like an AWS access key id (value not shown)');
    await expect(output).toContainText('"vacuous": false');

    await tabs.getByRole('button', { name: /Hooks/ }).click();
    // a transcript inserted as HTML would swallow anything that looks like a tag
    await expect(output).toContainText('docsguard:reset-hard');
    await expect(output).toContainText('docsguard:protected-path');
    await expect(output).toContainText('`path:.env -- <why>`');
    await expect(output).toContainText('the tool call goes ahead');
    await expect(tabs.getByRole('button', { name: /Hooks/ })).toHaveAttribute('aria-pressed', 'true');
  });

  test('no recorded output contains anything shaped like a secret, and the pasted key is not in it', async ({
    page,
  }) => {
    await page.goto('/?lang=en');
    const text = await page.evaluate(() => JSON.stringify((window as unknown as { TRANSCRIPTS: object }).TRANSCRIPTS));
    expect(text).not.toMatch(/AKIA[0-9A-Z]{16}|-----BEGIN|gh[pousr]_[A-Za-z0-9]{20}|Bearer [A-Za-z0-9]{12}/);
    expect(text).not.toContain('QZ7K3WP9');
  });

  test('every hard part offers a recipe and a link that opens the lab on that tab', async ({ page }) => {
    await page.goto('/?lang=en#hard-parts');
    await leaveSplash(page);
    const list = page.getByRole('group', { name: 'Hard parts to try' });
    const names = [
      'Lose a document',
      'Cut a link',
      'Skip the measurement',
      'Let the instructions grow',
      'Paste a key',
      'Ask a hook to destroy work',
      'Write where you must not',
    ];
    for (const name of names) {
      await list.getByRole('button', { name }).click();
      await expect(page.getByText('You should see', { exact: true })).toBeVisible();
      await expect(page.getByRole('link', { name: 'Try it in the lab' })).toHaveAttribute('href', /lab\.html(#\w+)?$/);
    }
  });

  test('the theme switch is applied, remembered across reloads, and nothing leaves the page', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'light' });
    await page.goto('/?lang=en');
    await leaveSplash(page);
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
    await page.getByRole('button', { name: 'Use the dark theme' }).click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
    await page.reload();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  });

  test('works with reduced motion and still reveals every section', async ({ browser }) => {
    const context = await browser.newContext({ reducedMotion: 'reduce' });
    const page = await context.newPage();
    await page.goto('/?lang=en');
    await leaveSplash(page);
    await page.locator('#faq').scrollIntoViewIfNeeded();
    await expect(page.getByRole('heading', { name: /Asked often/ })).toBeVisible();
    await context.close();
  });

  test('has no horizontal scroll on a phone', async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 360, height: 740 } });
    const page = await context.newPage();
    await page.goto('/?lang=en');
    await leaveSplash(page);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
    await context.close();
  });

  test('the hero artwork keeps every label inside its frame and inside its own box', async ({ page }) => {
    await page.goto('/?lang=en');
    await leaveSplash(page);
    const outside = await page.evaluate(() => {
      const frame = document.querySelector('.hero-art svg');
      if (!frame) return ['no artwork'];
      const box = frame.getBoundingClientRect();
      const bad: string[] = [];
      for (const t of frame.querySelectorAll('text')) {
        const r = t.getBoundingClientRect();
        if (r.left < box.left - 1 || r.right > box.right + 1) bad.push(`${t.textContent} leaves the frame`);
        // the card or pill a label sits in: the smallest rect that contains the label's start
        const host = [...frame.querySelectorAll('rect')]
          .map((rect) => ({ rect, b: rect.getBoundingClientRect() }))
          .filter(({ b }) => b.left <= r.left + 2 && b.right >= r.left && b.top <= r.top + 2 && b.bottom >= r.bottom - 2)
          .sort((a, c) => a.b.width * a.b.height - c.b.width * c.b.height)[0];
        if (host && r.right > host.b.right + 1) bad.push(`${t.textContent} runs past the box it sits in`);
      }
      return bad;
    });
    expect(outside).toEqual([]);
  });
});

for (const scheme of ['light', 'dark'] as const) {
  test(`accessibility: the landing page has no WCAG A/AA violations (${scheme})`, async ({ browser }) => {
    const context = await browser.newContext({ colorScheme: scheme, reducedMotion: 'reduce' });
    const page = await context.newPage();
    await page.goto('/?lang=en');
    await leaveSplash(page);
    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
    expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(' | ')}`)).toEqual([]);
    await context.close();
  });
}
