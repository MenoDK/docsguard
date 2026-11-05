/* Content for the landing page and the lab. Everything the page says about behaviour is backed by a test; the output in
   the tour is recorded from the real tool (scripts/record_transcripts.py) and CI fails if it drifts. */
window.SITE = {
  name: 'docsguard',
  short: 'docsguard',
  title: 'docsguard · documentation that fails the build',
  logo: 'shield',
  repo: 'https://github.com/MenoDK/docsguard',
  accent: {
    light: { fill: '#8fc93a', ink: '#3f6a0a', on: '#14230a', soft: '#e8f5d0', onNavy: '#b5e66b' },
    dark: { fill: '#9ad34a', ink: '#c4ee8c', on: '#14230a', soft: '#2c3d14', onNavy: '#b5e66b' },
  },
  loading: {
    context: 'Docs',
    title: 'Following every link',
    text: 'Reading the documents, counting what the map claims, running the guards.',
    icon: 'doc',
    satellites: ['link', 'check', 'lock'],
    foot: 'Local demo · a sample project in a temporary folder, nothing leaves this machine',
    sketch: 'M10 122C56 122 66 58 112 58S158 128 204 128 252 70 300 70 322 112 334 112',
  },
  lab: { href: 'lab.html', cta: 'Enter the lab' },

  hero: {
    eyebrow: 'Documentation · guards that fail the build, hooks that say no',
    lead: 'Documentation that',
    soft: 'fails the build.',
    text: 'An AI coding session is only as good as the documents it loads, and documents rot. docsguard turns the habits that keep a documentation system healthy into checks that fail: a map that must be whole, decisions that keep their rejected alternatives, a handoff that reports a number, a startup budget, no secrets. Two hooks enforce what a markdown file can only request: no command that destroys unrecoverable work, no write to a protected path without a written reason.',
    primary: { label: 'Open the lab', href: 'lab.html' },
    secondary: { label: 'See how it works', href: '#tour', icon: 'layers' },
    pilot: 'Runs on your laptop · Python standard library only, nothing to sign up for',
    proof: [
      { icon: 'check', a: 'Every guard is proven by sabotage', b: 'a mutant must turn a test red' },
      { icon: 'flask', a: 'Every failure is a button', b: 'in a lab you can click' },
    ],
    top: ['DOCSGUARD', 'Fails the build. Says no before the damage.'],
    status: { icon: 'shield', small: 'Last verdict', strong: 'map-complete failed: docs/runbook.md is not on the map. The other eight guards passed.' },
    art: `<svg viewBox="0 50 500 620" role="img" aria-label="A file called CLAUDE.md points at a map document, which links to a handoff, a decision record and a checklist. A runbook next to it is not linked from anywhere and is marked as an orphan. Below, the output of the check command shows two guards passing and the map-complete guard failing on the runbook. Under that, a short bar shows what a session pays on every turn next to a long bar for reading everything, and a git reset --hard command is shown as denied before it runs.">
      <g class="a-line"><path d="M0 120H500M0 240H500M0 360H500M0 480H500M0 600H500M100 30V700M250 30V700M400 30V700"/></g>
      <g transform="translate(0 40)">
      <circle cx="420" cy="140" r="64" class="a-soft"/>

      <g>
        <rect x="26" y="114" width="112" height="46" rx="12" class="a-body"/>
        <rect x="26" y="114" width="112" height="46" rx="12" class="a-line"/>
        <text x="40" y="134" class="a-text-s">CLAUDE.md</text>
        <text x="40" y="150" class="a-text-s">~376 tokens</text>
      </g>
      <path d="M140 137H180" class="a-dash"/>
      <path d="M172 129l10 8-10 8" class="a-accent-s"/>

      <g>
        <rect x="184" y="106" width="116" height="62" rx="14" class="a-body"/>
        <rect x="184" y="106" width="116" height="62" rx="14" class="a-line"/>
        <text x="242" y="125" text-anchor="middle" class="a-text">MAP</text>
        <text x="242" y="144" text-anchor="middle" class="a-text-s">00-READ-FIRST</text>
        <text x="242" y="159" text-anchor="middle" class="a-text-s">not content</text>
      </g>

      <path d="M302 134C324 134 324 110 346 110" class="a-dash"/>
      <path d="M302 140H346" class="a-dash"/>
      <path d="M302 146C324 146 324 178 346 178" class="a-dash"/>
      <g>
        <rect x="346" y="96" width="128" height="28" rx="8" class="a-body"/>
        <text x="358" y="114" class="a-text-s">HANDOFF.md</text>
        <rect x="346" y="130" width="128" height="28" rx="8" class="a-body"/>
        <text x="358" y="148" class="a-text-s">ADR 0001</text>
        <rect x="346" y="164" width="128" height="28" rx="8" class="a-body"/>
        <text x="358" y="182" class="a-text-s">CHECKLIST.md</text>
      </g>

      <path d="M236 171l12 12M248 171l-12 12" class="a-bad"/>
      <g>
        <rect x="170" y="188" width="140" height="26" rx="8" class="a-bad-f" fill-opacity="0.3"/>
        <rect x="170" y="188" width="140" height="26" rx="8" class="a-line"/>
        <text x="180" y="205" class="a-text-s">orphan: runbook.md</text>
      </g>

      <g>
        <rect x="26" y="232" width="448" height="96" rx="16" class="a-body"/>
        <rect x="26" y="232" width="448" height="96" rx="16" class="a-line"/>
        <text x="42" y="252" class="a-text-s">docsguard check</text>
        <text x="458" y="252" text-anchor="end" class="a-text-s">FAILED · 1 problem</text>
        <path d="M40 260H460" class="a-line"/>
        <path d="M40 274l4 4 7-8" class="a-accent-s"/>
        <text x="60" y="278" class="a-text-s">map-links-live      5 examined</text>
        <rect x="34" y="284" width="432" height="18" rx="5" class="a-bad-f" fill-opacity="0.3"/>
        <path d="M41 288l8 8M49 288l-8 8" class="a-bad"/>
        <text x="60" y="296" class="a-text-s">map-complete        docs/runbook.md</text>
        <path d="M40 310l4 4 7-8" class="a-accent-s"/>
        <text x="60" y="314" class="a-text-s">no-secrets          18 examined</text>
      </g>

      <g>
        <text x="26" y="356" class="a-text">WHAT A SESSION PAYS</text>
        <rect x="26" y="366" width="56" height="18" rx="5" class="a-accent"/>
        <text x="92" y="379" class="a-text-s">every turn · ~1.2k tokens</text>
        <rect x="26" y="390" width="448" height="18" rx="5" class="a-line"/>
        <text x="36" y="403" class="a-text-s">reading everything · ~7.1k tokens</text>
      </g>

      <g>
        <rect x="26" y="424" width="448" height="30" rx="10" class="a-bad-f" fill-opacity="0.3"/>
        <rect x="26" y="424" width="448" height="30" rx="10" class="a-line"/>
        <text x="40" y="443" class="a-text-s">$ git reset --hard   →   denied before it runs</text>
      </g>
      </g>
    </svg>`,
  },

  principles: {
    lead: ['Documentation that rots', 'is worse than none.'],
    items: [
      ['link', 'A map that must be whole'],
      ['scroll', 'Decisions that keep what lost'],
      ['gauge', 'A startup cost with a ceiling'],
      ['shield', 'Hooks that say no'],
    ],
  },

  tour: {
    eyebrow: 'A tour of the whole thing',
    title: ['Five ways documentation', 'goes quietly wrong.'],
    text: 'Pick a tab. The output below is recorded from the real tool on a sample project; CI records it again and fails if it ever stops being true.',
    tag: 'Recorded output',
    tabs: [
      {
        id: 'map',
        label: 'Map',
        icon: 'link',
        title: 'A document nobody can reach does not exist.',
        text: 'The map is the one thing a session reads before choosing what to open. docsguard follows every link, requires every document under docs/ to be reachable from the map, and compares the counts the map declares with what is on disk. A broken link also orphans whatever it led to, and the output says so.',
        lab: 'lab.html#docs',
        transcript: (window.TRANSCRIPTS || {}).map || '',
      },
      {
        id: 'shape',
        label: 'Shape',
        icon: 'scroll',
        title: 'A record keeps what lost. A handoff keeps a number.',
        text: 'A decision record needs a status, a context, a decision and the alternatives it rejected, with numbering and an index that are whole. The handoff has eight sections, a real date and a measured suite state: “everything passes, as expected” is not a measurement. A skill has to say when it applies, or nobody will find it.',
        lab: 'lab.html#docs',
        transcript: (window.TRANSCRIPTS || {}).shape || '',
      },
      {
        id: 'budget',
        label: 'Budget',
        icon: 'gauge',
        title: 'What a session pays before it has done anything.',
        text: 'CLAUDE.md, what it imports and the unscoped rules are loaded on every turn, so they get a line cap and a token budget. The budget command prints what a fresh session pays against reading every document, measured on your repository and labelled as an estimate.',
        lab: 'lab.html#budget',
        transcript: (window.TRANSCRIPTS || {}).budget || '',
      },
      {
        id: 'secrets',
        label: 'Secrets',
        icon: 'key',
        title: 'A credential in a document travels with the document.',
        text: 'Documentation is copied into prompts and exports. Keys, tokens, credentials in a URL and cloud identifiers are found by pattern; the match is never printed, only which pattern matched and where. Obvious placeholders and the development defaults that appear in every README are not reported.',
        lab: 'lab.html#docs',
        transcript: (window.TRANSCRIPTS || {}).secrets || '',
      },
      {
        id: 'hooks',
        label: 'Hooks',
        icon: 'shield',
        title: 'A markdown file can only ask. A hook can refuse.',
        text: 'git-guard refuses commands that destroy unrecoverable work, also when they hide inside a wrapper or a substitution. scope-guard refuses writes to protected paths unless a committed line says why. Both let through anything they cannot parse, so they are never the reason a session stalls. What follows is the exact JSON Claude Code receives.',
        lab: 'lab.html#hooks',
        transcript: (window.TRANSCRIPTS || {}).hooks || '',
      },
    ],
    modulesTitle: 'Everything in the box.',
    modulesNote: 'Each part has its own tests and a place in the lab',
    modules: [
      ['check', 'docsguard check', 'Nine guards over the documentation system, and a tenth for the staged change: a document is added to the map in the commit that creates it. Exit 1 on any finding. A guard that examined nothing fails too, because a guard that sees nothing proves nothing.'],
      ['gauge', 'docsguard budget', 'What a session pays up front against reading everything, measured on your repository. Token counts are characters divided by four and are labelled as estimates wherever they are printed.'],
      ['shield', 'hook git-guard', 'A PreToolUse hook with a real shell tokenizer, not a regular expression over the string: wrappers, bash -c, command substitution and heredocs are understood. It denies with a reason, and lets through what it cannot parse.'],
      ['lock', 'hook scope-guard', 'Reads are never blocked. Writes to protected paths are denied unless .claude/authorizations.txt carries a committed line with a reason. A line without a reason is ignored on purpose, and the denial says so.'],
      ['box', 'docsguard init', 'A template with CLAUDE.md, AGENTS.md, the map, decision records, a handoff, skills, agent contracts and a bridge protocol. It passes its own guards: if it ever failed them, nearly every test would fail with it.'],
      ['flask', 'playground/', 'This page’s lab. A small standard-library server that runs the real guards on a sample project you can break. It is not part of the installed package, and it cannot run anything you type.'],
    ],
    transparency: {
      strong: 'Honest about the demo.',
      text: 'The lab edits a sample project in a temporary directory it owns, and the hooks are only ever asked what they would decide: nothing you type is run. The hooks are a denylist, so they stop the accidents they were written for, not a determined session. And a passing check proves a map is whole, not that a document is true.',
    },
  },

  challenges: {
    eyebrow: 'The hard parts',
    title: ['Go on,', 'try to lose a document.'],
    text: 'These are seven things that are easy to claim and hard to get right. Each has a recipe, what you should see, and a button that opens the lab on that exact tab.',
    items: [
      {
        label: 'Lose a document',
        icon: 'link',
        access: 'Lab · Docs',
        title: 'Add a runbook and forget the map.',
        text: 'A document nobody links to is one nobody will open.',
        steps: [
          'In <code>Docs</code>, press “Break it” on “Add a runbook and forget the map”.',
          'Read the row for <code>map-complete</code>.',
          'Press “Put it back”.',
        ],
        expect: '<code>map-complete</code> fails and names <code>docs/runbook.md</code>: not reachable from the map, with what to do about it. The other eight guards stay green, and putting it back returns every guard to <code>ok</code>.',
        lab: 'lab.html#docs',
      },
      {
        label: 'Cut a link',
        icon: 'route',
        access: 'Lab · Docs',
        title: 'Point the map at a file that is gone.',
        text: 'One dead link can hide more than one file.',
        steps: [
          'In <code>Docs</code>, press “Break it” on “Point the map at a file that is gone”.',
          'Read the findings of the two guards that fail.',
          'Press “Put it back”.',
        ],
        expect: '<code>map-links-live</code> says the map links to <code>PLAN.md</code>, which does not exist. <code>map-complete</code> then fails as well, because the checklist was only reachable through that row. Only the first of the two was written by you.',
        lab: 'lab.html#docs',
      },
      {
        label: 'Skip the measurement',
        icon: 'scroll',
        access: 'Lab · Docs',
        title: 'Write a decision with no losers, and a handoff with no number.',
        text: 'The two documents that most often become fiction.',
        steps: [
          'In <code>Docs</code>, press “Break it” on “Write a decision without the alternatives that lost”.',
          'Press “Break it” on “Report the suite state without a number”.',
          'Read the two rows, then press “Start over” at the top.',
        ],
        expect: '<code>adr-shape</code> says the record has no “Rejected alternatives” section: an ADR records what lost, and why. <code>handoff-shape</code> says the suite state carries no number: report what ran, not what was expected. “Start over” rebuilds the sample from the template and everything is green.',
        lab: 'lab.html#docs',
      },
      {
        label: 'Let the instructions grow',
        icon: 'gauge',
        access: 'Lab · Budget',
        title: 'Grow CLAUDE.md until a session pays for it on every turn.',
        text: 'Every rule is reasonable. Together they are not.',
        steps: [
          'In <code>Budget</code>, note what a session pays now.',
          'Press “Grow CLAUDE.md”.',
          'Look at the numbers, then open <code>Docs</code> and read the <code>instruction-budget</code> row.',
        ],
        expect: 'The session start jumps from about one thousand tokens to about eight and a half thousand, past the budget of six thousand, and a typical start goes from 58% of reading everything to 89% of it: the saving is nearly gone. <code>instruction-budget</code> fails twice: the file is over the per-file line cap, and the set that is loaded at the start is over the token budget.',
        lab: 'lab.html#budget',
      },
      {
        label: 'Paste a key',
        icon: 'key',
        access: 'Lab · Docs',
        title: 'Put a cloud access key in the handoff.',
        text: 'The key is made up. The guard does not know that, and it never prints it.',
        steps: [
          'In <code>Docs</code>, press “Break it” on “Paste a cloud access key into the handoff”.',
          'Read the <code>no-secrets</code> row and the terminal output under it.',
          'Look for the key in either of them.',
        ],
        expect: '<code>no-secrets</code> names the file and the pattern (an AWS access key id) and says the value is not shown. The key appears nowhere in the answer of the server, which a test pins.',
        lab: 'lab.html#docs',
      },
      {
        label: 'Ask a hook to destroy work',
        icon: 'shield',
        access: 'Lab · Hooks',
        title: 'Try a command that throws away uncommitted work.',
        text: 'A hook sees the command before the shell does.',
        steps: [
          'In <code>Hooks</code>, press “git reset --hard HEAD~3”.',
          'Press “bash -c "git reset --hard"”, which hides the same command inside a wrapper.',
          'Press “git status”.',
        ],
        expect: 'The first two are <code>denied</code>, each with a reason that says what would be lost and what to do instead. The request shown is the JSON Claude Code would send and the answer is what the hook printed. <code>git status</code> is allowed, and the answer is empty. Nothing you typed was run.',
        lab: 'lab.html#hooks',
      },
      {
        label: 'Write where you must not',
        icon: 'lock',
        access: 'Lab · Hooks',
        title: 'Write a protected file, then authorize it properly.',
        text: 'An exception is a line in a file, with a reason, in the diff.',
        steps: [
          'In <code>Hooks</code>, press “Write .env”: it is denied.',
          'Press “Write the line without a reason”, then “Write .env” again.',
          'Press “Authorize .env with a reason”, then “Write .env” a third time.',
        ],
        expect: 'The first answer is <code>protected-path</code> with the reason the path is protected and the exact line a human would add. After the line with no reason it is denied again, and the answer says one authorization line was ignored because it gave no reason. After the line with a reason it is allowed.',
        lab: 'lab.html#hooks',
      },
    ],
  },

  run: {
    eyebrow: 'Run it in a minute',
    title: ['One command.', 'A documentation system you can break.'],
    text: 'You need Docker for the lab. The tool itself needs only Python 3.11 or newer and has no dependencies. Nothing leaves your machine.',
    steps: [
      ['terminal', 'Clone', 'git clone, then cd into the folder.'],
      ['play', 'Start', 'make playground builds a small image and starts the lab on the loopback of your machine.'],
      ['globe', 'Open', 'http://localhost:8200 is this page. Press “Enter the lab”.'],
      ['flask', 'Break it', 'Use the hard parts above, or run make smoke for the checks that talk to the running server.'],
    ],
    terminal: {
      title: 'bash',
      lines: [
        '# 1. get the code',
        'git clone https://github.com/MenoDK/docsguard.git',
        'cd docsguard',
        '# 2. start the lab (builds a small image, nothing to configure)',
        'make playground',
        '# 3. open http://localhost:8200 and press “Enter the lab”',
        '# or use the tool on a folder of your own, without Docker',
        'pip install .',
        'docsguard init ./my-project --name my-project',
        'docsguard check --root ./my-project',
      ],
    },
  },

  under: {
    eyebrow: 'Under the hood',
    title: ['A small surface,', 'serious edges.'],
    text: 'The interesting code is short on purpose. The decisions behind it are written down with the alternatives that lost.',
    stackTitle: 'What it is built with',
    stack: [
      { group: 'Language', items: ['Python 3.11 and newer', 'Standard library only · no dependencies', 'mypy --strict · ruff', 'A shell tokenizer, not a regular expression'] },
      { group: 'Guards', items: ['Nine guards and one for the staged change', 'A guard that examined nothing fails', 'Dismissals carry a reason and can expire', 'A finding never prints the secret it found'] },
      { group: 'Hooks', items: ['PreToolUse · deny with a reason', 'A denylist that fails open', 'Authorizations are lines in the diff', 'bash -c and substitution are understood'] },
      { group: 'Quality', items: ['pytest · real files, real processes', 'A sabotage script that must be caught', 'Playwright + axe · 14 languages', 'The template passes its own guards'] },
      { group: 'Delivery', items: ['Multi-stage Dockerfile, non-root', 'Read-only mount, no network, no capabilities', 'GitHub Actions · pinned gitleaks', 'A composite action for your CI'] },
    ],
    proofTitle: 'What is measured, and the records behind it',
    numbers: [
      ['451', 'tests, none of them against a mock of the thing they test'],
      ['86', 'sabotages of the guards and the lab, each caught by the test that guards it'],
      ['10', 'ways to break the sample, each caught by the guard it names'],
      ['7', 'decision records, each with rejected alternatives'],
    ],
    decisions: [
      ['Standard library only', 'ADR 0002: why a guard that needs an install step is a guard people skip.', 'docs/adr/0002-standard-library-only.md'],
      ['Hooks: a denylist that fails open', 'ADR 0003: why a hook must never be the reason a session stalls.', 'docs/adr/0003-hooks-denylist-and-fail-open.md'],
      ['A guard that examines nothing fails', 'ADR 0005: the vacuous pass, and how to refuse it.', 'docs/adr/0005-a-guard-that-examines-nothing-fails.md'],
      ['Dismissals carry reasons and expire', 'ADR 0006: how an exception avoids becoming the rule.', 'docs/adr/0006-dismissals-carry-reasons-and-expire.md'],
    ],
    measuredOn: 'Measured on 2026-11-05. Counts come from the commands in the README, not from memory.',
    future: [
      ['Run it in a real repository’s CI for a month', 'to see which guards earn their keep and which only make noise.'],
      ['A guard for links to code', 'a document that names a function which was renamed.'],
      ['A real tokenizer for the budget', 'instead of characters divided by four, when it can be an optional extra.'],
      ['A hook for new dependencies', 'refusing one that has no decision record.'],
    ],
  },

  about: {
    why: 'docsguard is the part of my work about how people and AI sessions share a codebase: documents that stay true, a startup cost that stays small, and refusals that happen before the damage rather than after. The ideas come from how I document my own projects; the code in this repository is written fresh, tested, and breakable on purpose.',
  },

  faq: [
    ['Why not a markdown linter?', 'A linter checks how a file looks. The rot that costs sessions is structural: a document no link reaches, a count that stopped being true, a decision that lost its alternatives, a handoff with nothing measured. Those are the checks here.'],
    ['Does it need Claude Code?', 'No. check, budget and init are plain commands, and the guards are useful in any repository that keeps its documentation as a map. The two hooks speak the PreToolUse format of Claude Code and do nothing when the command is not installed.'],
    ['Can the hooks be bypassed?', 'Yes. They are a denylist, so they stop the accidents they were written for and not a session that is set on doing harm. They also let through input they cannot parse, on purpose: a guard that blocks on its own parsing failures gets switched off by the first person it annoys, which is worse than the accident (ADR 0003).'],
    ['Why only the standard library?', 'A guard that needs an install step is a guard people skip, and a dependency is a thing that can break the build of the thing that guards it. The cost is writing a small shell tokenizer and a front-matter reader by hand, and testing them (ADR 0002).'],
    ['Is the token count real?', 'It is characters divided by four, and every place that prints it says so. It is good for budgeting a startup cost and not for billing. A real tokenizer would be an optional extra, not a requirement (ADR 0004).'],
    ['Can the lab reach anything?', 'It edits a sample project in a temporary directory that the process owns and removes on exit. The hooks are only asked what they would decide: nothing you type is run, and a test pins that. Its changing endpoints answer 404 unless asked for, the server refuses to start with them on when told it is in production, and it refuses any Host or Origin it does not own.'],
    ['Why fail a guard that found nothing to check?', 'Because a map guard that looked at zero documents has proved nothing, and a green tick that means nothing is how checks lose trust. A guard that examined nothing, and was not explicitly skipped, fails (ADR 0005).'],
  ],

  closing: {
    eyebrow: 'Your turn',
    title: ['Try to lose', 'a document.'],
    button: 'Open the lab',
    fine: 'Local only · a sample project · nothing is sent anywhere',
  },
};
