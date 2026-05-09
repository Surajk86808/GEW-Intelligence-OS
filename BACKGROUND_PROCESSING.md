# GEW Background Processing

## What this supports

The GEW local batch pipeline now supports long-running Windows-native background transcription runs for Phase 2.

Recommended command:

```powershell
python main.py --background --resume
```

You can also launch the detached helper:

```powershell
run_background.bat
```

## What keeps running

When Phase 2 is active, the pipeline is designed to keep running locally if:

- the screen turns off
- the display sleeps
- Windows is locked
- the terminal is minimized
- the terminal loses focus

This works because the process stays alive on the local machine and Phase 2 now calls the Windows execution-state API to prevent full system sleep during active processing.

## What still stops processing

The batch does **not** continue if the whole laptop enters:

- full system sleep
- hibernation
- shutdown
- forced reboot

Important distinction:

- `screen off` or `display sleep` means the machine is still awake, so processing continues
- `system sleep` means the CPU/GPU stop running, so transcription stops

Keep the laptop lid open during overnight runs unless you already use a Windows power plan that avoids sleep with the lid open.

## How background mode works

`--background` enables a long-duration batch mode that:

- reduces Rich console redraw overhead
- minimizes terminal dependency
- writes progress to files after every completed call
- records failures without stopping the whole run
- keeps one Whisper model loaded and reused across the batch
- logs runtime diagnostics on an interval

Useful flags:

- `--background`: background-safe batch mode
- `--resume`: skip already completed calls and continue the remaining queue
- `--minimal-ui`: lightweight console output
- `--quiet`: even less console output, while logs still update
- `--no-console`: file logging only
- `--keep-display-awake`: prevent display sleep too

## Progress and logs

Phase 2 now writes durable state and logs here:

- `phase_2_transcription/logs/transcription.log`
- `phase_2_transcription/logs/failures.log`
- `phase_2_transcription/logs/runtime_metrics.log`
- `phase_2_transcription/logs/progress.log`
- `phase_2_transcription/logs/runtime_terminal.log`
- `phase_2_transcription/outputs/state/processed_calls.json`
- `phase_2_transcription/outputs/state/processing.lock`

Checkpoint behavior:

- each successful call is written to `processed_calls.json`
- completed transcript files are detected during `--resume`
- the transcript manifest is rebuilt from completed outputs
- failed files are logged and the batch moves on

## Resume workflow

If a run is interrupted:

```powershell
python main.py --background --resume
```

Resume mode will:

- read `processed_calls.json`
- detect already existing transcript and metadata files
- skip completed calls
- process only the remaining queue

## Safe shutdown

If you press `Ctrl+C`, the pipeline now:

- marks the run as interrupted
- preserves checkpoint state
- restores Windows sleep behavior
- releases the processing lock

After that, restart with `--resume`.

## Runtime diagnostics

`runtime_metrics.log` records periodic snapshots for:

- CPU usage
- RAM usage
- GPU usage when `nvidia-smi` is available
- VRAM usage when `nvidia-smi` is available
- processing speed
- estimated remaining time

The pipeline also warns about:

- low battery
- low disk space
- high GPU temperature when readable from `nvidia-smi`

## Recommended Windows settings

For overnight local processing:

1. Keep the laptop plugged in.
2. Keep the lid open.
3. Use a power mode that does not put the PC to sleep while plugged in.
4. Allow the display to turn off if you want; that is safe.
5. Make sure enough disk space is available for logs and outputs.

## Troubleshooting

If the batch does not continue overnight:

1. Check whether Windows put the entire system to sleep rather than only turning the screen off.
2. Check `phase_2_transcription/logs/runtime_terminal.log` and `failures.log`.
3. Check whether a stale `processing.lock` exists from an older crashed run.
4. Confirm the laptop was plugged in and not battery-limited.
5. Confirm the GPU driver still exposes `nvidia-smi` if you expect GPU metrics.

If a single file is corrupted:

- the failure is logged
- the rest of the batch continues
- you can repair or remove the bad file and rerun with `--resume`

## For future batch AI phases

The shared Windows batch runtime lives in [shared/batch_runtime.py](/p:/Gew/shared/batch_runtime.py) and can be reused by later phases for:

- sleep prevention
- process locking
- checkpoint persistence
- runtime metrics
- graceful interruption
- post-item cleanup
