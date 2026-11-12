"""
End-to-end integration tests over the complete 2024-2026 dataset.
"""

import os
import unittest
import openpyxl
import csv
from generate_qualifying_standards import main as cli_main


class TestEndToEnd(unittest.TestCase):

    def setUp(self):
        self.excel_out = "wbop2027-test-standards.xlsx"
        self.csv_out = "wbop2027-test-standards.csv"

    def tearDown(self):
        for path in [self.excel_out, self.csv_out]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

    def test_full_pipeline_default(self):
        # Run CLI with default parameters
        exit_code = cli_main([
            "--output-excel", self.excel_out,
            "--output-csv", self.csv_out,
            "--quiet"
        ])
        self.assertEqual(exit_code, 0)

        # 1. Verify Excel Workbook exists and has expected sheets
        self.assertTrue(os.path.exists(self.excel_out))
        wb = openpyxl.load_workbook(self.excel_out)
        self.assertEqual(wb.sheetnames, ["Qualifying Standards", "Audit & Diagnostics"])

        # Check Qualifying Standards sheet
        ws_standards = wb["Qualifying Standards"]
        rows_standards = list(ws_standards.iter_rows(values_only=True))
        # Title is at rows 0, 1; header at row 3 (0-indexed)
        # There should be 4 header/title rows + 36 data rows = 40 rows
        data_rows = [r for r in rows_standards[4:] if any(r)]
        self.assertEqual(len(data_rows), 36)

        # Check Audit & Diagnostics sheet
        ws_audit = wb["Audit & Diagnostics"]
        rows_audit = list(ws_audit.iter_rows(values_only=True))
        audit_data_rows = [r for r in rows_audit[4:] if any(r)]
        self.assertEqual(len(audit_data_rows), 36)

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
            self.assertEqual(len(csv_rows), 36)

        # 3. Verify specific benchmark calculations
        # Y8 Girls 50m Freestyle (2024: 36.38, 2025: 36.54, 2026: 34.37)
        # Standard: (36.38 + 36.54 + 34.37) / 3 = 35.76s
        freestyle_50_row = [r for r in csv_rows if r[1] == "Girls" and r[2] == "Y8" and r[3] == "50" and r[4] == "Freestyle"][0]
        self.assertEqual(freestyle_50_row[5], "35.76")
        self.assertEqual(freestyle_50_row[6], "35.76")

    def test_pipeline_custom_flags(self):
        # Run CLI with --combine fastest and --target-rank 10
        exit_code = cli_main([
            "--combine", "fastest",
            "--target-rank", "10",
            "--output-excel", self.excel_out,
            "--output-csv", self.csv_out,
            "--quiet"
        ])
        self.assertEqual(exit_code, 0)
        self.assertTrue(os.path.exists(self.csv_out))

        with open(self.csv_out, mode="r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)
            csv_rows = list(reader)
            self.assertEqual(len(csv_rows), 36)

    def test_pipeline_input_dir(self):
        # Run CLI with --input-dir
        exit_code = cli_main([
            "--input-dir", ".",
            "--output-excel", self.excel_out,
            "--output-csv", self.csv_out,
            "--quiet"
        ])
        self.assertEqual(exit_code, 0)
        self.assertTrue(os.path.exists(self.csv_out))
        self.assertTrue(os.path.exists(self.excel_out))

    def test_pipeline_explicit_inputs(self):
        # Run CLI with explicit generic files
        exit_code = cli_main([
            "--inputs", "results-2024.xls", "results-2025.xls", "results-2026.xls",
            "--output-excel", self.excel_out,
            "--output-csv", self.csv_out,
            "--quiet"
        ])
        self.assertEqual(exit_code, 0)
        self.assertTrue(os.path.exists(self.csv_out))
        self.assertTrue(os.path.exists(self.excel_out))


if __name__ == '__main__':
    unittest.main()
