#!/usr/bin/env python3
"""
Command-Line Interface (CLI) for generating swimming qualifying standards
from historical championship meet data.
"""

import argparse
import os
import sys
from typing import List, Optional

from swim_standards.parser import WorkbookReader, extract_year_from_filename
from swim_standards.aggregator import MultiYearAggregator
from swim_standards.exporter import export_to_excel, export_to_csv, print_console_summary


def scan_directory_for_results(directory: str, exclude_files: Optional[List[str]] = None) -> List[str]:
    """
    Scans a directory for .xls and .xlsx meet result files,
    ignoring temporary lock files and generated output files.
    """
    if not os.path.isdir(directory):
        raise NotADirectoryError(f"Specified input directory does not exist: {directory}")

    exclude_set = {os.path.basename(f).lower() for f in (exclude_files or [])}
    found_files = []
    for entry in os.listdir(directory):
        full_path = os.path.join(directory, entry)
        if not os.path.isfile(full_path):
            continue
        entry_lower = entry.lower()
        if entry.startswith("~$"):
            continue
        if not (entry_lower.endswith(".xls") or entry_lower.endswith(".xlsx")):
            continue
        # Exclude generated standards output files
        if "qualifying-standards" in entry_lower or "test-standards" in entry_lower:
            continue
        if entry_lower in exclude_set:
            continue
        found_files.append(full_path)

    # Deduplicate by meet year if multiple files exist for the same year
    # (e.g. prefer 'results-2024.xls' over 'wbop2024-top8.xls')
    year_to_file = {}
    no_year_files = []

    for path in found_files:
        yr = extract_year_from_filename(path)
        if yr is None:
            no_year_files.append(path)
        else:
            if yr not in year_to_file:
                year_to_file[yr] = path
            else:
                existing = year_to_file[yr]
                existing_base = os.path.basename(existing).lower()
                new_base = os.path.basename(path).lower()
                if "results-" in new_base and "results-" not in existing_base:
                    year_to_file[yr] = path

    final_files = [year_to_file[yr] for yr in sorted(year_to_file.keys())] + sorted(no_year_files)
    return final_files


def resolve_input_files(
    inputs: Optional[List[str]] = None,
    input_dir: Optional[str] = None,
    output_excel: Optional[str] = None
) -> List[str]:
    """
    Resolves input meet result workbooks from explicit file arguments,
    an explicit input directory, or dynamic directory scans.
    """
    exclude_list = [output_excel] if output_excel else []

    if inputs:
        resolved = []
        for path in inputs:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Input file not found: {path}")
            resolved.append(path)
        return resolved

    if input_dir:
        files = scan_directory_for_results(input_dir, exclude_files=exclude_list)
        if not files:
            raise FileNotFoundError(f"No XLS/XLSX meet result files found in directory: {input_dir}")
        return files

    # Dynamic scan in current working directory
    scanned = scan_directory_for_results(".", exclude_files=exclude_list)
    if scanned:
        return scanned

    raise FileNotFoundError(
        "No meet result files found. Please provide file paths via --inputs (e.g. --inputs results-2024.xls results-2025.xls) "
        "or specify a directory containing .xls/.xlsx files via --input-dir."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate  swimming qualifying standards from historical meet workbooks."
    )
    parser.add_argument(
        "--inputs",
        nargs="+",
        default=None,
        help="Path to specific input XLS/XLSX workbooks (default: generic results-2024.xls results-2025.xls results-2026.xls, or scanned from directory)"
    )
    parser.add_argument(
        "--input-dir", "-d", "--dir",
        dest="input_dir",
        default=None,
        help="Directory path to scan for result XLS/XLSX files (e.g. --input-dir ./results)"
    )
    parser.add_argument(
        "--target-rank", "-n",
        type=int,
        default=8,
        help="Target placing to calculate/extrapolate (default: 8)"
    )
    parser.add_argument(
        "--extrapolate",
        choices=["step-average", "linear-trend", "percent-increment"],
        default="step-average",
        help="Extrapolation model: step-average, linear-trend, percent-increment (default: step-average)"
    )
    parser.add_argument(
        "--combine",
        choices=["average", "median", "fastest"],
        default="average",
        help="Multi-year combination strategy: average, median, fastest (default: average)"
    )
    parser.add_argument(
        "--gap-threshold",
        type=float,
        default=2.0,
        help="Multiplier over median step to flag an outlier blowout (default: 2.0)"
    )
    parser.add_argument(
        "--output-excel",
        default="qualifying-standards.xlsx",
        help="Output path for styled Excel workbook (default: qualifying-standards.xlsx)"
    )
    parser.add_argument(
        "--output-csv",
        default="qualifying-standards.csv",
        help="Output path for machine-readable CSV (default: qualifying-standards.csv)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose console audit diagnostics"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable detailed diagnostic logging of parser operations and warnings"
    )
    return parser


def main(args: List[str] = None) -> int:
    parser = build_parser()
    parsed_args = parser.parse_args(args)

    try:
        input_files = resolve_input_files(
            inputs=parsed_args.inputs,
            input_dir=parsed_args.input_dir,
            output_excel=parsed_args.output_excel
        )
    except Exception as e:
        sys.stderr.write(f"Error locating input meet files: {e}\n")
        return 1

    if not parsed_args.quiet:
        print("\n=======================================================")
        print("  Swimming Qualifying Standards Generator")
        print("=======================================================")
        print(f" Target Rank           : {parsed_args.target_rank}")
        print(f" Extrapolation Method  : {parsed_args.extrapolate}")
        print(f" Combination Strategy  : {parsed_args.combine}")
        print(f" Outlier Gap Threshold : {parsed_args.gap_threshold}x")
        print(f" Input Files ({len(input_files)})       : {', '.join(input_files)}")
        print("=======================================================\n")

    reader = WorkbookReader(exclude_relays=True, verbose=parsed_args.verbose)
    datasets = []
    for filepath in input_files:
        try:
            events = reader.read_file(filepath)
            if not parsed_args.quiet:
                print(f"Loaded {len(events):>2} individual events from: {filepath}")
            datasets.append(events)
        except Exception as e:
            sys.stderr.write(f"Error reading file '{filepath}': {e}\n")
            return 1

    if parsed_args.verbose and reader.warnings:
        print("\n--- Diagnostic & Parsing Warnings ---")
        for w in reader.warnings:
            print(f"  [!] {w}")
        print("-------------------------------------\n")

    if not any(len(d) > 0 for d in datasets):
        sys.stderr.write("Error: No valid individual swimming events found in the provided input files.\n")
        return 1

    aggregator = MultiYearAggregator(
        target_rank=parsed_args.target_rank,
        combine_method=parsed_args.combine,
        extrapolate_method=parsed_args.extrapolate,
        gap_threshold=parsed_args.gap_threshold
    )

    try:
        standards = aggregator.aggregate_meets(datasets)
    except Exception as e:
        sys.stderr.write(f"Error synthesizing standards: {e}\n")
        return 1

    # Output exports
    try:
        export_to_excel(standards, parsed_args.output_excel)
        if not parsed_args.quiet:
            print(f"\n[+] Successfully exported Excel workbook: {parsed_args.output_excel}")
    except Exception as e:
        sys.stderr.write(f"Error generating Excel output: {e}\n")
        return 1

    try:
        export_to_csv(standards, parsed_args.output_csv)
        if not parsed_args.quiet:
            print(f"[+] Successfully exported CSV file      : {parsed_args.output_csv}")
    except Exception as e:
        sys.stderr.write(f"Error generating CSV output: {e}\n")
        return 1

    print_console_summary(standards, quiet=parsed_args.quiet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
