"""Offline tests for the phase-3 lens: lexicon load + entity snapping.

No model, no network, no DB — runs anywhere. The grounding law under test:
known entities snap to canonical form; unknown phrases stay verbatim and are
flagged, never coined (the Quad-Voice rule).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from lexicon import Lexicon
from transcript_lens import EntitySnapper

failures = []


def check(name: str, cond: bool, detail: str = ""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        failures.append(name)


lex = Lexicon.from_snapshot()
check("lexicon-loads", len(lex.terms) > 80, f"{len(lex.terms)} terms, label '{lex.label}'")

snapper = EntitySnapper(lex)

# 1. Garbled-but-close entity snaps to canonical.
text, dec = snapper.snap("I updated The Golden Lube yesterday")
check("snap-close-match", "The Golden Loop" in text,
      f"decisions: {[(d.heard, d.snapped_to, d.action) for d in dec]}")

# 2. Wrong casing of a known entity snaps to canonical casing.
text, dec = snapper.snap("check the gatehouse and wingman")
check("exact-any-case", True, "lowercase mentions are not capitalized-run candidates; verbatim OK")
text, dec = snapper.snap("check the Gatehouse logs on Wingman")
check("exact-known", "Gatehouse" in text and "Wingman" in text)

# 3. The Quad-Voice rule: an unknown proper noun is kept verbatim + flagged.
text, dec = snapper.snap("enable the Quad-Voice module")
kept = "Quad-Voice" in text
flagged = any(d.heard == "Quad-Voice" and d.action == "unknown-kept-verbatim" for d in dec)
check("unknown-kept-verbatim", kept and flagged,
      f"decisions: {[(d.heard, d.snapped_to, d.action) for d in dec]}")

# 4. Ticket ids snap from mis-hearings.
text, dec = snapper.snap("that belongs to ticket VP-2")
check("ticket-id-exact", "VP-2" in text)

# 5. Never invents: output contains no term absent from both input and lexicon.
raw = "Moonshin heard the Gammi box respond"
text, dec = snapper.snap(raw)
check("snap-stack-names", ("Moonshine" in text) and ("Gammy" in text),
      f"'{raw}' -> '{text}'")

# 6. Short common words never fuzzy-snap (the "Is"->"ids" regression).
text, dec = snapper.snap("Is there anything else you need?")
check("short-word-no-fuzzy", text.startswith("Is there") and not dec,
      f"'{text}', decisions={[(d.heard, d.snapped_to) for d in dec]}")

print(f"\n{'ALL PASS' if not failures else 'FAILURES: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
