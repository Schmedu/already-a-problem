#!/usr/bin/env python3
"""UserPromptSubmit hook: flags (and praises) a handful of recurring
German->English transfer patterns in the submitted prompt. Mistakes get an
in-session banner plus a brief red screen flash; correct usage of the same
constructs gets a banner only. Silent otherwise."""
import json
import os
import re
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FLASH_SCRIPT = os.path.join(SCRIPT_DIR, "flash-red.js")

VOWEL_SOUND_EXCEPTIONS = {
    "hour", "hours", "honest", "honor", "honour", "mvp", "html", "api",
    "mri", "rsvp", "x-ray", "xray", "llm", "fbi", "ngo", "mkv",
}
# prefixes, so compounds like "userland"/"unibody" inherit the same sound
CONSONANT_SOUND_PREFIXES = (
    "ui", "unique", "unicorn", "user", "europe", "uniform", "university",
    "utility", "utensil", "use", "useful", "usable", "unit", "united",
    "universal", "url", "uk", "us", "one", "once", "uuid",
)

GERMAN_STOPWORDS = {
    "und", "nicht", "ist", "der", "die", "das", "für", "fuer", "mit", "auch",
    "oder", "auf", "sich", "eine", "einen", "einem", "einer", "kann", "wir",
    "ich", "du", "sie", "er", "es", "zu", "im", "am", "vom", "zum", "zur",
    "als", "wenn", "weil", "aber", "noch", "schon", "dann", "also", "doch",
    "mal", "bitte", "danke", "heute", "morgen", "hier", "da", "was", "wer",
    "wo", "warum", "wie", "kein", "keine", "wuerde", "würde", "sollte",
    "koennen", "können", "muessen", "müssen",
}

ARTICLE_WORD_RE = re.compile(r"\b(a|an)\s+([a-zA-Z][a-zA-Z-]*)\b")

MISTAKE_RULES = [
    (
        "adverb placement",
        re.compile(r"\b(?:have|has|had)\s+(already|still|also)\s+(a|an|some|any|no|many|few|this|that|the)\b", re.I),
        "in English 'already/still/also' go right before the main verb: “I already have…” not “I have already a…”",
    ),
    (
        "a way how",
        re.compile(r"\b(a|an|the)\s+(way|solution|method|approach)\s+how\b", re.I),
        "drop 'how': “a way to…” / “a way we can…”, not “a way how…”",
    ),
    (
        "mean with",
        re.compile(r"\bmeans?\s+with\b", re.I),
        "it's 'what do you mean BY X', not 'mean with X'",
    ),
    (
        "present-simple + since",
        re.compile(r"\b(i am|i'm|he is|he's|she is|she's|we are|we're|they are|they're)\s+(?:a|an|the)\s+\w+(?:\s+\w+){0,3}\s+since\s+(19|20)\d{2}\b", re.I),
        "use present perfect with 'since': “I've been… since 2022”, not “I am… since 2022”",
    ),
    (
        "subject-verb agreement",
        re.compile(r"\bdoes\s+\w+\s+has\b", re.I),
        "after 'does', use the base form: “does X have”, not “does X has”",
    ),
    (
        "missing do-support",
        re.compile(r"\bhave\s+not\s+enough\b", re.I),
        "negate with 'don't': “we don't have enough”, not “we have not enough”",
    ),
    (
        "uncountable noun",
        re.compile(r"\binformations\b", re.I),
        "'information' has no plural in English, even though German 'Informationen' does",
    ),
    (
        "past-simple vs present-perfect",
        re.compile(r"\b(its|it's)\s+already\s+\d+\s+days?\s+ago\b|\bnow\s+(saw|did|went|had|made|found|got|came|took|gave|wrote|ate|drank)\s+already\b", re.I),
        "use present perfect here: “it's already been 3 days since…” / “I've now seen…”, not past simple + already/ago",
    ),
    (
        "stative verb + progressive",
        re.compile(r"\b(is|are|was|were)\s+not\s+having\b", re.I),
        "'have' (possession) isn't normally progressive: “we don't have”, not “we are not having”",
    ),
    (
        "good vs. well / usual vs. usually",
        re.compile(r"\bhow\s+good\s+(can|do|does|did|will|would|is|are)\b|\bas\s+usually\b", re.I),
        "'good' is an adjective, 'well' is the adverb (“how well can…”); and it's “as usual”, not “as usually”",
    ),
    (
        "preposition (extra)",
        re.compile(r"\blink(?:s|ed|ing)?\s+under\s+each\s+other\b", re.I),
        "'link to each other', not 'link under each other'",
    ),
    (
        "how do you call",
        re.compile(r"\bhow\s+(do|does|did)\s+(u|you)\s+call\s+(this|that|these|those)\b", re.I),
        "'what do you call this', not 'how do you call this' (that asks about the action of calling, not the name)",
    ),
    (
        "idiom calque",
        re.compile(r"\ba\s+fresh\s+wind\b", re.I),
        "the English idiom is 'a breath of fresh air', not 'a fresh wind'",
    ),
    (
        "coined word",
        re.compile(r"\brehappen(?:ing|ed|s)?\b|\bexistend\b", re.I),
        "not a word in English - use 'happen again'/'recur' or 'existing'",
    ),
    (
        "nationality capitalization",
        re.compile(r"\b(german|european|american|french|italian|spanish|chinese|japanese|russian|dutch|swiss|austrian|british|english|indian|canadian|mexican|brazilian|korean|african|australian|irish|scottish|welsh|polish|swedish|norwegian|danish|finnish|greek|turkish|ukrainian)\b"),
        "nationality/language adjectives are always capitalized in English, even mid-sentence",
    ),
]

PRAISE_RULES = [
    (
        "adverb placement",
        re.compile(r"\b(already|still|also)\s+(have|has|had)\s+(a|an|some|any|no|many|few|this|that|the)\b", re.I),
        "nice - adverb right before the verb, exactly where it belongs",
    ),
    (
        "a way how",
        re.compile(r"\b(a|an|the)\s+(way|solution|method|approach)\s+(to|that|we|i|you|of|for)\b", re.I),
        "clean - no stray 'how' after way/solution",
    ),
    (
        "mean with",
        re.compile(r"\bmeans?\s+by\b", re.I),
        "correct preposition - 'mean by', not 'mean with'",
    ),
    (
        "present-simple + since",
        re.compile(r"\b(i've|i have|we've|we have|they've|they have|he's|he has|she's|she has|you've|you have)\s+been\b[\w\s]{0,40}?\bsince\s+(19|20)\d{2}\b", re.I),
        "present perfect + 'since' - exactly right",
    ),
    (
        "subject-verb agreement",
        re.compile(r"\bdoes\s+\w+\s+have\b", re.I),
        "correct - base form after 'does'",
    ),
    (
        "missing do-support",
        re.compile(r"\b(don'?t|doesn'?t)\s+have\s+enough\b", re.I),
        "correct do-support in the negative",
    ),
    (
        "uncountable noun",
        re.compile(r"\b(some|any|no|much|little)\s+information\b", re.I),
        "correct - 'information' stayed singular/uncountable",
    ),
    (
        "stative verb + progressive",
        re.compile(r"\b(don'?t|doesn'?t)\s+have\s+(a|an|any|some|no)\b", re.I),
        "correct - simple present, not progressive, for possession",
    ),
    (
        "good vs. well / usual vs. usually",
        re.compile(r"\bhow\s+well\s+(can|do|does|did|will|would|is|are)\b|\bas\s+usual\b", re.I),
        "correct - well/usual used as the adverb here",
    ),
    (
        "how do you call",
        re.compile(r"\bwhat\s+(do|does|did)\s+(u|you)\s+call\s+(this|that|these|those)\b", re.I),
        "correct - 'what do you call', not 'how'",
    ),
]


def is_mostly_german(text):
    words = re.findall(r"[a-zA-ZäöüÄÖÜß]+", text.lower())
    if not words:
        return False
    if re.search(r"[äöüßÄÖÜ]", text):
        return True
    hits = sum(1 for w in words if w in GERMAN_STOPWORDS)
    return hits >= 3


def check_article(text):
    for m in ARTICLE_WORD_RE.finditer(text):
        article, word = m.group(1).lower(), m.group(2).lower()
        is_tricky = False
        if word in VOWEL_SOUND_EXCEPTIONS:
            expected = "an"
            is_tricky = True
        elif word.startswith(CONSONANT_SOUND_PREFIXES):
            expected = "a"
            is_tricky = True
        elif word[0] in "aeiou":
            expected = "an"
        else:
            expected = "a"
        if expected != article:
            return ("MISTAKE", m.group(0), f"should be '{expected} {word}', not '{article} {word}'")
        elif is_tricky:
            return ("PRAISE", m.group(0), f"correct - '{article} {word}' is one of the tricky ones")
    return None


def check_redundant_adverb(text):
    words = text.split()
    for target in ("already", "also", "still"):
        positions = [i for i, w in enumerate(words) if re.sub(r"[^a-zA-Z]", "", w).lower() == target]
        for a, b in zip(positions, positions[1:]):
            if b - a <= 12:
                return (target, f"used '{target}' twice close together - probably only needs it once")
    return None


def flash_red():
    try:
        subprocess.Popen(
            ["osascript", "-l", "JavaScript", FLASH_SCRIPT],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def banner(message):
    print(json.dumps({"systemMessage": message}))


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    text = payload.get("prompt", "")
    if not text or not isinstance(text, str):
        return
    if is_mostly_german(text):
        return

    mistakes, praises = [], []
    for name, pattern, tip in MISTAKE_RULES:
        m = pattern.search(text)
        if m:
            mistakes.append((name, m.group(0), tip))
    for name, pattern, tip in PRAISE_RULES:
        m = pattern.search(text)
        if m:
            praises.append((name, m.group(0), tip))

    art = check_article(text)
    if art:
        kind, snippet, tip = art
        if kind == "PRAISE":
            praises.append(("article (a/an)", snippet, tip))
        else:
            mistakes.append(("article (a/an)", snippet, tip))

    redundant = check_redundant_adverb(text)
    if redundant:
        word, tip = redundant
        mistakes.append(("redundant repetition", word, tip))

    if mistakes:
        name, snippet, tip = mistakes[0]
        extra = f" (+{len(mistakes) - 1} more)" if len(mistakes) > 1 else ""
        flash_red()
        banner(f"🩸 English slip - {name}{extra}: \"{snippet.strip()}\" -> {tip}")
    elif praises:
        name, snippet, tip = praises[0]
        extra = f" (+{len(praises) - 1} more)" if len(praises) > 1 else ""
        banner(f"✅ Nice - {name}{extra}: \"{snippet.strip()}\" -> {tip}")


if __name__ == "__main__":
    main()
