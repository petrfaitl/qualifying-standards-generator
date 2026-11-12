"""
Unit and regression tests for workbook parsing, time conversions, and event normalization.
"""

import unittest
import os
import openpyxl
from swim_standards.models import EventInfo, SwimmerResult
from swim_standards.parser import (
    time_to_seconds,
    seconds_to_time,
    normalize_year_group,
    normalize_division,
    normalize_year_and_gender,
    normalize_division_or_year,
    parse_event_header,
    WorkbookReader
)


class TestParser(unittest.TestCase):

    def test_time_conversions(self):
        # Normal times
        self.assertEqual(time_to_seconds("1:31.13"), 91.13)
        self.assertEqual(time_to_seconds("36.84"), 36.84)
        self.assertEqual(time_to_seconds("18.05"), 18.05)
        self.assertEqual(time_to_seconds("2:05.40"), 125.40)

        # Asterisk ties and trailing marks
        self.assertEqual(time_to_seconds("*1:33.86"), 93.86)
        self.assertEqual(time_to_seconds("*36.84*"), 36.84)
        self.assertEqual(time_to_seconds(" 36.84 "), 36.84)

        # Non-finishers & invalid formats
        self.assertIsNone(time_to_seconds("DQ"))
        self.assertIsNone(time_to_seconds("DNF"))
        self.assertIsNone(time_to_seconds("SCR"))
        self.assertIsNone(time_to_seconds("NS"))
        self.assertIsNone(time_to_seconds(""))
        self.assertIsNone(time_to_seconds(None))
        self.assertIsNone(time_to_seconds("invalid_time"))

    def test_seconds_to_time(self):
        self.assertEqual(seconds_to_time(91.13), "1:31.13")
        self.assertEqual(seconds_to_time(36.84), "36.84")
        self.assertEqual(seconds_to_time(125.04), "2:05.04")
        self.assertEqual(seconds_to_time(36.84, format_mm_ss=True), "00:36.84")
        self.assertEqual(seconds_to_time(91.13, format_mm_ss=True), "01:31.13")

    def test_normalize_year_group(self):
        self.assertEqual(normalize_year_group("5"), "Y5")
        self.assertEqual(normalize_year_group("6"), "Y6")
        self.assertEqual(normalize_year_group("Y5"), "Y5")
        self.assertEqual(normalize_year_group("Year 6"), "Y6")
        self.assertEqual(normalize_year_group("07"), "Y7")
        self.assertEqual(normalize_year_group("Y13"), "Y13")
        self.assertEqual(normalize_year_group("5&6"), "Y5&6")
        self.assertEqual(normalize_year_group("Y5&6"), "Y5&6")
        self.assertEqual(normalize_year_group("Y5&Y6"), "Y5&6")
        self.assertEqual(normalize_year_group("7 & 8"), "Y7&8")
        self.assertEqual(normalize_year_group("Y7&8"), "Y7&8")
        self.assertIsNone(normalize_year_group("0"))
        self.assertIsNone(normalize_year_group("14"))
        self.assertIsNone(normalize_year_group("St Peters"))
        self.assertIsNone(normalize_year_group(""))

    def test_normalize_division(self):
        self.assertEqual(normalize_division("jr"), "Junior")
        self.assertEqual(normalize_division("jnr"), "Junior")
        self.assertEqual(normalize_division("junior"), "Junior")
        self.assertEqual(normalize_division("in"), "Intermediate")
        self.assertEqual(normalize_division("int"), "Intermediate")
        self.assertEqual(normalize_division("inter"), "Intermediate")
        self.assertEqual(normalize_division("intermediate"), "Intermediate")
        self.assertEqual(normalize_division("sr"), "Senior")
        self.assertEqual(normalize_division("snr"), "Senior")
        self.assertEqual(normalize_division("senior"), "Senior")
        self.assertEqual(normalize_division("open"), "Open")
        self.assertIsNone(normalize_division("primary"))
        self.assertIsNone(normalize_division(""))

    def test_normalize_year_and_gender(self):
        # Combined year + gender
        self.assertEqual(normalize_year_and_gender("Y5G"), ("Y5", "Girls"))
        self.assertEqual(normalize_year_and_gender("Y6B"), ("Y6", "Boys"))
        self.assertEqual(normalize_year_and_gender("5G"), ("Y5", "Girls"))
        self.assertEqual(normalize_year_and_gender("6B"), ("Y6", "Boys"))
        self.assertEqual(normalize_year_and_gender("7G"), ("Y7", "Girls"))
        self.assertEqual(normalize_year_and_gender("8B"), ("Y8", "Boys"))

        # Combined division + gender
        self.assertEqual(normalize_year_and_gender("JrG"), ("Junior", "Girls"))
        self.assertEqual(normalize_year_and_gender("JrB"), ("Junior", "Boys"))
        self.assertEqual(normalize_year_and_gender("InG"), ("Intermediate", "Girls"))
        self.assertEqual(normalize_year_and_gender("InB"), ("Intermediate", "Boys"))
        self.assertEqual(normalize_year_and_gender("SrG"), ("Senior", "Girls"))
        self.assertEqual(normalize_year_and_gender("SrB"), ("Senior", "Boys"))
        self.assertEqual(normalize_year_and_gender("Junior Girls"), ("Junior", "Girls"))
        self.assertEqual(normalize_year_and_gender("Y6 Boys"), ("Y6", "Boys"))

        # Standalone
        self.assertEqual(normalize_year_and_gender("5"), ("Y5", None))
        self.assertEqual(normalize_year_and_gender("Y6"), ("Y6", None))
        self.assertEqual(normalize_year_and_gender("jr"), ("Junior", None))
        self.assertEqual(normalize_year_and_gender("in"), ("Intermediate", None))
        self.assertEqual(normalize_year_and_gender("sr"), ("Senior", None))
        self.assertEqual(normalize_year_and_gender("Girls"), (None, "Girls"))
        self.assertEqual(normalize_year_and_gender("Boys"), (None, "Boys"))
        self.assertEqual(normalize_year_and_gender("St Peters"), (None, None))

        # normalize_division_or_year wrapper
        self.assertEqual(normalize_division_or_year("Y5G"), ("Y5", "Girls"))
        self.assertEqual(normalize_division_or_year("In"), ("Intermediate", None))
        self.assertIsNone(normalize_division_or_year("Girls"))

    def test_parse_event_header(self):
        # Traditional format
        h1 = "Event 1  Girls 12 & Over 100 SC Meter Breaststroke Y8 Girls"
        ev1 = parse_event_header(h1)
        self.assertIsNotNone(ev1)
        self.assertEqual(ev1.event_number, 1)
        self.assertEqual(ev1.gender, "Girls")
        self.assertEqual(ev1.school_year, "Y8")
        self.assertEqual(ev1.distance, 100)
        self.assertEqual(ev1.stroke, "Breaststroke")
        self.assertFalse(ev1.is_relay)
        self.assertEqual(ev1.canonical_name, "Y8 Girls 100m Breaststroke")

        # Y5G combined token
        h5 = "Event 5 Y5G 50 SC Meter Freestyle"
        ev5 = parse_event_header(h5)
        self.assertIsNotNone(ev5)
        self.assertEqual(ev5.event_number, 5)
        self.assertEqual(ev5.gender, "Girls")
        self.assertEqual(ev5.school_year, "Y5")
        self.assertEqual(ev5.distance, 50)
        self.assertEqual(ev5.stroke, "Freestyle")
        self.assertEqual(ev5.canonical_name, "Y5 Girls 50m Freestyle")

        # Junior Boys
        h12 = "Event 12 Junior Boys 50 SC Meter Backstroke"
        ev12 = parse_event_header(h12)
        self.assertIsNotNone(ev12)
        self.assertEqual(ev12.gender, "Boys")
        self.assertEqual(ev12.school_year, "Junior")
        self.assertEqual(ev12.distance, 50)
        self.assertEqual(ev12.stroke, "Backstroke")
        self.assertEqual(ev12.canonical_name, "Junior Boys 50m Backstroke")

        # Y6B suffix
        h3 = "Event 3 50 SC Meter Butterfly Y6B"
        ev3 = parse_event_header(h3)
        self.assertIsNotNone(ev3)
        self.assertEqual(ev3.gender, "Boys")
        self.assertEqual(ev3.school_year, "Y6")
        self.assertEqual(ev3.stroke, "Butterfly")

        # IM Intermediate
        h9 = "Event 9 Girls 100 SC Meter IM Intermediate"
        ev9 = parse_event_header(h9)
        self.assertIsNotNone(ev9)
        self.assertEqual(ev9.gender, "Girls")
        self.assertEqual(ev9.school_year, "Intermediate")
        self.assertEqual(ev9.stroke, "IM")

        # Senior Boys
        h22 = "Event 22 Boys 13 & Over 50 SC Meter Freestyle Senior Boys"
        ev22 = parse_event_header(h22)
        self.assertIsNotNone(ev22)
        self.assertEqual(ev22.gender, "Boys")
        self.assertEqual(ev22.school_year, "Senior")

        # Relay event
        h17 = "Event 17  Girls 10-13 100 SC Meter Freestyle Relay Y7&8 Girls"
        ev17 = parse_event_header(h17)
        self.assertIsNotNone(ev17)
        self.assertEqual(ev17.event_number, 17)
        self.assertTrue(ev17.is_relay)

    def test_event_order_key(self):
        ev_y5 = EventInfo(1, "E1", "Girls", "Y5", "", 50, "Freestyle")
        ev_y6 = EventInfo(2, "E2", "Girls", "Y6", "", 50, "Freestyle")
        ev_y56 = EventInfo(3, "E3", "Girls", "Y5&6", "", 50, "Freestyle")
        ev_y7 = EventInfo(4, "E4", "Girls", "Y7", "", 50, "Freestyle")
        ev_jr = EventInfo(5, "E5", "Girls", "Junior", "", 50, "Freestyle")
        ev_in = EventInfo(6, "E6", "Girls", "Intermediate", "", 50, "Freestyle")
        ev_sr = EventInfo(7, "E7", "Girls", "Senior", "", 50, "Freestyle")
        ev_op = EventInfo(8, "E8", "Girls", "Open", "", 50, "Freestyle")

        sorted_events = sorted([ev_op, ev_sr, ev_y7, ev_y5, ev_in, ev_jr, ev_y6, ev_y56], key=lambda e: e.event_order_key)
        self.assertEqual(sorted_events, [ev_y5, ev_y56, ev_y6, ev_y7, ev_jr, ev_in, ev_sr, ev_op])

    def test_swimmer_row_disambiguation(self):
        temp_file = "temp_disambiguation_test.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Results"

        rows = [
            ["Event 1 Y5G 50 SC Meter Freestyle"],
            # 5-token row: [Rank, Name, Yr, School, Time]
            ["1", "Alice Smith", "5", "Hillcrest", "35.20"],
            # 4-token row with year: [Rank, Name, Yr, Time]
            ["2", "Beth Jones", "Y5", "36.10"],
            # 4-token row with school: [Rank, Name, School, Time]
            ["3", "Chloe Adams", "St Peters", "37.05"],
            # 4-token row with division: [Rank, Name, Division, Time]
            ["4", "Diana Prince", "jr", "38.50"],
            # 3-token row: [Rank, Name, Time]
            ["5", "Eve Taylor", "39.12"],
        ]
        for row in rows:
            ws.append(row)
        wb.save(temp_file)

        try:
            reader = WorkbookReader()
            events = reader.read_file(temp_file, meet_year=2025)
            self.assertEqual(len(events), 1)
            swimmers = events[0].swimmers
            self.assertEqual(len(swimmers), 5)

            # Row 1 (5 tokens)
            self.assertEqual(swimmers[0].name, "Alice Smith")
            self.assertEqual(swimmers[0].year_group, "Y5")
            self.assertEqual(swimmers[0].school, "Hillcrest")

            # Row 2 (4 tokens with year)
            self.assertEqual(swimmers[1].name, "Beth Jones")
            self.assertEqual(swimmers[1].year_group, "Y5")
            self.assertEqual(swimmers[1].school, "")

            # Row 3 (4 tokens with school)
            self.assertEqual(swimmers[2].name, "Chloe Adams")
            self.assertEqual(swimmers[2].year_group, "")
            self.assertEqual(swimmers[2].school, "St Peters")

            # Row 4 (4 tokens with division)
            self.assertEqual(swimmers[3].name, "Diana Prince")
            self.assertEqual(swimmers[3].year_group, "Junior")
            self.assertEqual(swimmers[3].school, "")

            # Row 5 (3 tokens)
            self.assertEqual(swimmers[4].name, "Eve Taylor")
            self.assertEqual(swimmers[4].year_group, "")
            self.assertEqual(swimmers[4].school, "")
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test_extract_year_from_filename(self):
        from swim_standards.parser import extract_year_from_filename, extract_year_from_rows
        self.assertEqual(extract_year_from_filename("results-2024.xls"), 2024)
        self.assertEqual(extract_year_from_filename("wbop2028-top8.xls"), 2028)
        self.assertEqual(extract_year_from_filename("/meets/2021/results.xlsx"), 2021)
        self.assertEqual(extract_year_from_filename("meet_1998_finals.xls"), 1998)
        self.assertEqual(extract_year_from_filename("results_24.xls"), 2024)
        self.assertEqual(extract_year_from_filename("meet99.xls"), 1999)
        self.assertIsNone(extract_year_from_filename("finals.xls"))

        # Test sheet header extraction
        sample_rows = [
            ["Waikato Bay of Plenty Championship 2030"],
            ["Event 1 Girls 50 Free Y5"]
        ]
        self.assertEqual(extract_year_from_rows(sample_rows), 2030)

    def test_read_real_workbooks(self):
        file_2024 = "results-2024.xls" if os.path.exists("results-2024.xls") else "wbop2024-top8.xls"
        if not os.path.exists(file_2024):
            self.skipTest("Historical sample meet files not present on disk.")

        reader = WorkbookReader(exclude_relays=True)
        events_2024 = reader.read_file(file_2024)
        self.assertEqual(len(events_2024), 36)


if __name__ == '__main__':
    unittest.main()
