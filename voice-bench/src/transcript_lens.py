"""VP-2 phase 3: entity-aware transcript-normalizer lens (S1-mini).

Reads captured voice turns (read-only), produces a cleaned transcript grounded
in the known-entity lexicon, and writes VERSIONED lens rows only — the raw
hot_layer row is never updated, and re-runs stack new lens_rev rows.

Grounding law (agent_chat b2edaf3a): the lens may snap a garbled phrase to an
entity the lexicon knows, and must otherwise leave the phrase verbatim and
flag it UNKNOWN — it never invents a new proper noun.

Two stages per turn:
1. S1-mini rewrite — superwhisper/s1-mini-GGUF (s1-mini-q4_k_m.gguf, 484 MB)
   through llama-cpp-python, prompted with the lexicon so cleanup is grounded.
   Downloads/runs on Gammy; this module lazy-imports llama_cpp.
2. Deterministic entity snap — fuzzy match capitalized/unknown phrases against
   the lexicon (difflib, cutoff 0.84). Auditable independent of the model;
   every decision lands in entities_snapped.

Run:  python src/transcript_lens.py --dry-run          (print, write nothing)
      python src/transcript_lens.py --limit 20         (write lens rows)
Env:  NOVACORE_SUPABASE_URL / NOVACORE_SUPABASE_KEY    (same as voice_capture)
      S1_MINI_GGUF   path to the .gguf (default models/s1-mini/s1-mini-q4_k_m.gguf)
The voice_transcript_lens table must exist first — DDL in sql/, which ships
only after Rook acks it in the room.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib import request

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GGUF = REPO_ROOT / "models" / "s1-mini" / "s1-mini-q4_k_m.gguf"

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lexicon import Lexicon  # noqa: E402

SNAP_CUTOFF = 0.78
# Runs of capitalized words (with optional joiners) — candidate entity mentions.
MENTION_RE = re.compile(r"\b[A-Z][\w']*(?:[-/ ](?:[A-Z][\w']*|\d[\w-]*))*\b")


@dataclass
class SnapDecision:
    heard: str
    snapped_to: str | None
    score: float
    action: str  # "snapped" | "exact" | "unknown-kept-verbatim"


class EntitySnapper:
    """Deterministic grounding pass; never invents, only snaps or flags."""

    def __init__(self, lexicon: Lexicon):
        self._lexicon = lexicon
        self._by_lower = {t.lower(): t for t in lexicon.terms}

    def snap(self, text: str) -> tuple[str, list[SnapDecision]]:
        decisions: list[SnapDecision] = []

        def replace(match: re.Match[str]) -> str:
            mention = match.group(0)
            low = mention.lower()
            if low in self._by_lower:
                canonical = self._by_lower[low]
                if canonical != mention:
                    decisions.append(SnapDecision(mention, canonical, 1.0, "exact"))
                    return canonical
                return mention
            close = difflib.get_close_matches(low, self._by_lower.keys(), n=1, cutoff=SNAP_CUTOFF)
            if close:
                canonical = self._by_lower[close[0]]
                score = difflib.SequenceMatcher(None, low, close[0]).ratio()
                decisions.append(SnapDecision(mention, canonical, round(score, 3), "snapped"))
                return canonical
            # Flag only entity-shaped unknowns (multi-word, hyphenated, or with
            # digits). Ordinary sentence-initial capitals pass through silently.
            if " " in mention or "-" in mention or any(c.isdigit() for c in mention):
                decisions.append(SnapDecision(mention, None, 0.0, "unknown-kept-verbatim"))
            return mention

        return MENTION_RE.sub(replace, text), decisions


class S1MiniCleaner:
    """Grounded rewrite through the S1-mini GGUF (llama-cpp-python)."""

    def __init__(self, gguf_path: Path, lexicon: Lexicon):
        from llama_cpp import Llama  # lazy: only needed where the model lives

        self._llm = Llama(model_path=str(gguf_path), n_ctx=4096, verbose=False)
        self._lexicon = lexicon

    def clean(self, raw: str) -> str:
        prompt = (
            "Clean up this speech-to-text transcript: fix punctuation, casing and "
            "obvious mis-hearings. Known entity names you may use (never invent "
            "names not on this list — leave anything else exactly as heard): "
            + "; ".join(self._lexicon.terms)
            + f"\n\nTranscript: {raw}\n\nCleaned transcript:"
        )
        out = self._llm(prompt, max_tokens=512, temperature=0.0, stop=["\n\n"])
        return out["choices"][0]["text"].strip()


class PassthroughCleaner:
    """Stand-in where the GGUF is absent (tests, this build container)."""

    def clean(self, raw: str) -> str:
        return raw


@dataclass
class LensRunner:
    cleaner: object
    snapper: EntitySnapper
    lexicon_label: str
    lens_model: str
    dry_run: bool = True
    written: int = field(default=0)

    def _rest(self, method: str, path: str, body: dict | None = None) -> list | dict:
        url = os.environ["NOVACORE_SUPABASE_URL"].rstrip("/") + path
        key = os.environ["NOVACORE_SUPABASE_KEY"]
        data = json.dumps(body).encode() if body is not None else None
        req = request.Request(
            url,
            data=data,
            method=method,
            headers={
                "apikey": key,
                "Authorization": "Bearer " + key,
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
        )
        with request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}

    def fetch_turns(self, limit: int) -> list[dict]:
        """Voice turns, read-only, newest first (source_type carries voice dye)."""
        return self._rest(
            "GET",
            "/rest/v1/hot_layer?select=id,role,full_content,created_at"
            "&source_type=like.*voice*"
            f"&order=created_at.desc&limit={limit}",
        )

    def process(self, turn: dict) -> dict:
        cleaned = self.cleaner.clean(turn["full_content"] or "")
        cleaned, decisions = self.snapper.snap(cleaned)
        row = {
            "hot_layer_id": turn["id"],
            "lens_rev": f"lens · {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
            "lens_model": self.lens_model,
            "lexicon_label": self.lexicon_label,
            "cleaned_text": cleaned,
            "entities_snapped": [d.__dict__ for d in decisions],
        }
        if self.dry_run:
            print(json.dumps(row, indent=2, ensure_ascii=False))
        else:
            self._rest("POST", "/rest/v1/voice_transcript_lens", row)
            self.written += 1
        return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--gguf", type=Path, default=Path(os.getenv("S1_MINI_GGUF", DEFAULT_GGUF)))
    args = parser.parse_args()

    lexicon = Lexicon.from_snapshot()
    snapper = EntitySnapper(lexicon)
    if args.gguf.is_file():
        cleaner: object = S1MiniCleaner(args.gguf, lexicon)
        model_name = f"superwhisper/s1-mini-GGUF:{args.gguf.name}"
    else:
        print(f"NOTE: {args.gguf} absent — passthrough cleaner (snap-only run)")
        cleaner = PassthroughCleaner()
        model_name = "passthrough+entity-snap"

    runner = LensRunner(cleaner, snapper, lexicon.label, model_name, dry_run=args.dry_run)
    turns = runner.fetch_turns(args.limit)
    for turn in turns:
        runner.process(turn)
    print(f"{len(turns)} turns processed, {runner.written} lens rows written "
          f"(lexicon: {lexicon.label})")


if __name__ == "__main__":
    main()
