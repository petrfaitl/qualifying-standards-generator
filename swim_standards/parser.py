"""
Workbook reader, cell extraction, regex event matching, and time conversion utilities.
"""

import os
import re
from typing import List, Optional, Tuple, Dict, Any
import xlrd
from .models import SwimmerResult, EventInfo, EventResults


TIME_PATTERN = re.compile(r'^\*?(?:(\d{1,2}):)?(\d{1,2}(?:\.\d{1,2})?)\*?$')
EVENT_HEADER_PATTERN = re.compile(
    r'^Event\s+(\d+)\s+(Girls|Boys)(?:\s+([\d\s&OverUnd-]+?))?\s+(\d+)\s+SC\s+Meter\s+(.*?)\s+(Y[78](?:&[78])?)\s*(?:Girls|Boys)?$',
    re.IGNORECASE
)
RELAY_PATTERN = re.compile(r'relay', re.IGNORECASE)
NON_FINISHER_PATTERN = re.compile(r'^(DQ|DNF|SCR|NS|NT|DQ\b|DNF\b)', re.IGNORECASE)


def time_to_seconds(time_str: Any) -> Optional[float]:
    """
    Converts swim clock string (e.g., '1:31.13', '36.84', '*36.84') to seconds as float.
    Returns None for invalid times or non-finishers (DQ, DNF, SCR, NS).
    """
    if time_str is None:
        return None
    s = str(time_str).strip()
    if not s:
        return None

    if NON_FINISHER_PATTERN.search(s):
        return None

    # Remove asterisk markings, quotes, or trailing indicators
    cleaned = s.replace('*', '').strip()
    match = TIME_PATTERN.match(cleaned)
    if not match:
        return None

    mins_part, secs_part = match.groups()
    try:
        seconds = float(secs_part)
        if mins_part:
            seconds += float(mins_part) * 60.0
        return round(seconds, 2)
    except (ValueError, TypeError):
        return None


def seconds_to_time(seconds: Optional[float], format_mm_ss: bool = False) -> str:
    """
    Converts float seconds back to standard swimming clock representation.
    If format_mm_ss is True, outputs MM:SS.ss even for times under 1 minute.
    Otherwise, uses M:SS.ss for >= 60s and SS.ss for < 60s.
    """
    if seconds is None:
        return ""
    if seconds < 0:
        return "0.00"

    mins = int(seconds // 60)
    secs = seconds % 60

    if format_mm_ss:
        return f"{mins:02d}:{secs:05.2f}"
    else:
        if mins > 0:
            return f"{mins}:{secs:05.2f}"
        else:
            return f"{secs:05.2f}"


def parse_event_header(raw_header: str) -> Optional[EventInfo]:
    """
    Parses an event header string into an EventInfo model.
    Example: 'Event 1  Girls 12 & Over 100 SC Meter Breaststroke Y8 Girls'
    """
    cleaned = re.sub(r'\s+', ' ', raw_header.strip())
    match = EVENT_HEADER_PATTERN.match(cleaned)
    if not match:
        return None

    ev_num_str, gender, age_group, dist_str, stroke, school_year = match.groups()
    stroke = stroke.strip()
    is_relay = bool(RELAY_PATTERN.search(stroke) or RELAY_PATTERN.search(cleaned))

    return EventInfo(
        event_number=int(ev_num_str),
        raw_title=cleaned,
        gender=gender.capitalize(),
        school_year=school_year.upper(),
        age_group=(age_group or "").strip(),
        distance=int(dist_str),
        stroke=stroke,
        is_relay=is_relay
    )


def extract_year_from_filename(filename: str) -> Optional[int]:
    """Extracts 4-digit year from filepath (e.g. results-2024.xls or wbop2024-top8.xls -> 2024)."""
    basename = os.path.basename(filename)
    match = re.search(r'20\d{2}', basename)
    if match:
        return int(match.group(0))
    match = re.search(r'19\d{2}', basename)
    if match:
        return int(match.group(0))
    return None


class WorkbookReader:
    """
    Robust reader for historical championship swimming meet workbooks.
    Normalizes compact (2024/2025) and shifted/sparse column layouts (2026).
    """

    def __init__(self, exclude_relays: bool = True):
        self.exclude_relays = exclude_relays

    def read_file(self, filepath: str, meet_year: Optional[int] = None) -> List[EventResults]:
        """
        Reads an XLS or XLSX file and returns a list of EventResults.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Meet file not found: {filepath}")

        if meet_year is None:
            meet_year = extract_year_from_filename(filepath) or 0

        # Read raw rows supporting both modern .xlsx (openpyxl) and legacy .xls (xlrd)
        if filepath.lower().endswith(".xlsx"):
            import openpyxl
            wb = openpyxl.load_workbook(filepath, data_only=True)
            sheet = wb.worksheets[0]
            raw_rows = [
                [cell.value if cell.value is not None else "" for cell in row]
                for row in sheet.iter_rows()
            ]
            wb.close()
        else:
            wb = xlrd.open_workbook(filepath)
            sheet = wb.sheet_by_index(0)
            raw_rows = [
                [sheet.cell_value(r, c) for c in range(sheet.ncols)]
                for r in range(sheet.nrows)
            ]

        events: List[EventResults] = []
        current_event_info: Optional[EventInfo] = None
        current_swimmers: List[SwimmerResult] = []

        for row_cells in raw_rows:
            non_empty = [str(val).strip() for val in row_cells if str(val).strip() != '']

            if not non_empty:
                continue

            first_cell = non_empty[0]

            # Detect Event header
            if first_cell.startswith("Event "):
                if current_event_info is not None:
                    if not (self.exclude_relays and current_event_info.is_relay):
                        events.append(EventResults(
                            event_info=current_event_info,
                            meet_year=meet_year,
                            swimmers=current_swimmers
                        ))
                current_event_info = parse_event_header(first_cell)
                current_swimmers = []
                continue

            if current_event_info is None:
                continue

            # Detect Swimmer result row
            # Rank can be '1', '2', or tie indicator '*1', '*8'
            rank_match = re.match(r'^\*?(\d+)$', first_cell)
            if rank_match:
                rank = int(rank_match.group(1))
                is_tied = first_cell.startswith('*')

                # Time is consistently the last non-empty token in valid swimmer rows
                time_token = non_empty[-1]
                time_sec = time_to_seconds(time_token)

                # Skip non-finishers or unparseable time entries
                if time_sec is None:
                    continue

                name = ""
                school = ""
                yr_group = ""

                # Cell token layout varies:
                # 5 tokens: [Rank, Name, Yr, School, Time]
                # 4 tokens: [Rank, Name, School, Time] (missing Yr)
                # 3 tokens: [Rank, Name, Time]
                if len(non_empty) >= 5:
                    name = non_empty[1]
                    yr_group = non_empty[2]
                    school = non_empty[3]
                elif len(non_empty) == 4:
                    name = non_empty[1]
                    school = non_empty[2]
                elif len(non_empty) == 3:
                    name = non_empty[1]

                swimmer = SwimmerResult(
                    rank=rank,
                    name=name,
                    year_group=yr_group,
                    school=school,
                    time_str=time_token.replace('*', '').strip(),
                    time_seconds=time_sec,
                    is_tied=is_tied
                )
                current_swimmers.append(swimmer)

        # Append last event in the sheet
        if current_event_info is not None:
            if not (self.exclude_relays and current_event_info.is_relay):
                events.append(EventResults(
                    event_info=current_event_info,
                    meet_year=meet_year,
                    swimmers=current_swimmers
                ))

        return events
