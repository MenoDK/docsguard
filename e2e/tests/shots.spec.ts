import { type Page, test } from '@playwright/test';
import { active, cards, leaveSplash, named, openLab, resetLab } from './helpers';

// Only with SHOTS=1 (`make screenshots`): these are the pictures in the README, taken from the real lab.
test.skip(process.env.SHOTS !== '1', 'screenshots are taken on request');
test.use({ viewport: { width: 1360, height: 860 }, colorScheme: 'light', contextOptions: { reducedMotion: 'reduce' } });

const OUT = process.env.SHOTS_DIR ?? '../docs/img';
const press = (page: Page, name: string) => active(page).getByRole('button', { name, exact: true }).first().click();
const settle = async (page: Page) => {
  await page.evaluate(() => window.scrollTo(0, 0)); // clicking scrolled the page; the picture starts at the top
  await page.waitForTimeout(5000); // let the confirmation toast leave
};

test('landing', async ({ page }) => {
  await page.goto('/?lang=en');
  await leaveSplash(page);
  await page.screenshot({ path: `${OUT}/landing.png` });
});

test('lab: a map with a dead link, and the guards that notice', async ({ page, request }) => {
  await resetLab(request);
  await openLab(page, 'Docs');
  await named(page, 'Point the map at a file that is gone').getByRole('button', { name: 'Break it' }).click();
  await named(page, 'map-complete').waitFor();
  await page.setViewportSize({ width: 1360, height: 1500 });
  await settle(page);
  await page.screenshot({ path: `${OUT}/lab-docs.png` });
  await resetLab(request);
});

test('lab: the hooks say no, with the JSON that was sent and the JSON that came back', async ({ page, request }) => {
  await resetLab(request);
  await openLab(page, 'Hooks');
  await press(page, 'git status');
  await press(page, 'bash -c "git reset --hard"');
  await cards(page).first().waitFor();
  await page.setViewportSize({ width: 1360, height: 1500 });
  await settle(page);
  await page.screenshot({ path: `${OUT}/lab-hooks.png` });
});

test('lab: what a session pays, before and after CLAUDE.md grows', async ({ page, request }) => {
  await resetLab(request);
  await openLab(page, 'Budget');
  await press(page, 'Grow CLAUDE.md');
  await active(page).getByText('over the budget of 6,000').waitFor();
  await page.setViewportSize({ width: 1360, height: 1300 });
  await settle(page);
  await page.screenshot({ path: `${OUT}/lab-budget.png` });
  await resetLab(request);
});
