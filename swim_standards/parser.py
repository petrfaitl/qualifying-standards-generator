"""
Workbook reader, cell extraction, regex event matching, and time conversion utilities.
"""

import os
import re
from typing import List, Optional, Tuple, Dict, Any
import xlrd
from .models import SwimmerResult, EventInfo, EventResults


TIME_PATTERN = re.compile(r'^\*?(?:(\d{1,2}):)?(\d{1,2}(?:\.\d{1,2})?)\*?$')
RELAY_PATTERN = re.compile(r'\brelays?\b|4x\d+', re.IGNORECASE)
NON_FINISHER_PATTERN = re.compile(r'^(DQ|DNF|SCR|NS|NT|DQ\b|DNF\b)', re.IGNORECASE)


def normalize_year_group(token: str) -> Optional[str]:
    """
    Normalizes school year representations (e.g., '5', 'Y5', 'Year 6', '5&6', 'Y7&8') to canonical 'Y<N>' format.
    Returns None if token is not a recognized school year.
    """
    if not token or not str(token).strip():
        return None
    t = str(token).strip()

    # Check combined year like 5&6, Y5&6, Y5&Y6, 5 & 6, 7-8, 7/8
    m_comb = re.match(r'^(?:Y|Year)?\s*(\d{1,2})\s*(?:&|/|-|and)\s*(?:Y|Year)?\s*(\d{1,2})$', t, re.IGNORECASE)
    if m_comb:
        y1, y2 = int(m_comb.group(1)), int(m_comb.group(2))
        if 1 <= y1 <= 13 and 1 <= y2 <= 13:
            return f"Y{y1}&{y2}"

    # Check single year like Y5, Year 5, Y05, 5, 05, etc.
    m_single = re.match(r'^(?:Y|Year)?\s*0*(\d{1,2})$', t, re.IGNORECASE)
    if m_single:
        y = int(m_single.group(1))
        if 1 <= y <= 13:
            return f"Y{y}"

    return None


def normalize_division(token: str) -> Optional[str]:
    """
    Normalizes division representations (e.g., 'jr', 'jnr', 'intermediate', 'in', 'sr', 'snr') to canonical TitleCase.
    Returns None if token is not a recognized division.
    """
    if not token or not str(token).strip():
        return None
    t = re.sub(r'[^\w]', '', str(token).strip().lower())
    if t in ("jr", "jnr", "junior"):
        return "Junior"
    if t in ("in", "int", "inter", "intermediate"):
        return "Intermediate"
    if t in ("sr", "snr", "senior"):
        return "Senior"
    if t in ("open", "opn"):
        return "Open"
    return None


def normalize_year_and_gender(token: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Disambiguates school year / division and gender from single or combined tokens.
    Examples:
        'Y5G' -> ('Y5', 'Girls')
        '6B' -> ('Y6', 'Boys')
        'JrG' -> ('Junior', 'Girls')
        'InB' -> ('Intermediate', 'Boys')
        'SrG' -> ('Senior', 'Girls')
        '5' -> ('Y5', None)
        'jr' -> ('Junior', None)
        'Girls' -> (None, 'Girls')
    """
    if not token or not str(token).strip():
        return None, None
    s = str(token).strip()

    # Split multi-token strings if spaces or delimiters exist
    parts = re.split(r'[\s\-_/]+', s)
    if len(parts) > 1:
        found_year = None
        found_gender = None
        for p in parts:
            sy, g = normalize_year_and_gender(p)
            if sy and not found_year:
                found_year = sy
            if g and not found_gender:
                found_gender = g
        if found_year or found_gender:
            return found_year, found_gender

    # 1. Combined division + gender (e.g. JrG, JnrB, IntermediateG, InB, SrG, SnrB, SeniorG, OpenB)
    m_div_g = re.match(r'^(Junior|Jr|Jnr|Intermediate|Inter|Int|In|Senior|Snr|Sr|Open)\.?([GB]|Girls?|Boys?)$', s, re.IGNORECASE)
    if m_div_g:
        div = normalize_division(m_div_g.group(1))
        g_raw = m_div_g.group(2).upper()
        g = "Girls" if g_raw.startswith("G") else "Boys"
        return div, g

    # 2. Combined year + gender (e.g. Y5G, 6B, 5G, Y6B, Y12G, 13B)
    m_yr_g = re.match(r'^(?:Y|Year)?\s*0*(\d{1,2})\s*([GB]|Girls?|Boys?)$', s, re.IGNORECASE)
    if m_yr_g:
        y_num = int(m_yr_g.group(1))
        if 1 <= y_num <= 13:
            g_raw = m_yr_g.group(2).upper()
            g = "Girls" if g_raw.startswith("G") else "Boys"
            return f"Y{y_num}", g

    # 3. Standalone division
    div = normalize_division(s)
    if div:
        return div, None

    # 4. Standalone year group
    yg = normalize_year_group(s)
    if yg:
        return yg, None

    # 5. Standalone gender
    s_clean = re.sub(r'[^\w]', '', s.lower())
    if s_clean in ("girls", "girl", "female", "females", "g", "f", "women", "woman"):
        return None, "Girls"
    if s_clean in ("boys", "boy", "male", "males", "b", "m", "men", "man"):
        return None, "Boys"
    if s_clean in ("mixed", "mix", "x"):
        return None, "Mixed"

    return None, None


def normalize_division_or_year(token: str) -> Optional[Tuple[str, Optional[str]]]:
    """
    Extracts (school_year, gender) from tokens like Y5, 5, Y5G, 6B, Jr, Junior, JrG, In, Intermediate, InB, Sr, Senior, SrG.
    Returns (school_year, gender) if school_year is detected, else None.
    """
    sy, g = normalize_year_and_gender(token)
    if sy is not None:
        return sy, g
    return None


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
    Parses an event header string into an EventInfo model across diverse syntax and token orderings.
    Examples:
        'Event 1  Girls 12 & Over 100 SC Meter Breaststroke Y8 Girls'
        'Event 5 Y5G 50 SC Meter Freestyle'
        'Event 12 Junior Boys 50 SC Meter Backstroke'
        'Event 3 50 SC Meter Butterfly Y6B'
    """
    cleaned = re.sub(r'\s+', ' ', raw_header.strip())
    # Must start with Event <num> or #<num> or Ev <num>
    m_ev = re.match(r'^(?:Event|Ev\.?|#)\s*(\d+)\b(.*)$', cleaned, re.IGNORECASE)
    if not m_ev:
        return None

    event_number = int(m_ev.group(1))
    remainder = m_ev.group(2).strip()

    is_relay = bool(RELAY_PATTERN.search(cleaned))

    # Extract Age group if present, e.g. '12 & Over', '11 & Under', '10-13', '12 & U', '13 & O', '13 & over', '10 - 13'
    age_group = ""
    m_age = re.search(r'\b(\d{1,2}\s*(?:&|-|to)\s*(?:Over|Under|U|O|\d{1,2}))\b', remainder, re.IGNORECASE)
    if m_age:
        age_group = m_age.group(1).strip()
        # Remove age group from remainder to avoid interference with distance/year
        remainder = remainder[:m_age.start()] + " " + remainder[m_age.end():]

    # Extract Distance
    # Standard swim distances: 25, 50, 100, 200, 400, 800, 1500
    # Match '100 SC Meter', '50 SC Metres', '50m', '100 m', '25 Metre', etc.
    distance = None
    m_dist = re.search(r'\b(\d{2,4})\s*(?:SC\s+Meters?|SC\s+Metres?|Meters?|Metres?|m)\b', remainder, re.IGNORECASE)
    if m_dist:
        distance = int(m_dist.group(1))
        remainder = remainder[:m_dist.start()] + " " + remainder[m_dist.end():]
    else:
        # Match standalone standard distance
        m_dist_standalone = re.search(r'\b(25|50|100|200|400|800|1500)\b', remainder)
        if m_dist_standalone:
            distance = int(m_dist_standalone.group(1))
            remainder = remainder[:m_dist_standalone.start()] + " " + remainder[m_dist_standalone.end():]

    if distance is None:
        return None

    # Extract Stroke
    stroke = None
    if re.search(r'\b(?:Individual\s+Medley|Ind\s+Medley|IM|Medley)\b', remainder, re.IGNORECASE):
        stroke = "IM"
        remainder = re.sub(r'\b(?:Individual\s+Medley|Ind\s+Medley|IM|Medley)\b', ' ', remainder, flags=re.IGNORECASE)
    elif re.search(r'\b(?:Breaststroke|Breast|Brst)\b', remainder, re.IGNORECASE):
        stroke = "Breaststroke"
        remainder = re.sub(r'\b(?:Breaststroke|Breast|Brst)\b', ' ', remainder, flags=re.IGNORECASE)
    elif re.search(r'\b(?:Backstroke|Back|Bk)\b', remainder, re.IGNORECASE):
        stroke = "Backstroke"
        remainder = re.sub(r'\b(?:Backstroke|Back|Bk)\b', ' ', remainder, flags=re.IGNORECASE)
    elif re.search(r'\b(?:Butterfly|Fly|Fl)\b', remainder, re.IGNORECASE):
        stroke = "Butterfly"
        remainder = re.sub(r'\b(?:Butterfly|Fly|Fl)\b', ' ', remainder, flags=re.IGNORECASE)
    elif re.search(r'\b(?:Freestyle|Free|Fr)\b', remainder, re.IGNORECASE):
        stroke = "Freestyle"
        remainder = re.sub(r'\b(?:Freestyle|Free|Fr)\b', ' ', remainder, flags=re.IGNORECASE)

    if stroke is None:
        return None

    # Clean remainder of leftover unit/relay words
    remainder = re.sub(r'\b(?:SC|Meter|Meters|Metre|Metres|m|Relay|Relays)\b', ' ', remainder, flags=re.IGNORECASE)

    # Disambiguate year/division and gender from remainder
    school_year = None
    gender = None

    tokens = [t.strip() for t in remainder.split() if t.strip()]
    for tok in tokens:
        sy, g = normalize_year_and_gender(tok)
        if sy and school_year is None:
            school_year = sy
        if g and gender is None:
            gender = g

    # Second check for combined years like Y5&6 or 5&6 if split into tokens
    if school_year is None:
        comb_match = re.search(r'\b(?:Y|Year)?\s*(\d{1,2})\s*&\s*(?:Y|Year)?\s*(\d{1,2})\b', remainder, re.IGNORECASE)
        if comb_match:
            school_year = f"Y{comb_match.group(1)}&{comb_match.group(2)}"

    # If gender not found, check full title for Girls/Boys/Mixed
    if gender is None:
        if re.search(r'\b(?:Girls?|Female|Women)\b', cleaned, re.IGNORECASE):
            gender = "Girls"
        elif re.search(r'\b(?:Boys?|Male|Men)\b', cleaned, re.IGNORECASE):
            gender = "Boys"
        elif re.search(r'\b(?:Mixed|Mix)\b', cleaned, re.IGNORECASE):
            gender = "Mixed"
        else:
            gender = "Unknown"

    if school_year is None:
        school_year = "Open"

    return EventInfo(
        event_number=event_number,
        raw_title=cleaned,
        gender=gender,
        school_year=school_year,
        age_group=age_group,
        distance=distance,
        stroke=stroke,
        is_relay=is_relay
    )


def extract_year_from_filename(filename: str) -> Optional[int]:
    """
    Extracts 4-digit or contextual 2-digit calendar year from path string.
    Examples:
        'results-2024.xls' -> 2024
        'wbop2028-top8.xls' -> 2028
        '/meets/2021/results.xls' -> 2021
        'meet_23_results.xls' -> 2023
    """
    if not filename:
        return None

    # 1. Search for 4-digit year in basename
    basename = os.path.basename(filename)
    m4 = re.search(r'\b(19\d{2}|20\d{2})\b', basename)
    if m4:
        return int(m4.group(1))

    # Search for embedded 4-digit year without word boundaries in basename (e.g. wbop2024)
    m4_embed = re.search(r'(19\d{2}|20\d{2})', basename)
    if m4_embed:
        return int(m4_embed.group(1))

    # 2. Search for 4-digit year in full filepath (e.g. parent directories)
    m4_path = re.search(r'\b(19\d{2}|20\d{2})\b', filename)
    if m4_path:
        return int(m4_path.group(1))

    # 3. Search for contextual 2-digit year in basename (e.g., results-24.xls, meet23.xls)
    m2 = re.search(r'(?:results|meet|wbop|top8|swim|champs?|yr|year)[-_]?(\d{2})\b', basename, re.IGNORECASE)
    if not m2:
        m2 = re.search(r'\b(\d{2})[-_]?(?:results|meet|wbop|top8|swim|champs?)\b', basename, re.IGNORECASE)
    if m2:
        yy = int(m2.group(1))
        return 2000 + yy if yy < 50 else 1900 + yy

    return None


def extract_year_from_rows(raw_rows: List[List[Any]], max_rows: int = 15) -> Optional[int]:
    """
    Scans the first few rows of a workbook sheet for a 4-digit calendar year (1900-2099).
    """
    for row in raw_rows[:max_rows]:
        row_str = " ".join(str(cell) for cell in row if cell is not None)
        matches = re.findall(r'\b(19\d{2}|20\d{2})\b', row_str)
        if matches:
            return int(matches[0])
    return None


class WorkbookReader:
    """
    Robust reader for historical championship swimming meet workbooks.
    Normalizes compact (2024/2025) and shifted/sparse column layouts (2026).
    """

    def __init__(self, exclude_relays: bool = True, verbose: bool = False):
        self.exclude_relays = exclude_relays
        self.verbose = verbose
        self.warnings: List[str] = []

    def read_file(self, filepath: str, meet_year: Optional[int] = None) -> List[EventResults]:
        """
        Reads an XLS or XLSX file and returns a list of EventResults.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Meet file not found: {filepath}")

        # Read raw rows supporting both modern .xlsx (openpyxl) and legacy .xls (xlrd)
        try:
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
        except Exception as e:
            err_msg = f"Failed to parse spreadsheet file '{filepath}': {e}"
            self.warnings.append(err_msg)
            raise ValueError(err_msg) from e

        if meet_year is None or meet_year == 0:
            meet_year = extract_year_from_filename(filepath)
            if meet_year is None:
                meet_year = extract_year_from_rows(raw_rows)
            meet_year = meet_year or 0

        events: List[EventResults] = []
        current_event_info: Optional[EventInfo] = None
        current_swimmers: List[SwimmerResult] = []

        file_basename = os.path.basename(filepath)

        for row_idx, row_cells in enumerate(raw_rows):
            non_empty = [str(val).strip() for val in row_cells if str(val).strip() != '']

            if not non_empty:
                continue

            first_cell = non_empty[0]

            # Detect Event header
            if first_cell.startswith("Event ") or re.match(r'^(?:Event|Ev\.?|#)\s*\d+\b', first_cell, re.IGNORECASE):
                if current_event_info is not None:
                    if not (self.exclude_relays and current_event_info.is_relay):
                        events.append(EventResults(
                            event_info=current_event_info,
                            meet_year=meet_year,
                            swimmers=current_swimmers
                        ))
                parsed_ev = parse_event_header(first_cell)
                if parsed_ev is None:
                    self.warnings.append(f"[{file_basename}:row {row_idx + 1}] Unable to parse event header: '{first_cell}'")
                current_event_info = parsed_ev
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
                    if NON_FINISHER_PATTERN.search(time_token):
                        if self.verbose:
                            self.warnings.append(f"[{file_basename}:row {row_idx + 1}] Non-finisher '{time_token}' excluded for rank {first_cell}")
                    else:
                        self.warnings.append(f"[{file_basename}:row {row_idx + 1}] Invalid time format '{time_token}' for rank {first_cell}")
                    continue

                name = ""
                school = ""
                yr_group = ""

                # Cell token layout varies:
                # 5+ tokens: [Rank, Name, Yr, School, Time]
                # 4 tokens: [Rank, Name, Token2, Time] (Token2 can be Year or School)
                # 3 tokens: [Rank, Name, Time]
                if len(non_empty) >= 5:
                    name = non_empty[1]
                    raw_yr = non_empty[2]
                    norm_yr, _ = normalize_year_and_gender(raw_yr)
                    yr_group = norm_yr if norm_yr else raw_yr
                    school = non_empty[3]
                elif len(non_empty) == 4:
                    name = non_empty[1]
                    token2 = non_empty[2]
                    norm_yr, _ = normalize_year_and_gender(token2)
                    if norm_yr:
                        yr_group = norm_yr
                        school = ""
                    else:
                        school = token2
                        yr_group = ""
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

        if len(events) == 0:
            self.warnings.append(f"[{file_basename}] No valid individual swimming events parsed from workbook.")

        return events
