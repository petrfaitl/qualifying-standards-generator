"""
Unit and regression tests for workbook parsing, time conversions, and event normalization.
"""

import unittest
import os
from swim_standards.parser import (
    time_to_seconds,
    seconds_to_time,
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

    def test_parse_event_header(self):
        # Individual event
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

        # Relay event
        h17 = "Event 17  Girls 10-13 100 SC Meter Freestyle Relay Y7&8 Girls"
        ev17 = parse_event_header(h17)
        self.assertIsNotNone(ev17)
        self.assertEqual(ev17.event_number, 17)
        self.assertTrue(ev17.is_relay)

        # 25m Butterfly
        h32 = "Event 32  Boys 12 & Over 25 SC Meter Butterfly Y8 Boys"
        ev32 = parse_event_header(h32)
        self.assertIsNotNone(ev32)
        self.assertEqual(ev32.distance, 25)
        self.assertEqual(ev32.stroke, "Butterfly")
        self.assertEqual(ev32.school_year, "Y8")

    def test_read_real_workbooks(self):
        reader = WorkbookReader(exclude_relays=True)

        file_2024 = "results-2024.xls" if os.path.exists("results-2024.xls") else "wbop2024-top8.xls"
        file_2025 = "results-2025.xls" if os.path.exists("results-2025.xls") else "wbop2025-top8.xls"
        file_2026 = "results-2026.xls" if os.path.exists("results-2026.xls") else "wbop2026-top8.xls"

        # Test 2024
        events_2024 = reader.read_file(file_2024)
        self.assertEqual(len(events_2024), 36)
        ev1_2024 = events_2024[0]
        self.assertEqual(ev1_2024.event_info.canonical_name, "Y8 Girls 100m Breaststroke")
        self.assertEqual(len(ev1_2024.swimmers), 8)
        self.assertEqual(ev1_2024.swimmers[0].name, "Lichtwark, Addy")
        self.assertEqual(ev1_2024.swimmers[0].time_seconds, 91.13)

        # Test 2025
        events_2025 = reader.read_file(file_2025)
        self.assertEqual(len(events_2025), 36)
        # Event 2 has tie in 1st place
        ev2_2025 = events_2025[1]
        self.assertTrue(ev2_2025.swimmers[0].is_tied)
        self.assertTrue(ev2_2025.swimmers[1].is_tied)
        self.assertEqual(ev2_2025.swimmers[0].time_seconds, 93.86)
        self.assertEqual(ev2_2025.swimmers[1].time_seconds, 93.86)

        # Test 2026 (75-column shifted layout and relay exclusion)
        events_2026 = reader.read_file(file_2026)
        self.assertEqual(len(events_2026), 36)
        # Check that no relays exist in filtered list
        self.assertFalse(any(ev.event_info.is_relay for ev in events_2026))

        # Check with exclude_relays=False
        reader_all = WorkbookReader(exclude_relays=False)
        all_2026 = reader_all.read_file(file_2026)
        self.assertEqual(len(all_2026), 38)
        self.assertTrue(any(ev.event_info.event_number == 17 for ev in all_2026))
        self.assertTrue(any(ev.event_info.event_number == 18 for ev in all_2026))


if __name__ == '__main__':
    unittest.main()
