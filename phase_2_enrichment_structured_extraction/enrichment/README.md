Phase 3 now operates as a transcript enrichment and voice intelligence layer.

It prefers transcript sources in this order:

1. manually corrected or manually reviewed enriched JSON
2. manually injected reviewed transcript files
3. enriched JSON transcripts
4. structured JSON transcripts
5. normalized TXT transcripts
6. raw per-call transcript TXT
7. combined transcript fallback blocks

Manual injection folders are now part of the architecture:

- `inputs/transcripts/`
- `inputs/enriched_json/`
- `inputs/manual_reviews/`
- `inputs/corrected_calls/`
- `inputs/external_imports/`

Supported manual file types:

- `.json`
- `.txt`
- `.md`

Manual review and corrected-call files override all automated versions for the same `CALL_XXXX`.

Phase 3 can now continue even when audio is unavailable.

When audio exists, it adds:

- emotion timeline
- silence analysis
- speaker balance
- acoustic metrics

When audio does not exist, it still adds:

- transcript enrichment
- CRM-linked metadata
- conversation intent tagging
- evidence-preserving segment annotations

Every enriched payload now includes `source_tracking` for auditability, including origin, pipeline stage, reviewed status, enrichment level, and source file path.

The transcript text is preserved. Enrichment adds metadata to each segment rather than replacing dialogue.
