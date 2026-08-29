-- VP-2 phase 3: versioned lens output for captured voice turns.
-- ADDITIVE ONLY. hot_layer (raw, Layer 1) is never updated or deleted; every
-- lens re-run INSERTS a new lens_rev row (rev law: stack, never overwrite).
-- DO NOT APPLY until Rook acks this DDL in the agent room.

create table if not exists voice_transcript_lens (
  id uuid primary key default gen_random_uuid(),
  hot_layer_id uuid not null references hot_layer(id),
  lens_rev text not null,                       -- dated label, e.g. 'lens · 2026-08-29 16:02 UTC'
  lens_model text not null,                     -- e.g. 'superwhisper/s1-mini-GGUF:s1-mini-q4_k_m.gguf'
  lexicon_label text not null,                  -- dated lexicon snapshot used
  cleaned_text text not null,
  entities_snapped jsonb not null default '[]'::jsonb,  -- every snap/flag decision, auditable
  processing_metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (hot_layer_id, lens_rev)
);

comment on table voice_transcript_lens is
  'VP-2 phase 3 lens output. Raw transcript stays in hot_layer untouched; unknown phrases are kept verbatim and flagged, never coined into entities.';

-- No UPDATE/DELETE path is part of the design; grants should be INSERT+SELECT only.
