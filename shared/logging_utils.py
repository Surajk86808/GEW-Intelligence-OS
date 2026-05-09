from __future__ import annotations

import csv
import time
import traceback
from contextlib import nullcontext
from pathlib import Path
from typing import Iterable

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn
from rich.rule import Rule
from rich.table import Table


class TerminalUI:
    def __init__(
        self,
        runtime_log_path: Path,
        *,
        quiet: bool = False,
        minimal_ui: bool = False,
        log_to_console: bool = True,
    ) -> None:
        self.console = Console(record=True)
        self.runtime_log_path = runtime_log_path
        self.quiet = quiet
        self.minimal_ui = minimal_ui
        self.log_to_console = log_to_console
        self.runtime_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.runtime_log_path.write_text("", encoding="utf-8")

    def rule(self, title: str, style: str = "cyan") -> None:
        timestamped = f"{self._now()} | {title}"
        if self.log_to_console and not self.minimal_ui and not self.quiet:
            self.console.print(Rule(title, style=style))
        self._append_log_line(timestamped)

    def info(self, message: str, *, echo_to_console: bool = True) -> None:
        self._log("INFO", message, "bold blue", echo_to_console=echo_to_console)

    def success(self, message: str) -> None:
        self._log("SUCCESS", message, "bold green")

    def warning(self, message: str) -> None:
        self._log("WARNING", message, "bold yellow")

    def error(self, message: str) -> None:
        self._log("ERROR", message, "bold red")

    def step(self, label: str, message: str, color: str = "bold cyan") -> None:
        self._log(label, message, color)

    def segment(self, start_seconds: float, text: str) -> None:
        timestamp = format_timestamp(start_seconds)
        if self.quiet:
            self._append_log_line(f"{self._now()} | SEGMENT | [{timestamp}] {text}")
            return
        if self.log_to_console and not self.minimal_ui:
            self.console.print(f"[cyan][{timestamp}][/cyan] {text}")
        self._append_log_line(f"{self._now()} | SEGMENT | [{timestamp}] {text}")

    def exception(self, context: str, reason: str, exc: BaseException) -> str:
        stack_trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        if self.log_to_console:
            self.console.print(f"[bold red][ERROR][/bold red] {context}")
            self.console.print(f"[bold red]Reason:[/bold red] {reason}")
            if not self.minimal_ui:
                self.console.print(Panel(stack_trace, title="Stack Trace", border_style="red", expand=False))
        self._append_log_line(f"{self._now()} | ERROR | {context} | {reason}")
        self._append_log_line(stack_trace.rstrip())
        return stack_trace

    def summary(self, title: str, rows: list[tuple[str, str]], status: str = "SUCCESS") -> None:
        table = Table(show_header=False, box=None, padding=(0, 1))
        for key, value in rows:
            table.add_row(f"[bold]{key}[/bold]", value)
        border_style = "green" if status.upper() == "SUCCESS" else "red"
        if self.log_to_console and not self.quiet:
            if self.minimal_ui:
                self.console.print(f"[{status}] {title}: " + ", ".join(f"{key}={value}" for key, value in rows))
            else:
                self.console.print(Panel(table, title=title, border_style=border_style, expand=False))
        self._append_log_line(f"{self._now()} | {status.upper()} | {title} | " + " | ".join(f"{key}={value}" for key, value in rows))

    def build_progress(self) -> Progress:
        if self.quiet or self.minimal_ui or not self.log_to_console:
            return nullcontext(_NullProgress())
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=None),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=self.console,
            transient=False,
        )

    def _log(self, level: str, message: str, color: str, *, echo_to_console: bool = True) -> None:
        if self.log_to_console and echo_to_console and not self.quiet:
            if self.minimal_ui:
                self.console.print(f"[{level}] {message}")
            else:
                self.console.print(f"[{color}][{level}][/{color}] {message}")
        self._append_log_line(f"{self._now()} | {level} | {message}")

    def _append_log_line(self, message: str) -> None:
        with self.runtime_log_path.open("a", encoding="utf-8") as handle:
            handle.write(message + "\n")

    def _now(self) -> str:
        return time.strftime("%Y-%m-%d %H:%M:%S")


class _NullProgress:
    def add_task(self, _description: str, total: int = 0) -> dict[str, int]:
        return {"total": total, "completed": 0}

    def advance(self, task: dict[str, int], advance: int = 1) -> None:
        task["completed"] = int(task.get("completed", 0)) + advance


def initialize_csv_log(log_path: Path, headers: list[str], overwrite: bool = False) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if log_path.exists() and not overwrite:
        return
    with log_path.open("w", newline="", encoding="utf-8") as handle:
        csv.DictWriter(handle, fieldnames=headers).writeheader()


def append_csv_row(log_path: Path, headers: list[str], row: dict[str, str]) -> None:
    initialize_csv_log(log_path, headers)
    with log_path.open("a", newline="", encoding="utf-8") as handle:
        csv.DictWriter(handle, fieldnames=headers).writerow(row)


def write_csv_rows(log_path: Path, headers: list[str], rows: Iterable[dict[str, str]]) -> None:
    initialize_csv_log(log_path, headers, overwrite=True)
    with log_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        for row in rows:
            writer.writerow(row)


def format_timestamp(seconds: float) -> str:
    total_seconds = max(int(seconds), 0)
    minutes, remaining_seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{remaining_seconds:02d}"
