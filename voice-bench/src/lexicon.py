"""Known-entity lexicon for the VP-2 phase-3 transcript lens.

The amendment (agent_chat b2edaf3a) requires entity-aware grounding: cleaned
transcripts snap to entities the NovaCore graph actually knows, and NEVER coin
new proper nouns (the "Quad-Voice" lesson — an unknown phrase stays verbatim
and gets flagged, it does not become an entity).

Sources, merged into one flat term list with a dated label (rev letters are
retired — labels are date/time of save):
- newest blueprint_revs row: node titles, node ids, ticket ids
- agent seat names, machine names, project stack vocabulary
A snapshot JSON in lexicon/ makes runs reproducible; refresh_from_wingman()
rebuilds a new dated snapshot from the live newest rev (read-only).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib import request

REPO_ROOT = Path(__file__).resolve().parent.parent
LEXICON_DIR = REPO_ROOT / "lexicon"


@dataclass(frozen=True)
class Lexicon:
    label: str
    terms: tuple[str, ...]

    @classmethod
    def from_snapshot(cls, path: Path | None = None) -> "Lexicon":
        """Load the newest snapshot in lexicon/ (or an explicit file)."""
        if path is None:
            snapshots = sorted(LEXICON_DIR.glob("lexicon_snapshot_*.json"))
            if not snapshots:
                raise FileNotFoundError(f"no lexicon snapshots in {LEXICON_DIR}")
            path = snapshots[-1]
        payload = json.loads(path.read_text(encoding="utf-8"))
        terms: list[str] = []
        for group in payload["entities"].values():
            terms.extend(t for t in group if isinstance(t, str) and t.strip())
        # Dedupe case-insensitively, keep first casing seen.
        seen: dict[str, str] = {}
        for term in terms:
            seen.setdefault(term.lower(), term)
        return cls(label=payload["label"], terms=tuple(seen.values()))


def refresh_from_wingman() -> Path:
    """Rebuild a dated snapshot from the live newest blueprint_revs row.

    Read-only against Wingman via PostgREST; requires NOVACORE_SUPABASE_URL and
    NOVACORE_SUPABASE_KEY (same env contract as voice_capture). Static vocab is
    carried over from the previous snapshot.
    """
    url = os.environ["NOVACORE_SUPABASE_URL"].rstrip("/")
    key = os.environ["NOVACORE_SUPABASE_KEY"]
    req = request.Request(
        url + "/rest/v1/blueprint_revs?select=id,rev_label,data&order=saved_at.desc&limit=1",
        headers={"apikey": key, "Authorization": "Bearer " + key},
    )
    with request.urlopen(req, timeout=30) as resp:
        row = json.loads(resp.read().decode())[0]

    previous = Lexicon.from_snapshot()  # noqa: F841 — proves a base snapshot exists
    base = json.loads(sorted(LEXICON_DIR.glob("lexicon_snapshot_*.json"))[-1].read_text())
    data = row["data"]
    base["entities"]["node_titles"] = sorted(
        {n["title"] for n in data.get("nodes", []) if n.get("title")}
    )
    base["entities"]["node_ids"] = sorted(
        {n["id"] for n in data.get("nodes", []) if n.get("id")}
    )
    base["entities"]["ticket_ids"] = sorted(
        {i["id"] for g in data.get("tickets", []) for i in g.get("items", []) if i.get("id")}
    )
    stamp = datetime.now(timezone.utc)
    base["label"] = f"lexicon · {stamp:%Y-%m-%d %H:%M} UTC"
    base["sources"]["blueprint_revs_row"] = row["id"]
    base["sources"]["blueprint_rev_label"] = row["rev_label"]

    out = LEXICON_DIR / f"lexicon_snapshot_{stamp:%Y-%m-%dT%H%M}Z.json"
    out.write_text(json.dumps(base, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out
