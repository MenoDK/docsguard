import AxeBuilder from '@axe-core/playwright';
import { type Page, expect, test } from '@playwright/test';
import { active, cards, named, openLab, resetLab, section, tab, watch } from './helpers';

const GUARDS = [
  'claude-entrypoint',
  'map-links-live',
  'map-complete',
  'map-counts',
  'adr-shape',
  'handoff-shape',
  'instruction-budget',
  'skill-shape',
  'no-secrets',
];

test.beforeEach(async ({ request }) => {
  await resetLab(request);
});

/** The button inside the break whose title is exactly `title`. */
const breakRow = (page: Page, title: string) => named(page, title);
const press = (page: Page, name: string) => active(page).getByRole('button', { name, exact: true }).first().click();

test.describe('lab: docs', () => {
  test('a fresh sample passes every guard, and the output under it is the real command line', async ({ page }) => {
    const problems = watch(page);
    await openLab(page, 'Docs');
    await expect(active(page)).toContainText('every guard passes');
    for (const guard of GUARDS) await expect(named(page, guard)).toContainText('ok');
    await expect(active(page).locator('pre.out')).toContainText('docsguard 0.1.0: /work/sample-shop');
    await expect(active(page).locator('pre.out')).toContainText('OK');
    await expect(active(page)).toContainText('CLAUDE.md'); // what init created
    expect(problems).toEqual([]);
  });

  test('a runbook nobody mapped fails map-complete and names it; putting it back is green again', async ({ page }) => {
    await openLab(page, 'Docs');
    await breakRow(page, 'Add a runbook and forget the map').getByRole('button', { name: 'Break it' }).click();
    await expect(named(page, 'map-complete')).toContainText('failed');
    await expect(named(page, 'map-complete')).toContainText('docs/runbook.md');
    await expect(named(page, 'map-links-live')).toContainText('ok');
    await expect(active(page)).toContainText('1 problem');
    await expect(active(page).locator('pre.out')).toContainText('FAILED: 1 problem(s)');
    await breakRow(page, 'Add a runbook and forget the map').getByRole('button', { name: 'Put it back' }).click();
    await expect(active(page)).toContainText('every guard passes');
  });

  test('a dead link in the map fails twice, because the checklist was only reachable through it', async ({ page }) => {
    await openLab(page, 'Docs');
    await breakRow(page, 'Point the map at a file that is gone').getByRole('button', { name: 'Break it' }).click();
    await expect(named(page, 'map-links-live')).toContainText("links to 'PLAN.md', which does not exist");
    await expect(named(page, 'map-complete')).toContainText('docs/CHECKLIST.md');
    await expect(active(page)).toContainText('2 problems');
  });

  test('a decision without its losers and a handoff without a number are both named', async ({ page }) => {
    await openLab(page, 'Docs');
    await breakRow(page, 'Write a decision without the alternatives that lost')
      .getByRole('button', { name: 'Break it' })
      .click();
    await breakRow(page, 'Report the suite state without a number').getByRole('button', { name: 'Break it' }).click();
    await expect(named(page, 'adr-shape')).toContainText("has no '## Rejected alternatives' section");
    await expect(named(page, 'handoff-shape')).toContainText('carries no number');
    await expect(active(page)).toContainText('2 problems');
  });

  test('a pasted key is reported by pattern and file, and the key itself is nowhere on the page', async ({ page }) => {
    await openLab(page, 'Docs');
    await breakRow(page, 'Paste a cloud access key into the handoff').getByRole('button', { name: 'Break it' }).click();
    await expect(named(page, 'no-secrets')).toContainText('AWS access key id');
    await expect(named(page, 'no-secrets')).toContainText('value not shown');
    expect(await page.content()).not.toMatch(/AKIA[0-9A-Z]{16}/);
    expect(await active(page).innerText()).not.toMatch(/AKIA[0-9A-Z]{16}/);
  });

  test('a dismissal that matches nothing is reported, so it cannot rot', async ({ page }) => {
    await openLab(page, 'Docs');
    await breakRow(page, 'Keep a dismissal for a file that no longer exists')
      .getByRole('button', { name: 'Break it' })
      .click();
    await expect(named(page, 'exemptions')).toContainText('matches nothing any more');
  });

  test('"Start over" puts every break back', async ({ page }) => {
    await openLab(page, 'Docs');
    await breakRow(page, 'Forget to point CLAUDE.md at the map').getByRole('button', { name: 'Break it' }).click();
    await expect(named(page, 'claude-entrypoint')).toContainText('failed');
    await page.getByRole('button', { name: 'Start over' }).click();
    await expect(page.getByText('Back to a clean sample.')).toBeVisible();
    await expect(active(page)).toContainText('every guard passes');
  });
});

test.describe('lab: hooks', () => {
  test('commands that destroy work are denied with a reason, also inside a wrapper, and ordinary ones are not', async ({
    page,
  }) => {
    await openLab(page, 'Hooks');
    await press(page, 'git reset --hard HEAD~3');
    await expect(cards(page).first()).toContainText('denied');
    await expect(cards(page).first()).toContainText('reset-hard');
    await expect(cards(page).first()).toContainText('discards uncommitted work for good');
    await expect(cards(page).first()).toContainText('"tool_name": "Bash"');
    await expect(cards(page).first()).toContainText('"permissionDecision": "deny"');

    await press(page, 'bash -c "git reset --hard"');
    await expect(cards(page).first()).toContainText('denied');

    await press(page, 'git status');
    await expect(cards(page).first()).toContainText('allowed');
    await expect(cards(page).first()).toContainText('the hook printed nothing');
    await expect(cards(page).first()).toContainText('(nothing)');
  });

  test('a command typed by hand is asked, never run', async ({ page, request }) => {
    await openLab(page, 'Hooks');
    await page.getByLabel('Or type a command').fill('git push --force origin main');
    await section(page, '1 · git-guard').getByRole('button', { name: 'Ask the hook' }).click();
    await expect(cards(page).first()).toContainText('denied');
    // and the sample is exactly as it was: nothing the lab was asked about touched it
    const check = await (await request.get('/api/check')).json();
    expect(check.ok).toBe(true);
  });

  test('a write to .env is denied, a line without a reason is ignored, a line with a reason lets it through', async ({
    page,
  }) => {
    await openLab(page, 'Hooks');
    await press(page, 'Write .env');
    await expect(cards(page).first()).toContainText('denied');
    await expect(cards(page).first()).toContainText('protected-path');
    await expect(cards(page).first()).toContainText('path:.env -- <why>');

    await press(page, 'Write the line without a reason');
    await expect(active(page)).toContainText('path:.env');
    await press(page, 'Write .env');
    await expect(cards(page).first()).toContainText('denied');
    await expect(cards(page).first()).toContainText('ignored because they give no reason');

    await press(page, 'Authorize .env with a reason');
    await expect(active(page)).toContainText('path:.env -- staging file, reviewed in the pull request');
    await press(page, 'Write .env');
    await expect(cards(page).first()).toContainText('allowed');

    await page.getByRole('button', { name: 'Start over' }).click();
    await expect(page.getByText('Back to a clean sample.')).toBeVisible();
    await expect(active(page)).toContainText('No authorization lines yet');
    await press(page, 'Write .env');
    await expect(cards(page).first()).toContainText('denied');
  });

  test('reads and ordinary writes are never blocked', async ({ page }) => {
    await openLab(page, 'Hooks');
    await press(page, 'Write src/app.py');
    await expect(cards(page).first()).toContainText('allowed');
    await press(page, 'Write .env.example');
    await expect(cards(page).first()).toContainText('allowed');
  });

  test('a path chosen by hand goes through the same hook', async ({ page }) => {
    await openLab(page, 'Hooks');
    await page.getByLabel('Or choose a tool').selectOption('Edit');
    await page.getByLabel('and a path (or, for Bash, a command)').fill('deploy/server.pem');
    await section(page, '2 · scope-guard').getByRole('button', { name: 'Ask the hook' }).click();
    await expect(cards(page).first()).toContainText('denied');
    await expect(cards(page).first()).toContainText('private keys and certificates');
  });
});

test.describe('lab: budget', () => {
  test('growing CLAUDE.md takes the session start over its budget, and the real output says so', async ({ page }) => {
    await openLab(page, 'Budget');
    await expect(active(page)).toContainText('within 6,000');
    await expect(active(page)).toContainText('~1,000 tokens');
    await expect(active(page).locator('pre.out')).toContainText('Session start: paid on every session');
    await press(page, 'Grow CLAUDE.md');
    await expect(active(page)).toContainText('over the budget of 6,000');
    await expect(active(page).locator('pre.out')).toContainText('286 lines');
    await press(page, 'Put it back');
    await expect(active(page)).toContainText('within 6,000');
  });

  test('the budget report keeps its columns: no line of it is wrapped in the middle', async ({ page }) => {
    await openLab(page, 'Budget');
    await press(page, 'Grow CLAUDE.md'); // the widest report: every figure has four digits
    await expect(active(page)).toContainText('over the budget of 6,000');
    const wrapped = await active(page)
      .locator('pre.out')
      .evaluate((pre) => {
        const style = getComputedStyle(pre);
        const lineHeight = Number.parseFloat(style.lineHeight);
        const padding = Number.parseFloat(style.paddingTop) + Number.parseFloat(style.paddingBottom);
        const lines = (pre.textContent ?? '').trimEnd().split('\n').length;
        return { white: style.whiteSpace, extra: Math.round((pre.scrollHeight - padding) / lineHeight) - lines };
      });
    expect(wrapped).toEqual({ white: 'pre', extra: 0 });
  });

  test('the same break shows up in the Docs tab as a failing guard', async ({ page }) => {
    await openLab(page, 'Budget');
    await press(page, 'Grow CLAUDE.md');
    await expect(active(page)).toContainText('over the budget');
    await tab(page, 'Docs').click();
    await expect(named(page, 'instruction-budget')).toContainText('failed');
    await expect(named(page, 'instruction-budget')).toContainText('286 lines exceeds the per-file cap of 200');
  });
});

test.describe('lab: the server in front of it', () => {
  test('a request that changes something must come from this origin', async ({ request }) => {
    const foreign = await request.post('/api/lab/reset', { data: {}, headers: { Origin: 'https://evil.example' } });
    expect(foreign.status()).toBe(403);
    const crossSite = await request.post('/api/lab/reset', { data: {}, headers: { 'Sec-Fetch-Site': 'cross-site' } });
    expect(crossSite.status()).toBe(403);
  });

  test('every page of the lab loads without a console problem or a third-party request', async ({ page }) => {
    const problems = watch(page);
    await openLab(page, 'Docs');
    await tab(page, 'Hooks').click();
    await expect(active(page)).toContainText('git-guard');
    await tab(page, 'Budget').click();
    await expect(active(page)).toContainText('What a session pays');
    expect(problems).toEqual([]);
  });
});

for (const scheme of ['light', 'dark'] as const) {
  for (const name of ['Docs', 'Hooks', 'Budget']) {
    test(`accessibility: the ${name} tab has no WCAG A/AA violations (${scheme})`, async ({ browser, request }) => {
      await resetLab(request);
      const context = await browser.newContext({ colorScheme: scheme, reducedMotion: 'reduce' });
      const page = await context.newPage();
      await openLab(page, name);
      if (name === 'Hooks') {
        await press(page, 'git reset --hard HEAD~3'); // a decision card is the part with the most markup
        await expect(cards(page).first()).toContainText('denied');
      }
      const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
      expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(' | ')}`)).toEqual(
        [],
      );
      await context.close();
    });
  }
}
