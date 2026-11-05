# 0007. The playground runs the real guards on a sample it owns, and executes nothing it is given

Status: Accepted

## Context

A documentation tool is easy to describe and hard to believe. The playground exists so that a reader can break a sample
project and watch the guards notice. Three things could make that demonstration worthless or dangerous:

- If the lab shows *recorded* answers for its buttons, the buttons prove nothing; the page could say anything.
- The hooks are asked "would you allow this command?". A lab that answered by *running* the command would be a remote
  shell with a friendly face, and a local one is still reachable from any web page the visitor has open (a hostile page
  can send requests to `localhost`, and a DNS-rebinding page arrives under its own name).
- The sample has to be damaged and repaired many times. A lab that edits real files, or a shared fixture, leaves
  residue, and the next visitor sees somebody else's break.

## Decision

1. **The lab runs the real code.** `check` and `budget` are the package's own functions over a real directory; each hook
   is called through its own entry point with the exact PreToolUse JSON Claude Code would send, and what it prints is
   what the page shows. There is no second implementation to drift.
2. **The lab owns a temporary directory.** The sample is built from the package's own template. The state is a set of
   active breaks plus the authorization lines written so far, and every change rebuilds the sample from that set, so
   two breaks on one file cannot undo each other and "start over" is exact. The directory is removed on exit.
3. **Nothing the visitor types is executed.** A command or path is serialized into the hook's input and nothing else; a
   test plants a marker file behind a command that would create it and requires the file not to exist.
4. **The changing endpoints are off unless asked for** (`DG_LAB=1`), and the server refuses to start with them on when it
   is told it is in production. They have no authentication on purpose: this is a local tool.
5. **Two checks keep a web page from driving it.** The `Host` header must be a name the server answers to, which is what
   defeats DNS rebinding; and a request that changes something must come from this origin or from no browser at all
   (`Origin`, `Sec-Fetch-Site`). Request bodies are read in full, or the connection is closed, before anything is
   answered.
6. **The server is the standard library** (ADR 0002 extended to the demo), with a strict content security policy: every
   script and style is a same-origin file and nothing is inline.

## Rejected alternatives

- **Recorded answers behind the buttons.** Cheap and safe, and a demonstration of nothing. The landing page keeps
  recorded output for the tour, regenerated and checked in CI, but the lab is live.
- **Run the visitor's command in a sandbox to show what the hook *prevented*.** More vivid, and it moves the whole risk
  of the demo into the sandbox. A hook is a decision function; the lab shows the decision.
- **A web framework for the server.** Routing and validation for eight endpoints are shorter than the framework's
  configuration, and a dependency here would contradict the tool the demo is about (ADR 0002).
- **Authentication for the lab.** It would protect a sample project in a temporary directory with a login screen that is
  larger than the thing protected, and it would be the first thing a reader has to get past. The right answer is that it
  binds to the loopback, is off unless asked, and is refused in production.
- **Share one sample between visitors.** Simpler, and one visitor's break becomes the next one's confusion. A single
  sample with a lock is acceptable for a local tool used by one person; it is documented as such.

## Consequences

The lab is single-user by design and says so. The honest limit of the demonstration is stated on the page: the hooks are
a denylist (ADR 0003), the lab shows what they would decide and not what a session would do next, and a passing check
proves a map is whole, not that a document is true. The server tests run over a real socket, including two requests on
one connection, because that is where the one real bug of this component lived.
