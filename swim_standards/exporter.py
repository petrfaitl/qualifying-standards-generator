"""
Multi-format reporting engine: styled Excel workbook, standard CSV, and console tables.
"""

import csv
import os
from typing import List
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from .models import AggregatedStandard
from .parser import seconds_to_time


def export_to_csv(standards: List[AggregatedStandard], filepath: str) -> None:
    """
    Exports qualifying standards to a clean, machine-readable CSV format.
    """
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Event_Number",
            "Gender",
            "School_Year",
            "Distance_M",
            "Stroke",
            "Qualifying_Time",
            "Qualifying_Seconds"
        ])
        for idx, s in enumerate(standards, start=1):
            writer.writerow([
                idx,
                s.event_info.gender,
                s.event_info.school_year,
                s.event_info.distance,
                s.event_info.stroke,
                s.standard_time_str,
                f"{s.standard_seconds:.2f}"
            ])


def export_to_excel(standards: List[AggregatedStandard], filepath: str) -> None:
    """
    Generates a professionally formatted multi-sheet Excel workbook:
    - 'Qualifying Standards': Athlete/Coach distribution table.
    - 'Audit & Diagnostics': Full transparency trace of annual results and extrapolation methods.
    """
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    wb = Workbook()

    # ----------------------------------------------------
    # Sheet 1: Qualifying Standards
    # ----------------------------------------------------
    ws_standards = wb.active
    ws_standards.title = "Qualifying Standards"
    ws_standards.views.sheetView[0].showGridLines = True

    # Styling definitions
    title_font = Font(name="Segoe UI", size=15, bold=True, color="1F497D")
    subtitle_font = Font(name="Segoe UI", size=10, italic=True, color="595959")
    header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    data_font = Font(name="Segoe UI", size=10, color="000000")
    bold_data_font = Font(name="Segoe UI", size=10, bold=True, color="1F497D")

    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    alt_row_fill = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

    thin_border_side = Side(style="thin", color="D9D9D9")
    thin_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)

    # Title block
    target_rank_str = f"Rank {standards[0].target_rank} Benchmark" if standards else "Rank 8 Benchmark"
    ws_standards.append(["Regional Intermediate Schools Swimming Championships"])
    ws_standards.append([f"Official Regional Qualifying Standards ({target_rank_str})"])
    ws_standards.append([])

    ws_standards["A1"].font = title_font
    ws_standards["A2"].font = subtitle_font

    headers_standards = [
        "Event #", "School Year", "Gender", "Distance", "Stroke",
        "Qualifying Standard (Time)", "Standard (Seconds)"
    ]
    ws_standards.append(headers_standards)

    header_row_idx = 4
    for col_idx in range(1, len(headers_standards) + 1):
        cell = ws_standards.cell(row=header_row_idx, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for idx, s in enumerate(standards, start=1):
        row_num = header_row_idx + idx
        time_formatted = seconds_to_time(s.standard_seconds, format_mm_ss=True)
        ws_standards.append([
            idx,
            s.event_info.school_year,
            s.event_info.gender,
            f"{s.event_info.distance}m",
            s.event_info.stroke,
            time_formatted,
            f"{s.standard_seconds:.2f}"
        ])
        fill_to_use = alt_row_fill if idx % 2 == 0 else white_fill
        for c in range(1, len(headers_standards) + 1):
            cell = ws_standards.cell(row=row_num, column=c)
            cell.font = bold_data_font if c == 6 else data_font
            cell.fill = fill_to_use
            cell.border = thin_border
            if c in [1, 2, 3, 4]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif c == 5:
                cell.alignment = Alignment(horizontal="left", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="right", vertical="center")

    # ----------------------------------------------------
    # Sheet 2: Audit & Diagnostics
    # ----------------------------------------------------
    ws_audit = wb.create_sheet(title="Audit & Diagnostics")
    ws_audit.views.sheetView[0].showGridLines = True

    audit_header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    extrap_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")

    # Identify all distinct years across standards
    all_years = sorted(list({yr for s in standards for yr in s.annual_results.keys() if yr > 0}))
    years_summary = ", ".join(str(y) for y in all_years) if all_years else "Multi-Year"

    ws_audit.append(["Qualifying Standards - Comprehensive Audit & Extrapolation Trace"])
    ws_audit.append([f"Mathematical diagnostics across historical meet archives ({years_summary})"])
    ws_audit.append([])

    headers_audit = ["Event #", "Event Description", "Target Rank"]
    for yr in all_years:
        headers_audit.extend([f"{yr} Target Time", f"{yr} Swimmers", f"{yr} Audit Flag"])
    headers_audit.extend(["Combination", "Standard (Time)", "Standard (s)", "Std Dev (s)"])

    ws_audit.append(headers_audit)
    audit_header_row = 4

    for col_idx in range(1, len(headers_audit) + 1):
        cell = ws_audit.cell(row=audit_header_row, column=col_idx)
        cell.font = header_font
        cell.fill = audit_header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for idx, s in enumerate(standards, start=1):
        row_num = audit_header_row + idx
        row_data = [
            idx,
            s.event_info.canonical_name,
            s.target_rank
        ]
        has_extrap = False
        for yr in all_years:
            yr_res = s.annual_results.get(yr)
            if yr_res:
                if yr_res.is_extrapolated:
                    has_extrap = True
                row_data.extend([
                    yr_res.target_time_str,
                    f"{yr_res.valid_count}/{yr_res.original_count}",
                    yr_res.audit_note
                ])
            else:
                row_data.extend(["-", "-", "N/A"])

        row_data.extend([
            s.combination_method.capitalize(),
            s.standard_time_str,
            f"{s.standard_seconds:.2f}",
            f"{s.std_dev_seconds:.2f}" if s.std_dev_seconds is not None else "-"
        ])
        ws_audit.append(row_data)

        fill_to_use = extrap_fill if has_extrap else (alt_row_fill if idx % 2 == 0 else white_fill)
        for c in range(1, len(headers_audit) + 1):
            cell = ws_audit.cell(row=row_num, column=c)
            cell.font = data_font
            cell.fill = fill_to_use
            cell.border = thin_border
            if c in [1, 3]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif c == 2:
                cell.alignment = Alignment(horizontal="left", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="center", vertical="center")

    # Auto-adjust column widths for both worksheets
    for sheet in [ws_standards, ws_audit]:
        for col in sheet.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                # ignore top title rows when calculating widths
                if cell.row < 4:
                    continue
                val_str = str(cell.value or "")
                max_len = max(max_len, len(val_str))
            sheet.column_dimensions[col_letter].width = max(max_len + 3, 11)

    wb.save(filepath)


def print_console_summary(standards: List[AggregatedStandard], quiet: bool = False) -> None:
    """
    Outputs a structured audit report to the terminal.
    """
    if quiet:
        return

    all_years = sorted(list({yr for s in standards for yr in s.annual_results.keys() if yr > 0}))
    if not all_years:
        all_years = [2024, 2025, 2026]

    header_cols = [f" {'#':>2}", f"{'Event':<30}", f"{'Target':<6}"]
    for yr in all_years:
        header_cols.append(f"{str(yr):<8}")
    header_cols.append(f"{'Standard':<8}")

    header_line = " | ".join(header_cols)
    width = max(len(header_line) + 2, 90)

    print("\n" + "=" * width)
    print("  REGIONAL INTERMEDIATE SWIMMING QUALIFYING STANDARDS")
    print("=" * width)
    print(header_line)
    print("-" * width)

    extrapolated_count = 0
    total_events = len(standards)

    for idx, s in enumerate(standards, start=1):
        row_cols = [f" {idx:>2}", f"{s.event_info.canonical_name:<30}", f"Rank {s.target_rank:<1}"]
        for yr in all_years:
            yr_res = s.annual_results.get(yr)
            val_str = (yr_res.target_time_str + ("*" if yr_res.is_extrapolated else "")) if yr_res else "-"
            row_cols.append(f"{val_str:>8}")
        row_cols.append(f"{s.standard_time_str:>8}")

        if any(r.is_extrapolated for r in s.annual_results.values() if r):
            extrapolated_count += 1

        print(" | ".join(row_cols))

    print("-" * width)
    print(f" Total Individual Events: {total_events}")
    print(f" Events with Extrapolated/Pruned Marks (*): {extrapolated_count}")
    print("=" * width + "\n")
