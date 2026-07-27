# already-a-problem

A [Claude Code](https://claude.com/claude-code) hook that watches everything you type and calls out your recurring English mistakes in real time — with a red damage-flash straight out of an FPS every time you get hit.

## Why

I'm a native German speaker. I asked Claude to read through ~2,500 of my own past Claude Code messages and tell me, honestly, what my recurring English mistakes were. It came back with a precise, well-cited list — mostly small, very German-shaped things: adverb placement ("I have already **a** dev account" instead of "I **already have** a dev account"), "a way **how**" instead of "a way **to**", "what do you mean **with**" instead of "what do you mean **by**", article mixups on borrowed technical words ("**a** html page", "**an** UI"), present-simple where English wants present-perfect ("I **am** a founder **since** 2022").

Getting a one-off report was useful. Getting pinged *the moment it happens, forever* is better. So this turns that report into a live hook: every prompt you send gets checked, in about 60ms, and:

- 🩸 a **mistake** flashes your entire screen red for a third of a second (every connected monitor) and drops a banner in your Claude Code session naming the mistake and the fix
- ✅ correctly nailing one of the same hard-won constructs gets a quiet banner instead — positive reinforcement, not just a scolding

## What it catches

~15 categories total, tuned for German→English transfer specifically (though the mechanism generalizes to any L1). A sample:

| Pattern | Wrong | Right |
|---|---|---|
| adverb placement | "I have already a call" | "I already have a call" |
| "a way how" | "a way how we can donate" | "a way to donate" |
| "mean with" | "what do you mean with X" | "what do you mean by X" |
| articles | "a html page" / "an UI" | "an html page" / "a UI" |
| present-simple + since | "I am a founder since 2022" | "I've been a founder since 2022" |
| do-support | "we have not enough" | "we don't have enough" |
| uncountables | "some informations" | "some information" |
| stative progressive | "we are not having" | "we don't have" |
| good vs. well | "how good can you build" | "how well can you build" |

See [`english-watcher.py`](./english-watcher.py) for the full, regex-documented list — every rule has a one-line explanation of *why* it's wrong baked in as the fix message.

Deliberately left out: general subject-verb agreement, word order, and spelling/typos — those need real NLP or are just fast-typing slips, not knowledge gaps, and a bad regex there produces more false positives than value.

A German-stopword/umlaut pre-filter skips non-English messages so it doesn't fire on German text (German "an" is a real preposition and will absolutely trip a naive regex).

## Install

Requires Python 3 and macOS (the screen flash uses a Cocoa/JXA trick; the banner works anywhere Claude Code hooks do — see [Non-macOS](#non-macos-linuxwindows) below).

1. Copy the two scripts somewhere permanent:
   ```bash
   mkdir -p ~/.claude/scripts
   cp english-watcher.py flash-red.js ~/.claude/scripts/
   chmod +x ~/.claude/scripts/english-watcher.py
   ```
2. Merge the hook from [`settings.snippet.json`](./settings.snippet.json) into your `~/.claude/settings.json` under `hooks.UserPromptSubmit`. **Merge, don't overwrite** — if you already have hooks configured, add this as another entry in that array.
3. Restart Claude Code (or run `/hooks` once) to pick up the new hook.
4. Type something wrong on purpose to test it, e.g. `I have already a call at 3pm`.

## Customize it for your own mistakes

The whole point is that this is *your* list, not a universal one. Ask Claude to do what I did:

> Look through my past [Claude Code / Cursor / whatever] conversations and tell me the recurring English (or any language) mistakes I actually make, with real quoted examples.

Then turn whatever it finds into `MISTAKE_RULES` / `PRAISE_RULES` entries — each is just `(category_name, compiled_regex, explanation_string)`. PRs adding solid rule sets for other L1 backgrounds (Spanish→English, Mandarin→English, etc.) are very welcome.

## Non-macOS (Linux/Windows)

`flash_red()` in `english-watcher.py` just shells out to `osascript`. Swap it for whatever your platform can do — the banner (`systemMessage` in the hook's JSON stdout) is cross-platform already, since that's a Claude Code feature, not an OS one.

## How the flash actually works

`flash-red.js` is JXA (`osascript -l JavaScript`) using the Cocoa bridge directly — no compiled app, no accessibility permissions needed. It creates a borderless, click-through, always-on-top `NSWindow` on every connected screen (`NSScreen.screens`, not just `mainScreen`) and fades its red background alpha out over ~12 steps.

Two non-obvious gotchas if you're extending it:
- `delay()` in JXA does **not** pump Cocoa's run loop, so a window ordered to the front never actually gets flushed to the window server before the script exits. Use `NSRunLoop.currentRunLoop.runUntilDate(...)` instead.
- `win.close()` and `win.display()` aren't reliably bridged through JXA's ObjC bridge in this context. Don't bother calling them — the window tears down fine when the `osascript` process exits, and setting `backgroundColor` already marks the window as needing display.

## License

MIT.
