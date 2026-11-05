/* The lab: three tabs, each one a way to ask the real guards a question. Loaded before kit.js; it only declares things.
   Everything that came from the API is inserted as text, never as markup. The page can only talk to this server (strict
   CSP). Every button that changes the sample goes through /api/lab/*, which answers 404 unless the lab is on. */
(() => {
  'use strict';

  const GIT_PRESETS = [
    'git reset --hard HEAD~3',
    'git push --force origin main',
    'git clean -fdx',
    'bash -c "git reset --hard"',
    'git status',
    'git commit -m "wip"',
  ];
  const SCOPE_PRESETS = [
    ['Write', '.env'],
    ['Edit', 'keys/server.pem'],
    ['Bash', 'echo x > .env'],
    ['Write', 'src/app.py'],
    ['Write', '.env.example'],
  ];
  const AUTHORIZE_REASON = 'staging file, reviewed in the pull request';

  const errorText = (r) => (r.data && r.data.error ? `${r.data.error}${r.data.issues ? `: ${r.data.issues.join('; ')}` : ''}` : `The server answered ${r.status}.`);
  const tokens = (n) => `~${n.toLocaleString('en-US')} tokens`;
  /** replaceChildren that accepts arrays and skips null, which it would otherwise print as the word "null". */
  const fill = (el, ...kids) => el.replaceChildren(...kids.flat().filter((x) => x !== null && x !== undefined && x !== false));
  function push(target, card, keep = 4) {
    target.prepend(card);
    while (target.children.length > keep) target.lastElementChild.remove();
  }

  let overview = null;
  const getOverview = () => {
    overview ||= fetch('/api/overview').then((r) => (r.ok ? r.json() : null)).catch(() => null);
    return overview;
  };
  /** A notice at the top of a tab when the server was started without the lab. */
  async function labNotice(k) {
    const { box } = k;
    const o = await getOverview();
    if (o && o.lab) return null;
    return box('The lab is off on this server', 'Start it with DG_LAB=1 (make playground does) to use the buttons that change the sample. Everything that only asks still works.');
  }

  /* ---------------------------------------------------------------- docs */
  async function docsTab(panel, k) {
    const { api, h, button, badge, box, out } = k;
    const notice = await labNotice(k);
    const breaks = h('div', { 'aria-live': 'polite' });
    const verdict = h('div', { 'aria-live': 'polite' });
    const terminal = h('div', {});
    const files = h('div', {});

    async function refresh() {
      const [o, c, f] = await Promise.all([api('/api/overview'), api('/api/check'), api('/api/files')]);
      if (!o.ok || !c.ok || !f.ok) throw new Error('Could not read the sample project.');

      fill(breaks, h('ul', { class: 'trace' }, o.data.breaks.map((b) => h('li', {},
        h('strong', {}, b.title),
        badge(b.guard, b.active ? 'bad' : ''),
        h('span', {}, b.summary),
        button(b.active ? 'Put it back' : 'Break it', () => toggle(b), { small: true, variant: b.active ? 'secondary' : 'primary', ic: b.active ? 'refresh' : 'alert' })))));

      fill(verdict,
        h('p', {}, c.data.ok ? badge('every guard passes', 'ok') : badge(`${c.data.problems} problem${c.data.problems === 1 ? '' : 's'}`, 'bad')),
        h('ul', { class: 'trace' }, c.data.rules.map((r) => h('li', {},
          h('strong', {}, r.rule),
          badge(r.ok ? 'ok' : 'failed', r.ok ? 'ok' : 'bad'),
          h('span', {}, r.skipped ? `skipped: ${r.skipped}` : `${r.examined} examined`),
          ...r.findings.map((x) => h('span', { class: 'hint' }, `${x.path}${x.line ? `:${x.line}` : ''}: ${x.message}`))))));

      fill(terminal, out(c.data.rendered));
      fill(files, h('ul', { class: 'trace' }, f.data.files.map((x) => h('li', {}, h('code', {}, x.path), h('span', {}, `${x.bytes.toLocaleString('en-US')} bytes`)))));
    }
    async function toggle(b) {
      const r = await api('/api/lab/break', { method: 'POST', body: { id: b.id, on: !b.active } });
      if (!r.ok) throw new Error(errorText(r));
      await refresh();
    }

    panel.append(h('div', { class: 'cols' },
      h('div', {},
        notice,
        box('1 · Break it', 'Each button changes one thing in a sample project, the way a busy week would. Press it again to put it back.', breaks)),
      h('div', {},
        box('2 · What the guards say', 'The real `docsguard check`, run on the sample after every change.', verdict, terminal),
        box('3 · What init created', 'The sample is the shipped template, rebuilt from scratch every time something changes. It passes its own guards.', files))));
    await refresh();
  }

  /* ---------------------------------------------------------------- hooks */
  /** A card for a hook's decision: the verdict, the reason, the JSON that was sent and the JSON that came back. */
  function decision(k, title, r) {
    const { h, badge, kv, out } = k;
    if (!r.ok) return h('div', { class: 'box arrive' }, h('h3', {}, title, ' ', badge(String(r.status), 'bad')), out(r.data));
    const d = r.data;
    return h('div', { class: 'box arrive' },
      h('h3', {}, title, ' ', d.allowed ? badge('allowed', 'ok') : badge('denied', 'bad'), ' ', h('small', {}, `${r.ms} ms`)),
      kv({ Hook: d.hook, Rule: d.rule || '—', Reason: d.reason || 'none: the hook printed nothing, so the tool call goes ahead' }),
      h('p', { class: 'hint' }, 'What Claude Code sends to the hook'),
      out(JSON.stringify(JSON.parse(d.request), null, 2)),
      h('p', { class: 'hint' }, 'What the hook printed'),
      out(d.wire ? JSON.stringify(JSON.parse(d.wire), null, 2) : '(nothing)'));
  }

  async function hooksTab(panel, k) {
    const { api, h, button, box, labelled } = k;
    const notice = await labNotice(k);
    const log = h('div', {});
    const authorizations = h('div', { 'aria-live': 'polite' });

    const command = h('input', { id: 'git-command', type: 'text', spellcheck: 'false', autocomplete: 'off', placeholder: 'git reset --hard' });
    const tool = h('select', { id: 'scope-tool' }, ['Write', 'Edit', 'Bash'].map((t) => h('option', { value: t }, t)));
    const target = h('input', { id: 'scope-target', type: 'text', spellcheck: 'false', autocomplete: 'off', placeholder: '.env' });

    const askGit = (text) => async () => {
      const r = await api('/api/hooks/git', { method: 'POST', body: { command: text } });
      push(log, decision(k, text, r));
    };
    const askScope = (t, text) => async () => {
      const r = await api('/api/hooks/scope', { method: 'POST', body: { tool: t, target: text } });
      push(log, decision(k, `${t} ${text}`, r));
    };
    async function showAuthorizations() {
      const o = await api('/api/overview');
      if (!o.ok) return;
      fill(authorizations, o.data.authorizations.length
        ? h('ul', { class: 'trace' }, o.data.authorizations.map((line) => h('li', {}, h('code', {}, line))))
        : h('p', { class: 'hint-inline' }, 'No authorization lines yet: .claude/authorizations.txt holds only its comment.'));
    }
    const authorize = (reason) => async () => {
      const r = await api('/api/lab/authorize', { method: 'POST', body: { needle: '.env', reason } });
      if (!r.ok) throw new Error(errorText(r));
      await showAuthorizations();
    };

    panel.append(h('div', { class: 'cols' },
      h('div', {},
        notice,
        box('1 · git-guard', 'Commands that throw away work nobody can get back. Nothing you type is run: the hook is only asked what it would decide.',
          h('div', { class: 'row' }, GIT_PRESETS.map((c) => button(c, askGit(c), { small: true, variant: 'secondary' }))),
          labelled('Or type a command', command),
          h('div', { class: 'row' }, button('Ask the hook', () => askGit(command.value)(), { small: true, variant: 'primary', ic: 'shield' }))),
        box('2 · scope-guard', 'Writes to paths that hold credentials. Reads are never blocked. An exception is a line in a file, with a reason.',
          h('div', { class: 'row' }, SCOPE_PRESETS.map(([t, p]) => button(`${t} ${p}`, askScope(t, p), { small: true, variant: 'secondary' }))),
          labelled('Or choose a tool', tool),
          labelled('and a path (or, for Bash, a command)', target),
          h('div', { class: 'row' }, button('Ask the hook', () => askScope(tool.value, target.value)(), { small: true, variant: 'primary', ic: 'shield' })),
          h('p', { class: 'hint' }, 'The line a human would add to .claude/authorizations.txt:'),
          h('div', { class: 'row' },
            button('Authorize .env with a reason', authorize(AUTHORIZE_REASON), { small: true, ic: 'lock' }),
            button('Write the line without a reason', authorize(''), { small: true, ic: 'unlock' })),
          authorizations)),
      h('div', {}, log)));
    await showAuthorizations();
  }

  /* ---------------------------------------------------------------- budget */
  async function budgetTab(panel, k) {
    const { api, h, button, badge, box, kv, out } = k;
    const notice = await labNotice(k);
    const summary = h('div', { 'aria-live': 'polite' });
    const loaded = h('div', {});
    const terminal = h('div', {});

    async function refresh() {
      const [b, o] = await Promise.all([api('/api/budget'), api('/api/overview')]);
      if (!b.ok || !o.ok) throw new Error('Could not read the budget.');
      const d = b.data;
      const grown = o.data.breaks.find((x) => x.id === 'bloat').active;
      const over = d.session_tokens > d.session_budget;
      const share = Math.round((100 * d.typical_start_tokens) / d.everything_tokens);
      fill(summary,
        kv({
          'Session start': h('span', {}, tokens(d.session_tokens), ' ', over ? badge(`over the budget of ${d.session_budget.toLocaleString('en-US')}`, 'bad') : badge(`within ${d.session_budget.toLocaleString('en-US')}`, 'ok')),
          'A typical start': `${tokens(d.typical_start_tokens)}: the above, plus the map and the handoff`,
          'Reading everything': tokens(d.everything_tokens),
          'A typical start is': `${share}% of reading everything`,
        }),
        h('label', { for: 'meter-typical' }, 'A typical start, against reading everything'),
        h('meter', { id: 'meter-typical', min: 0, max: d.everything_tokens, value: d.typical_start_tokens }, `${share}%`),
        h('div', { class: 'row' }, grown
          ? button('Put it back', () => grow(false), { small: true, ic: 'refresh' })
          : button('Grow CLAUDE.md', () => grow(true), { small: true, variant: 'primary', ic: 'alert' })));
      fill(loaded, h('ul', { class: 'trace' }, d.session_start.map((f) => h('li', {},
        h('strong', {}, f.path), badge(f.via, ''), h('span', {}, `${f.lines} lines · ${tokens(f.tokens)}`)))));
      const printed = out(d.rendered);
      printed.classList.add('terminal');
      fill(terminal, printed);
    }
    async function grow(on) {
      const r = await api('/api/lab/break', { method: 'POST', body: { id: 'bloat', on } });
      if (!r.ok) throw new Error(errorText(r));
      await refresh();
    }

    panel.append(h('div', { class: 'cols' },
      h('div', {},
        notice,
        box('1 · What a session pays', 'Measured on the sample, the way `docsguard budget` measures your repository. Token counts are characters divided by four: an estimate, good for budgeting and not for billing.', summary,
          h('div', { class: 'row' }, button('Refresh', refresh, { small: true, ic: 'refresh' }))),
        box('2 · What is loaded on every turn', 'CLAUDE.md, what it imports, and the rules that are not scoped to a path.', loaded)),
      h('div', {}, box('3 · The real output', 'Exactly what `docsguard budget` prints for the sample.', terminal))));
    await refresh();
  }

  window.LAB = {
    eyebrow: 'The lab',
    title: 'Break the documentation. Ask the hooks.',
    text: 'Ten ways for documentation to rot, two hooks that refuse, and what a session pays before it has done anything. Everything runs the real guards on a sample project in a temporary folder.',
    reset: {
      label: 'Start over',
      hint: 'Every break put back, every authorization line removed, the sample rebuilt from the template.',
      done: 'Back to a clean sample.',
      run: async ({ api }) => {
        const r = await api('/api/lab/reset', { method: 'POST', body: {} });
        if (!r.ok) throw new Error('Could not reset the lab.');
      },
    },
    tabs: [
      { id: 'docs', label: 'Docs', icon: 'scroll', render: (p, k) => docsTab(p, k) },
      { id: 'hooks', label: 'Hooks', icon: 'shield', render: (p, k) => hooksTab(p, k) },
      { id: 'budget', label: 'Budget', icon: 'gauge', render: (p, k) => budgetTab(p, k) },
    ],
  };
})();
