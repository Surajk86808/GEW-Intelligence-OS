from __future__ import annotations

import atexit
import ctypes
import gc
import os
import shutil
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from shared.json_utils import read_json, write_json

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
ES_AWAYMODE_REQUIRED = 0x00000040


@dataclass
class RuntimeOptions:
    background: bool = False
    resume: bool = False
    quiet: bool = False
    minimal_ui: bool = False
    allow_display_sleep: bool = True
    metrics_interval_seconds: int = 30


class SleepInhibitor:
    def __init__(self, enabled: bool, logger: Any | None = None, allow_display_sleep: bool = True) -> None:
        self.enabled = enabled and os.name == "nt"
        self.logger = logger
        self.allow_display_sleep = allow_display_sleep
        self._kernel32 = ctypes.windll.kernel32 if self.enabled else None
        self._active = False

    def activate(self) -> None:
        if not self.enabled or self._kernel32 is None or self._active:
            return
        flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        if self.allow_display_sleep:
            flags |= ES_AWAYMODE_REQUIRED
        else:
            flags |= ES_DISPLAY_REQUIRED
        result = self._kernel32.SetThreadExecutionState(flags)
        if result == 0:
            raise OSError("SetThreadExecutionState failed while enabling long-running batch protection.")
        self._active = True
        atexit.register(self.restore)
        if self.logger:
            self.logger.info("Windows sleep prevention enabled for active processing. Display sleep and lock are still allowed.")

    def restore(self) -> None:
        if not self.enabled or self._kernel32 is None or not self._active:
            return
        self._kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        self._active = False
        if self.logger:
            self.logger.info("Windows sleep prevention restored to normal system behavior.")


class ProcessLock:
    def __init__(self, lock_path: Path, metadata: dict[str, Any]) -> None:
        self.lock_path = lock_path
        self.metadata = metadata
        self.acquired = False

    def acquire(self) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        if self.lock_path.exists():
            existing = read_json(self.lock_path, default={}) or {}
            existing_pid = int(existing.get("pid", 0) or 0)
            if existing_pid and _pid_exists(existing_pid):
                raise RuntimeError(
                    f"Another batch run is already active (pid={existing_pid}). Remove {self.lock_path.name} only if that run is no longer alive."
                )
        payload = dict(self.metadata)
        payload["pid"] = os.getpid()
        payload["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        write_json(self.lock_path, payload)
        self.acquired = True
        atexit.register(self.release)

    def release(self) -> None:
        if self.acquired and self.lock_path.exists():
            self.lock_path.unlink()
        self.acquired = False


class ProgressTracker:
    def __init__(self, progress_path: Path, phase_name: str) -> None:
        self.progress_path = progress_path
        self.phase_name = phase_name
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)
        self._payload = read_json(progress_path, default=None) or self._default_payload()

    def _default_payload(self) -> dict[str, Any]:
        return {
            "phase": self.phase_name,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "status": "initialized",
            "total_calls": 0,
            "processed_calls": [],
            "failed_calls": [],
            "skipped_calls": [],
            "active_call_id": "",
            "last_error": "",
        }

    @property
    def payload(self) -> dict[str, Any]:
        return self._payload

    def initialize(self, total_calls: int, resume: bool) -> None:
        if not resume:
            self._payload = self._default_payload()
        self._payload["total_calls"] = total_calls
        self._payload["status"] = "running"
        self._payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.save()

    def mark_active(self, call_id: str) -> None:
        self._payload["active_call_id"] = call_id
        self._payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.save()

    def mark_success(self, call_id: str) -> None:
        self._append_unique("processed_calls", call_id)
        self._remove_value("failed_calls", call_id)
        self._remove_value("skipped_calls", call_id)
        self._payload["active_call_id"] = ""
        self._payload["last_error"] = ""
        self._payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.save()

    def mark_failure(self, call_id: str, error_message: str) -> None:
        self._append_unique("failed_calls", call_id)
        self._payload["active_call_id"] = ""
        self._payload["last_error"] = error_message
        self._payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.save()

    def mark_skipped(self, call_id: str) -> None:
        self._append_unique("skipped_calls", call_id)
        self._payload["active_call_id"] = ""
        self._payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.save()

    def finalize(self, status: str) -> None:
        self._payload["status"] = status
        self._payload["active_call_id"] = ""
        self._payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.save()

    def processed_set(self) -> set[str]:
        return set(str(item) for item in self._payload.get("processed_calls", []))

    def failed_set(self) -> set[str]:
        return set(str(item) for item in self._payload.get("failed_calls", []))

    def save(self) -> None:
        write_json(self.progress_path, self._payload)

    def _append_unique(self, key: str, value: str) -> None:
        values = [str(item) for item in self._payload.get(key, [])]
        if value not in values:
            values.append(value)
            self._payload[key] = values

    def _remove_value(self, key: str, value: str) -> None:
        self._payload[key] = [str(item) for item in self._payload.get(key, []) if str(item) != value]


class ShutdownController:
    def __init__(self, tracker: ProgressTracker, logger: Any | None = None) -> None:
        self.tracker = tracker
        self.logger = logger
        self.stop_requested = threading.Event()
        self._installed = False

    def install(self) -> None:
        if self._installed:
            return
        self._installed = True
        for signum in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(signum, self._handle_signal)
            except (ValueError, AttributeError):
                continue

    def _handle_signal(self, signum: int, _frame: Any) -> None:
        if self.logger:
            self.logger.warning(f"Shutdown signal received ({signum}). Finishing current file, saving state, and exiting cleanly.")
        self.stop_requested.set()
        self.tracker.finalize("interrupted")

    def raise_if_requested(self) -> None:
        if self.stop_requested.is_set():
            raise KeyboardInterrupt("Shutdown requested.")


class RuntimeMetricsMonitor:
    def __init__(
        self,
        metrics_path: Path,
        total_items: int,
        processed_counter: Callable[[], int],
        started_at: float,
        logger: Any | None = None,
        interval_seconds: int = 30,
    ) -> None:
        self.metrics_path = metrics_path
        self.total_items = total_items
        self.processed_counter = processed_counter
        self.started_at = started_at
        self.logger = logger
        self.interval_seconds = max(interval_seconds, 5)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._cpu_sampler = CpuSampler()

    def start(self) -> None:
        self.metrics_path.parent.mkdir(parents=True, exist_ok=True)
        self._thread = threading.Thread(target=self._run, name="runtime-metrics", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        while not self._stop_event.wait(self.interval_seconds):
            line = self._build_metrics_line()
            with self.metrics_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
            if self.logger:
                self.logger.info(line, echo_to_console=False)

    def _build_metrics_line(self) -> str:
        processed = self.processed_counter()
        elapsed = max(time.perf_counter() - self.started_at, 0.001)
        items_per_minute = processed / elapsed * 60
        eta_minutes = ((self.total_items - processed) / items_per_minute) if items_per_minute > 0 else None
        process_memory_mb = get_process_memory_mb()
        system_memory = get_system_memory_snapshot()
        cpu_percent = self._cpu_sampler.sample()
        gpu_snapshot = get_gpu_snapshot()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        eta_text = f"{eta_minutes:.2f}m" if eta_minutes is not None else "unknown"
        return (
            f"{timestamp} | processed={processed}/{self.total_items}"
            f" | speed={items_per_minute:.2f} items/min"
            f" | eta={eta_text}"
            f" | cpu={cpu_percent:.1f}%"
            f" | ram_process={process_memory_mb:.1f}MB"
            f" | ram_system_used={system_memory['used_mb']:.1f}MB/{system_memory['total_mb']:.1f}MB"
            f" | gpu={gpu_snapshot['gpu_utilization']}"
            f" | vram={gpu_snapshot['vram_used']}/{gpu_snapshot['vram_total']}"
        )


class CpuSampler:
    def __init__(self) -> None:
        self._last_idle = None
        self._last_total = None

    def sample(self) -> float:
        idle, kernel, user = _read_system_times()
        total = kernel + user
        if self._last_idle is None or self._last_total is None:
            self._last_idle = idle
            self._last_total = total
            return 0.0
        idle_delta = idle - self._last_idle
        total_delta = total - self._last_total
        self._last_idle = idle
        self._last_total = total
        if total_delta <= 0:
            return 0.0
        busy = max(total_delta - idle_delta, 0)
        return busy / total_delta * 100


def run_cleanup(logger: Any | None = None) -> None:
    collected = gc.collect()
    if logger:
        logger.info(f"Post-file cleanup completed. Garbage collector reclaimed {collected} objects.", echo_to_console=False)


def collect_runtime_warnings(min_disk_free_gb: float = 5.0) -> list[str]:
    warnings: list[str] = []
    battery = get_battery_snapshot()
    if battery["present"] and not battery["plugged_in"] and battery["percent"] is not None and battery["percent"] <= 25:
        warnings.append(f"Battery is low at {battery['percent']}%. Plug in the laptop for overnight processing stability.")
    free_gb = get_free_disk_gb(Path.cwd())
    if free_gb < min_disk_free_gb:
        warnings.append(f"Only {free_gb:.2f} GB of free disk space remains. Large batch jobs may fail or stall.")
    gpu_snapshot = get_gpu_snapshot()
    temperature = gpu_snapshot.get("temperature")
    if temperature not in (None, "", "n/a"):
        try:
            numeric_temperature = float(str(temperature).replace("C", "").strip())
            if numeric_temperature >= 85:
                warnings.append(f"GPU temperature is {numeric_temperature:.0f}C. Thermal throttling may reduce overnight throughput.")
        except ValueError:
            pass
    return warnings


def get_free_disk_gb(path: Path) -> float:
    usage = shutil.disk_usage(path)
    return usage.free / (1024 ** 3)


def get_process_memory_mb() -> float:
    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    process = ctypes.windll.kernel32.GetCurrentProcess()
    success = ctypes.windll.psapi.GetProcessMemoryInfo(process, ctypes.byref(counters), counters.cb)
    if not success:
        return 0.0
    return counters.WorkingSetSize / (1024 ** 2)


def get_system_memory_snapshot() -> dict[str, float]:
    class MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatusEx()
    status.dwLength = ctypes.sizeof(status)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
    total_mb = status.ullTotalPhys / (1024 ** 2)
    available_mb = status.ullAvailPhys / (1024 ** 2)
    return {
        "total_mb": total_mb,
        "available_mb": available_mb,
        "used_mb": total_mb - available_mb,
    }


def get_battery_snapshot() -> dict[str, Any]:
    class SystemPowerStatus(ctypes.Structure):
        _fields_ = [
            ("ACLineStatus", ctypes.c_byte),
            ("BatteryFlag", ctypes.c_byte),
            ("BatteryLifePercent", ctypes.c_byte),
            ("Reserved1", ctypes.c_byte),
            ("BatteryLifeTime", ctypes.c_ulong),
            ("BatteryFullLifeTime", ctypes.c_ulong),
        ]

    status = SystemPowerStatus()
    success = ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status))
    if not success:
        return {"present": False, "plugged_in": None, "percent": None}
    battery_present = status.BatteryFlag != 128
    percent = None if status.BatteryLifePercent == 255 else int(status.BatteryLifePercent)
    return {
        "present": battery_present,
        "plugged_in": status.ACLineStatus == 1,
        "percent": percent,
    }


def get_gpu_snapshot() -> dict[str, str]:
    command = [
        "nvidia-smi",
        "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=3, check=False)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return {"gpu_utilization": "n/a", "vram_used": "n/a", "vram_total": "n/a", "temperature": "n/a"}
    if result.returncode != 0 or not result.stdout.strip():
        return {"gpu_utilization": "n/a", "vram_used": "n/a", "vram_total": "n/a", "temperature": "n/a"}
    first_line = result.stdout.strip().splitlines()[0]
    parts = [part.strip() for part in first_line.split(",")]
    if len(parts) < 4:
        return {"gpu_utilization": "n/a", "vram_used": "n/a", "vram_total": "n/a", "temperature": "n/a"}
    return {
        "gpu_utilization": f"{parts[0]}%",
        "vram_used": f"{parts[1]}MB",
        "vram_total": f"{parts[2]}MB",
        "temperature": f"{parts[3]}C",
    }


def _read_system_times() -> tuple[int, int, int]:
    class FileTime(ctypes.Structure):
        _fields_ = [("dwLowDateTime", ctypes.c_ulong), ("dwHighDateTime", ctypes.c_ulong)]

    idle = FileTime()
    kernel = FileTime()
    user = FileTime()
    success = ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user))
    if not success:
        return 0, 0, 0
    return _filetime_to_int(idle), _filetime_to_int(kernel), _filetime_to_int(user)


def _filetime_to_int(value: Any) -> int:
    return (int(value.dwHighDateTime) << 32) | int(value.dwLowDateTime)


def _pid_exists(pid: int) -> bool:
    try:
        process = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False
    return str(pid) in process.stdout
