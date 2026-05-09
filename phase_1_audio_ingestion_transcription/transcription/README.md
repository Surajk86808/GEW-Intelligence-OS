Phase 2 is now the GEW transcript infrastructure layer.

Supported modes:

- Native ASR: audio -> Faster-Whisper -> normalized transcript -> structured JSON
- External ingestion: transcript files -> parsing -> normalization -> structured JSON
- Hybrid: ingest external transcripts first, then use ASR only for remaining calls

Primary Phase 2 outputs:

- `outputs/transcripts/*.txt`
- `outputs/transcripts/*.metadata.json`
- `structured_output/CALL_XXXX.json`
- `outputs/metadata/transcript_manifest.json`
- `outputs/metadata/transcript_catalog.json`

External transcript support includes:

- combined transcript batches such as `transcripts/transcript from gemini/ALL_CALLS_COMBINED.txt`
- per-call Gemini transcript files
- future manual or imported transcript files passed through the CLI

Recommended hybrid run:

```powershell
python main.py --mode hybrid --background --resume
```

External-only run:

```powershell
python main.py --mode external --background --resume
```
