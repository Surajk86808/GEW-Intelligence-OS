from __future__ import annotations

import shutil
from pathlib import Path
from typing import Tuple

import pandas as pd


def load_workbook_sheets(input_path: Path, combined_sheet: str, calls_sheet: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if not input_path.exists():
        raise FileNotFoundError(f"Input Excel file not found at: {input_path}")
    combined_df = pd.read_excel(input_path, sheet_name=combined_sheet, engine="openpyxl")
    calls_df = pd.read_excel(input_path, sheet_name=calls_sheet, engine="openpyxl")
    return combined_df, calls_df


def save_updated_workbook(
    combined_df: pd.DataFrame,
    calls_df: pd.DataFrame,
    output_path: Path,
    source_path: Path,
    combined_sheet: str,
    calls_sheet: str,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not output_path.exists() and source_path.exists() and source_path.resolve() != output_path.resolve():
        shutil.copy2(source_path, output_path)
        mode = "a"
    else:
        mode = "a" if output_path.exists() else "w"

    with pd.ExcelWriter(
        output_path,
        engine="openpyxl",
        mode=mode,
        if_sheet_exists="replace" if mode == "a" else None,
    ) as writer:
        combined_df.to_excel(writer, sheet_name=combined_sheet, index=False)
        calls_df.to_excel(writer, sheet_name=calls_sheet, index=False)

