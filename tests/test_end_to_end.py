"""
End-to-end integration tests over multi-year datasets and arbitrary calendar years.
"""

import os
import shutil
import unittest
import openpyxl
import csv
from generate_qualifying_standards import main as cli_main
from swim_standards.exporter import print_console_summary
from swim_standards.aggregator import MultiYearAggregator
from swim_standards.parser import WorkbookReader


class TestEndToEnd(unittest.TestCase):

    def setUp(self):
        self.test_dir = "temp_test_meet_files"
        os.makedirs(self.test_dir, exist_ok=True)
        self.excel_out = "temp_test_standards.xlsx"
        self.csv_out = "temp_test_standards.csv"

        # Generate synthetic multi-year workbooks (2021, 2022, 2023, 2028)
        self.meet_years = [2021, 2022, 2023, 2028]
        self.meet_files = []
        for yr in self.meet_years:
            fname = os.path.join(self.test_dir, f"meet_results_{yr}.xlsx")
            self._create_synthetic_workbook(fname, yr)
            self.meet_files.append(fname)

    def tearDown(self):
        for path in [self.excel_out, self.csv_out]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
        if os.path.exists(self.test_dir):
            try:
                shutil.rmtree(self.test_dir)
            except OSError:
                pass

    def _create_synthetic_workbook(self, filepath: str, year: int):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Results {year}"
        ws.append([f"Regional Championship Meet Results {year}"])
        ws.append([])

        events_def = [
            ("Event 1 Y5G 50 SC Meter Freestyle", 36.0),
            ("Event 2 50 SC Meter Butterfly Y6B", 34.0),
            ("Event 3 Junior Boys 50 SC Meter Backstroke", 38.0),
            ("Event 4 Intermediate Girls 50 SC Meter Breaststroke", 42.0),
            ("Event 5 Senior Boys 100 SC Meter Freestyle", 60.0),
            ("Event 6 Girls 10-13 100 SC Meter Freestyle Relay Y5&6 Girls", 58.0),  # Relay to be excluded
        ]

        for header, base_time in events_def:
            ws.append([header])
            for rank in range(1, 9):
                time_val = round(base_time + (rank - 1) * 0.6 + (year - 2020) * 0.1, 2)
                ws.append([str(rank), f"Swimmer {rank}", "School Alpha", f"{time_val:.2f}"])
            ws.append([])

        wb.save(filepath)

    def test_full_pipeline_dynamic_years(self):
        # Run CLI with explicit 4 arbitrary years
        exit_code = cli_main([
            "--inputs", *self.meet_files,
            "--output-excel", self.excel_out,
            "--output-csv", self.csv_out,
            "--quiet"
        ])
        self.assertEqual(exit_code, 0)

        # 1. Verify Excel Workbook exists and has expected sheets
        self.assertTrue(os.path.exists(self.excel_out))
        wb = openpyxl.load_workbook(self.excel_out)
        self.assertEqual(wb.sheetnames, ["Qualifying Standards", "Audit & Diagnostics"])

        # Check Qualifying Standards sheet (5 individual events)
        ws_standards = wb["Qualifying Standards"]
        rows_standards = list(ws_standards.iter_rows(values_only=True))
        data_rows = [r for r in rows_standards[4:] if any(r)]
        self.assertEqual(len(data_rows), 5)

        # Check Audit & Diagnostics sheet
        ws_audit = wb["Audit & Diagnostics"]
        rows_audit = list(ws_audit.iter_rows(values_only=True))
        header_row = rows_audit[3]
        # Verify all 4 years appear in header columns
        for yr in self.meet_years:
            self.assertIn(f"{yr} Target Time", header_row)
            self.assertIn(f"{yr} Swimmers", header_row)
            self.assertIn(f"{yr} Audit Flag", header_row)

        audit_data_rows = [r for r in rows_audit[4:] if any(r)]
        self.assertEqual(len(audit_data_rows), 5)

        # 2. Verify CSV file
        self.assertTrue(os.path.exists(self.csv_out))
        with open(self.csv_out, mode="r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            self.assertEqual(header, [
                "Event_Number", "Gender", "School_Year", "Distance_M",
                "Stroke", "Qualifying_Time", "Qualifying_Seconds"
            ])
            csv_rows = list(reader)
            self.assertEqual(len(csv_rows), 5)
            # Verify supported divisions and school years
            school_years = [r[2] for r in csv_rows]
            self.assertIn("Y5", school_years)
            self.assertIn("Y6", school_years)
            self.assertIn("Junior", school_years)
            self.assertIn("Intermediate", school_years)
            self.assertIn("Senior", school_years)

    def test_pipeline_input_dir(self):
        exit_code = cli_main([
            "--input-dir", self.test_dir,
            "--output-excel", self.excel_out,
            "--output-csv", self.csv_out,
            "--quiet"
        ])
        self.assertEqual(exit_code, 0)
        self.assertTrue(os.path.exists(self.csv_out))
        self.assertTrue(os.path.exists(self.excel_out))

    def test_pipeline_custom_flags(self):
        exit_code = cli_main([
            "--inputs", *self.meet_files,
            "--combine", "fastest",
            "--target-rank", "10",
            "--output-excel", self.excel_out,
            "--output-csv", self.csv_out,
            "--quiet"
        ])
        self.assertEqual(exit_code, 0)
        self.assertTrue(os.path.exists(self.csv_out))

    def test_console_summary(self):
        reader = WorkbookReader()
        datasets = [reader.read_file(f) for f in self.meet_files]
        aggregator = MultiYearAggregator()
        standards = aggregator.aggregate_meets(datasets)
        # Verify print_console_summary executes cleanly
        print_console_summary(standards, quiet=False)

    def test_missing_input_file_error(self):
        exit_code = cli_main([
            "--inputs", "non_existent_file_999.xlsx",
            "--quiet"
        ])
        self.assertEqual(exit_code, 1)

    def test_empty_directory_error(self):
        empty_dir = os.path.join(self.test_dir, "empty_sub_dir")
        os.makedirs(empty_dir, exist_ok=True)
        exit_code = cli_main([
            "--input-dir", empty_dir,
            "--quiet"
        ])
        self.assertEqual(exit_code, 1)

    def test_corrupt_file_error(self):
        corrupt_file = os.path.join(self.test_dir, "corrupt_sheet.xlsx")
        with open(corrupt_file, "w") as f:
            f.write("This is not a real spreadsheet content.")
        exit_code = cli_main([
            "--inputs", corrupt_file,
            "--quiet"
        ])
        self.assertEqual(exit_code, 1)

    def test_no_events_error(self):
        no_events_file = os.path.join(self.test_dir, "no_events.xlsx")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Just header info", "No swim events here"])
        wb.save(no_events_file)

        exit_code = cli_main([
            "--inputs", no_events_file,
            "--quiet"
        ])
        self.assertEqual(exit_code, 1)

    def test_verbose_flag(self):
        exit_code = cli_main([
            "--inputs", *self.meet_files,
            "--output-excel", self.excel_out,
            "--output-csv", self.csv_out,
            "--verbose"
        ])
        self.assertEqual(exit_code, 0)

    def test_warning_collection(self):
        warn_file = os.path.join(self.test_dir, "warn_test.xlsx")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Event Random Nonparseable Title Without Numbers"])
        ws.append(["1", "Swimmer 1", "Y5", "School A", "DQ"])
        ws.append(["2", "Swimmer 2", "Y5", "School A", "invalid_time"])
        wb.save(warn_file)

        reader = WorkbookReader(verbose=True)
        events = reader.read_file(warn_file, meet_year=2025)
        self.assertEqual(len(events), 0)
        self.assertTrue(len(reader.warnings) > 0)
        # Check that unparseable header warning is present
        self.assertTrue(any("Unable to parse event header" in w for w in reader.warnings))


if __name__ == '__main__':
    unittest.main()
