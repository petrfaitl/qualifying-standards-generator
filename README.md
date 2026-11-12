# Regional Swimming Qualifying Standards Generator

An automated, data-driven system for generating regional swimming championship qualifying standards for  School Sports.

The system balances broad athlete participation against competitive integrity and scheduling efficiency, deriving empirical cutoff times from multi-year meet archives while handling sparse fields and late-heat time blowouts transparently.

---

## Table of Contents
- [Regional Swimming Qualifying Standards Generator](#regional-swimming-qualifying-standards-generator)
  - [Table of Contents](#table-of-contents)
  - [Purpose](#purpose)
  - [Scope](#scope)
    - [Included School Years \& Divisions](#included-school-years--divisions)
    - [Event Header \& Token Disambiguation](#event-header--token-disambiguation)
    - [Excluded Events](#excluded-events)
  - [Sourcing \& Preparing Meet Result Files](#sourcing--preparing-meet-result-files)
    - [1. Exporting from Hy-Tek Meet Manager](#1-exporting-from-hy-tek-meet-manager)
    - [2. Manually Creating a Result File](#2-manually-creating-a-result-file)
    - [3. Calendar Year Agnosticism \& Automatic Discovery](#3-calendar-year-agnosticism--automatic-discovery)
  - [Downloading the Repository Files](#downloading-the-repository-files)
    - [Option 1: Clone with Git (Recommended)](#option-1-clone-with-git-recommended)
    - [Option 2: Download as ZIP Archive](#option-2-download-as-zip-archive)
    - [Repository Contents](#repository-contents)
  - [System Requirements \& Installation](#system-requirements--installation)
    - [Python Version](#python-version)
    - [Required Packages](#required-packages)
    - [Installation Instructions](#installation-instructions)
  - [How to Run the Script](#how-to-run-the-script)
    - [Quick Start (Default Standard Run)](#quick-start-default-standard-run)
    - [Directory Scanning Mode](#directory-scanning-mode)
    - [Custom Target Placing (e.g., 10th Place Cutoff)](#custom-target-placing-eg-10th-place-cutoff)
    - [Alternative Multi-Year Combination Strategies](#alternative-multi-year-combination-strategies)
    - [Alternative Extrapolation Models](#alternative-extrapolation-models)
    - [Verbose Diagnostic Mode](#verbose-diagnostic-mode)
    - [Custom Input Files \& Output Destinations](#custom-input-files--output-destinations)
    - [Automated Unit Testing](#automated-unit-testing)
  - [Command-Line Flags \& Options](#command-line-flags--options)
  - [Mathematical Methodology](#mathematical-methodology)
    - [1. Dynamic Outlier Blowout Detection](#1-dynamic-outlier-blowout-detection)
    - [2. Algorithmic Extrapolation Models](#2-algorithmic-extrapolation-models)
    - [3. Multi-Year Combination Strategies](#3-multi-year-combination-strategies)
  - [Error Handling \& Diagnostic Reporting](#error-handling--diagnostic-reporting)
  - [Generated Outputs \& Deliverables](#generated-outputs--deliverables)
    - [1. Formatted Excel Workbook (`.xlsx`)](#1-formatted-excel-workbook-xlsx)
    - [2. Machine-Readable CSV (`.csv`)](#2-machine-readable-csv-csv)
    - [3. Terminal Console Summary](#3-terminal-console-summary)

---

## Purpose

Establishing regional qualifying barriers requires maximizing overall student welfare, athletic access, and competitive fairness without overwhelming pool session timelines or compromising heat integrity. Fixed arbitrary times often produce severe systemic imbalances: either creating unfillable heats in demanding strokes or causing massive over-subscription in popular sprints.

This tool resolves those challenges by:
1. **Rooting benchmarks in real empirical performance** across arbitrary historical annual cohorts (e.g., 2021, 2024, 2025, 2026, or any arbitrary calendar years).
2. **Supporting all educational age brackets**, encompassing Primary (Year 5, Year 6), Intermediate (Year 7, Year 8), Secondary levels (Year 9–13), combined cohorts (`Y5&6`, `Y7&8`), and named divisions (`Junior`, `Intermediate`, `Senior`, `Open`).
3. **Eliminating cohort bias** by synthesizing multi-year performance using configurable aggregation operators (`average`, `median`, `fastest`).
4. **Protecting against uncompetitive outliers** by dynamically pruning extreme tail drop-offs (blowouts) before cutoffs are calculated.
5. **Providing mathematically consistent extrapolation** when fewer than $n$ athletes completed an event.
6. **Guaranteeing complete institutional transparency** via dynamic multi-year audit logs and detailed error diagnostics that document exactly how every threshold was derived.

---

## Scope

### Included School Years & Divisions
The pipeline automatically identifies, standardizes, and calculates qualifying standards for all individual events contested across school swimming levels:
- **Numerical School Years**: `Y5`, `Y6`, `Y7`, `Y8`, through `Y13`, and standalone numerical tokens (`5`, `6`, `7`, `8`).
- **Combined Year Groups**: Multi-year bands such as `Y5&6` and `Y7&8`.
- **Named Divisions**: `Junior`, `Intermediate`, `Senior`, and `Open` (along with standard abbreviations like `jr`, `in`, `sr`, `jnr`, `int`, `snr`).
- **Genders**: Girls, Boys, and Mixed.
- **Distances**: 25m, 50m, 100m, 200m, etc.
- **Strokes**: Butterfly, Backstroke, Breaststroke, Freestyle, and Individual Medley (IM).

### Event Header & Token Disambiguation
Event result sheets often employ varied shorthand naming conventions. The system includes a composable token disambiguation engine capable of parsing diverse syntax regardless of word order:
- **Combined Year & Gender Tokens**: Automatically splits combined codes in event titles (e.g., `Y5G` $\rightarrow$ Year `Y5`, `Girls`; `Y6B` $\rightarrow$ Year `Y6`, `Boys`; `5G` $\rightarrow$ Year `Y5`, `Girls`; `6B` $\rightarrow$ Year `Y6`, `Boys`).
- **Combined Division & Gender Tokens**: Disambiguates codes such as `JrG` / `JrB` $\rightarrow$ `Junior`, `Girls` / `Boys`; `InG` / `InB` $\rightarrow$ `Intermediate`, `Girls` / `Boys`; `SrG` / `SrB` $\rightarrow$ `Senior`, `Girls` / `Boys`.
- **Flexible Event Syntax**: Accurately extracts metadata from varied phrasing:
  - `Event 5 Y5G 50 SC Meter Freestyle`
  - `Event 12 Junior Boys 50 SC Meter Backstroke`
  - `Event 3 50 SC Meter Butterfly Y6B`
  - `Event 1 Girls 12 & Over 100 SC Meter Breaststroke Y8 Girls`
  - `Event 9 Girls 100 SC Meter IM Intermediate`
- **Swimmer Row Year/School Disambiguation**: In 4-column swimmer results (`[Rank, Name, Token, Time]`), the parser dynamically distinguishes whether the third column represents a school year / division (e.g. `5`, `Y6`, `jr`, `in`, `sr`) or a school/club name (e.g. `St Peters`, `Hillcrest`).

### Excluded Events
- **Relay Events (e.g., 4x50m, 100m Freestyle Relays)**: Relays measure school team aggregate speed rather than individual athletic qualification, and historical scheduling varies across years. The parser automatically detects and filters out relay events from standard calculations (configurable via `--include-relays` in programmatic usage).

---

## Sourcing & Preparing Meet Result Files

### 1. Exporting from Hy-Tek Meet Manager
The standard way to produce historical meet results from Hy-Tek Meet Manager is as follows:

1. Open Hy-Tek Meet Manager with your historical meet database loaded.
2. From the top navigation menu, navigate to:
   **Reports** > **Results**
3. In the Results Report filter window:
   - Under **Event Selection**, click **Select All** (or choose all individual events).
   - Under **Gender**, select **Both** (Girls and Boys).
   - In the **Top How Many** field, limit the report length to your desired benchmark depth (e.g. enter **`8`** for top-8 times, or **`10`** for top-10).
   - Click **Create Report**.
4. In the Print/Export Reports preview window:
   - Click the **Export Report** button (floppy disk or export icon).
   - In the export format dropdown, select:
     **`Microsoft Excel 97-2000 Data only (XLS)`**
   - Click **OK** and choose your destination.
5. Save or rename the exported workbook using standard names containing the calendar year (e.g., `results-2021.xls`, `results-2024.xls`, `results-2025.xls`, `results-2026.xls`, `wbop2028-top8.xls`).

### 2. Manually Creating a Result File
If you do not have Hy-Tek Meet Manager or need to provide results from another source (such as manual timekeeping sheets or custom spreadsheets), you can create an `.xls` or `.xlsx` workbook following this simple layout:

- **Format**: Standard Microsoft Excel (`.xls` or `.xlsx`).
- **Event Header**: Each event section must begin with a descriptive header cell starting with `Event <Number>`, followed by gender, school year/division, distance, and stroke in any standard order.
  - *Example (Traditional)*: `Event 1  Girls 12 & Over 100 SC Meter Breaststroke Y8 Girls`
  - *Example (Combined code)*: `Event 5 Y5G 50 SC Meter Freestyle`
  - *Example (Named division)*: `Event 12 Junior Boys 50 SC Meter Backstroke`
  - *Example (Suffix code)*: `Event 3 50 SC Meter Butterfly Y6B`
  - *Example (Intermediate IM)*: `Event 9 Girls 100 SC Meter IM Intermediate`
- **Results Rows**: Underneath each event header, list finishers in placing order. The row can contain standard column headers or go directly to swimmer entries:
  - **Rank / Placing**: 1st column containing placing integer (`1`, `2`, `3`...) or tie indicator (`*1`, `*2`).
  - **Swimmer Name**: Last name, First name (or First Last).
  - **Year Group / Division**: School year (`Y5`, `Y6`, `Y7`, `Y8`, `5`, `6`) or division (`Junior`, `Intermediate`, `Senior`, `jr`, `in`, `sr`).
  - **School / Club**: School or team name (e.g. `Hillcrest`, `St Peters`).
  - **Finals Time**: The clock time as the final token in the row.
- **Flexible Row Column Formats**:
  - *5-token rows*: `[Rank, Name, Year, School, Time]` (e.g., `["1", "Alice Smith", "Y5", "Hillcrest", "35.20"]`)
  - *4-token rows (with Year)*: `[Rank, Name, Year, Time]` (e.g., `["2", "Beth Jones", "5", "36.10"]`)
  - *4-token rows (with School)*: `[Rank, Name, School, Time]` (e.g., `["3", "Chloe Adams", "St Peters", "37.05"]`)
  - *3-token rows*: `[Rank, Name, Time]` (e.g., `["4", "Diana Prince", "38.50"]`)
- **Time Format**: Supported formats include `M:SS.ss` (e.g., `1:24.01`, `2:10.84`) and `SS.ss` (e.g., `35.76`, `49.89`).
- **Non-Finishers**: Swimmers marked as `DQ`, `DNF`, `SCR`, `NS`, or `NT` are automatically ignored by the ingestion engine without disrupting valid finisher times.

### 3. Calendar Year Agnosticism & Automatic Discovery
The generator is fully calendar-year agnostic and dynamically adapts to any past, present, or future meet archives:
- **Filename Year Extraction**: Detects 4-digit years (`1900`–`2099`) or contextual 2-digit years across filenames and folder paths.
- **Worksheet Header Fallback**: If filenames lack year identifiers, the engine inspects top worksheet title rows for year references.
- **Arbitrary Year Counts**: Seamlessly handles any number of annual input files (e.g., single-year baseline, 3-year historical cohorts, 5-year archives, or more).
- **Missing Annual Events**: When an event was contested in only a subset of years, available years are aggregated cleanly while audit flags transparently record available cohort counts.

---

## Downloading the Repository Files

To run the qualifying standards generator, you need to download or clone the repository to your local computer.

### Option 1: Clone with Git (Recommended)
If you have Git installed, open your terminal (PowerShell, Command Prompt, or Bash) and clone the repository:

```powershell
# Clone the repository to your local machine
git clone https://github.com/petrfaitl/qualifying-standards-generator.git

# Navigate into the project folder
cd qualifying-standards-generator
```

### Option 2: Download as ZIP Archive
If you do not use Git:
1. Navigate to the repository page on GitHub: [`https://github.com/petrfaitl/qualifying-standards-generator`](https://github.com/petrfaitl/qualifying-standards-generator)
2. Click the green **Code** button near the top right of the file list.
3. Select **Download ZIP** from the dropdown menu.
4. Extract the downloaded ZIP archive to your desired directory (e.g., `C:\Swimming\qualifying-standards-generator`).
5. Open your terminal in the extracted folder.

### Repository Contents
Once downloaded or extracted, verify that the project directory contains the required files and modules:
- `generate_qualifying_standards.py`: The executable command-line interface.
- `requirements.txt`: Python package dependency specifications.
- `swim_standards/`: Python package containing parser, extrapolator, aggregator, and exporter modules.
- `tests/`: Automated unit and integration test suite.
- `results-2024.xls`, `results-2025.xls`, `results-2026.xls`: Historical meet result archives.

---

## System Requirements & Installation

### Python Version
- **Python 3.10** or higher is required.

### Required Packages
The script relies on three standard third-party libraries:
| Package | Minimum Version | Purpose |
| :--- | :--- | :--- |
| `xlrd` | `2.0.1` | Ingests legacy Microsoft Excel binary workbooks (`.xls`, BIFF8 format). |
| `openpyxl` | `3.0.0` | Creates styled, publication-ready modern Excel workbooks (`.xlsx`) with formatting and auto-fitted columns. |
| `numpy` | `1.20.0` | Powers statistical median step computations and ordinary least-squares regression trendlines. |

### Installation Instructions

1. Open your terminal (PowerShell, Command Prompt, or Bash) in the project directory:
   ```powershell
   cd qualifying-standards-generator
   ```

2. Install all required dependencies using `requirements.txt`:
   ```powershell
   pip install -r requirements.txt
   ```

   *Alternatively, install the packages directly:*
   ```powershell
   pip install xlrd openpyxl numpy
   ```

3. Verify installation:
   ```powershell
   python -c "import xlrd, openpyxl, numpy; print('Environment ready!')"
   ```

---

## How to Run the Script

### Quick Start (Default Standard Run)
To generate the official regional qualifying standards using the default parameters (Target Rank: **8th place**, Extrapolation: **step-average**, Combination: **multi-year average**, Outlier threshold: **2.0x**):

```powershell
python generate_qualifying_standards.py
```

When run with no arguments, the tool automatically checks for generic annual result workbooks (`results-2024.xls`, `results-2025.xls`, `results-2026.xls`) in the project directory, or automatically scans the directory for `.xls`/`.xlsx` meet results. It prints an ANSI summary table to the console and writes:
- `qualifying-standards.xlsx` (Styled Excel workbook with Standards + Audit Trace sheets)
- `qualifying-standards.csv` (Meet software import file)

---

### Directory Scanning Mode
Instead of listing individual file paths, you can provide an input directory containing your `.xls` or `.xlsx` result archives using the `--input-dir` (or `-d` / `--dir`) flag. The tool automatically discovers all valid meet files, orders them chronologically by year, and ignores temporary lock files:

```powershell
# Scan a specific directory for meet result spreadsheets
python generate_qualifying_standards.py --input-dir "C:\Swimming\HistoricalResults"

# Short flag variant
python generate_qualifying_standards.py -d ./data
```

---

### Custom Target Placing (e.g., 10th Place Cutoff)
To expand regional participation opportunities by setting the qualification barrier to 10th place (or restrict to 6th place):

```powershell
# Set qualifying benchmark to 10th position
python generate_qualifying_standards.py --target-rank 10 --output-excel standards-top10.xlsx --output-csv standards-top10.csv
```

---

### Alternative Multi-Year Combination Strategies
Control how annual meet times are combined across historical cohorts:

```powershell
# Median: Maximizes resistance against single-cohort anomalies
python generate_qualifying_standards.py --combine median

# Fastest: Selects the strictest performance mark across the years
python generate_qualifying_standards.py --combine fastest
```

---

### Alternative Extrapolation Models
When an event has fewer valid finishers than the target rank, select between different projection methods:

```powershell
# Linear Trendline: Fits an ordinary least-squares regression line
python generate_qualifying_standards.py --extrapolate linear-trend

# Percentage Increment: Compounds the final valid time by +3.5% per rank position
python generate_qualifying_standards.py --extrapolate percent-increment
```

---

### Verbose Diagnostic Mode
To view line-by-line parsing details, skipped non-finisher records, and row-level warning diagnostics:

```powershell
# Enable verbose diagnostic logging
python generate_qualifying_standards.py --verbose

# Short flag variant
python generate_qualifying_standards.py -v
```

---

### Custom Input Files & Output Destinations
To run the tool against specific historical workbooks or custom output paths:

```powershell
python generate_qualifying_standards.py `
  --inputs "results-2021.xls" "results-2024.xls" "results-2025.xls" "results-2026.xls" `
  --output-excel "2027-qualifying-standards.xlsx" `
  --output-csv "2027-qualifying-standards.csv"
```

To suppress console logging for batch operations or script integration, add `--quiet`:
```powershell
python generate_qualifying_standards.py --quiet
```

---

### Automated Unit Testing
To verify data ingestion, mathematical models, directory scanning, and report exporters against the automated test suite:

```powershell
python -m unittest discover tests
```

---

## Command-Line Flags & Options

| Flag | Short | Default | Allowed Values | Description |
| :--- | :---: | :---: | :--- | :--- |
| `--inputs` | | Auto-detected | File paths | One or more space-separated `.xls` or `.xlsx` meet result workbooks. If omitted, automatically discovers available meet files in the directory. |
| `--input-dir` / `--dir` | `-d` | `None` | Directory path | Path to a folder to automatically scan for `.xls` and `.xlsx` meet result files across arbitrary calendar years. |
| `--target-rank` | `-n` | `8` | Positive Integer ($\ge 1$) | The placing rank used as the qualifying cutoff (e.g., 8 for 8th place, 10 for 10th place). |
| `--extrapolate` | | `step-average` | `step-average`, `linear-trend`, `percent-increment` | Mathematical method used to project target times when valid finishers $< n$. |
| `--combine` | | `average` | `average`, `median`, `fastest` | Multi-year aggregation method for synthesizing annual times into a single cutoff. |
| `--gap-threshold`| | `2.0` | Float ($\ge 1.0$) | Multiplier over the median time differential ($\Delta$) used to flag uncompetitive tail blowouts. |
| `--output-excel`| | `qualifying-standards.xlsx` | File path | Destination path for the styled Excel workbook containing Standards and Audit sheets. |
| `--output-csv`  | | `qualifying-standards.csv` | File path | Destination path for the machine-readable CSV file. |
| `--verbose`     | `-v` | `False` | Flag | Display detailed diagnostic parsing logs and row-level warnings. |
| `--quiet`       | `-q` | `False` | Flag | Suppress console summary tables and diagnostic messages. |
| `--help`        | `-h` | | | Display the help message and argument descriptions. |

---

## Mathematical Methodology

### 1. Dynamic Outlier Blowout Detection
Athletic heats occasionally include a tail swimmer who suffered an equipment failure, injury, or unrepresentative drop-off (for example, in 2024 Event 11, 5th place finished in 1:40.35 while 6th place finished in 2:14.19, a +33.84s jump). Using that 6th place time directly would unduly lower standards and distort heat allocation.

The algorithm:
1. Calculates sequential time steps $\Delta_i = T_i - T_{i-1}$ for each finisher.
2. Identifies anomalous drops where:
   $$\Delta_i > \max\left(\text{threshold} \times \text{median}(\Delta_{2..i-1}),\; \text{floor buffer}\right)$$
   *(The dynamic floor buffer scales with race duration: $\max(3.5\text{s}, 0.12 \times T_{i-1})$).*
3. Distinguishes tail blowouts from fast breakaway winners by verifying if remaining swimmers form a clustered pack.
4. Truncates unrepresentative tail times and extrapolates outward from dependable competitive ranks.

### 2. Algorithmic Extrapolation Models
When an event has $m < n$ valid finishers:
- **`step-average` (Default)**: Calculates the average step among valid finishers $\overline{\Delta} = \frac{T_m - T_1}{m - 1}$ and projects forward:
  $$T_n = T_m + (n - m) \times \overline{\Delta}$$
- **`linear-trend`**: Fits an ordinary least-squares regression line $T(r) = \alpha \cdot r + \beta$ over ranks $r \in \{1, \dots, m\}$ and evaluates $T(n)$.
- **`percent-increment`**: Compounds the final valid time by $p = 3.5\%$ per place:
  $$T_n = T_m \times (1 + p)^{n - m}$$

### 3. Multi-Year Combination Strategies
For each event, the target rank times $T_{y_1}, T_{y_2}, \dots, T_{y_k}$ across all $k$ historical meet cohorts are synthesized:
- **`average` (Default)**: Arithmetic mean $\frac{1}{k}\sum_{j=1}^k T_{y_j}$. Distributes weighting evenly across all cohorts to smooth year-to-year grade strength variations.
- **`median`**: Middle value. Maximizes stability against single-year weather or timing anomalies.
- **`fastest`**: Minimum value $\min(T_{y_j})$. Defines a strict, aspirational performance standard.

---

## Error Handling & Diagnostic Reporting

To ensure operational reliability and transparent troubleshooting, the system incorporates structured error handling and layered diagnostics:
- **Missing or Inaccessible Input Files**: Emits clear descriptive errors to `sys.stderr` and exits cleanly with non-zero exit code `1` without stack traces.
- **Empty Directories or Unparseable Spreadsheets**: Detects when directories contain no valid meet workbooks or sheets lack valid events, providing immediate actionable guidance.
- **Corrupt or Malformed Swimmer Rows**: Collects row-level warnings (identifying filename, row index, and issue description) while continuing to ingest valid events.
- **Verbose Trace Logging**: Activating `--verbose` (`-v`) outputs real-time parsing traces, skipped non-finisher tags (`DQ`, `DNF`, `SCR`, `NS`), and outlier pruning decisions.

---

## Generated Outputs & Deliverables

### 1. Formatted Excel Workbook (`.xlsx`)
The generated workbook includes two structured tabs:
- **`Qualifying Standards` Sheet**:
  - High-contrast, clean corporate layout designed for printing or posting to regional athletic associations.
  - Columns: Event Number, Gender, School Year / Division, Distance, Stroke, and Qualifying Time (formatted as `MM:SS.ss` or `SS.ss`).
- **`Audit & Diagnostics` Sheet**:
  - Detailed transparency logging for meet directors and school coaches.
  - Dynamically constructs column triplets for every calendar year present in the dataset (`{yr} Target Time`, `{yr} Swimmers`, `{yr} Audit Flag`).
  - Columns: Target Rank, Final Standard (formatted & seconds), Multi-Year Spread (Std Dev), annual times, participant counts, and explicit calculation method flags (e.g., `Direct`, `Extrapolated (Step-Mean)`, `Pruned Outlier at Rank 6 -> Extrapolated`, or `Not Contested`).

### 2. Machine-Readable CSV (`.csv`)
A standardized comma-separated values file designed for automated import into meet management platforms (e.g., Meet Manager, RaceTec, SportsEngine):
```csv
Event_Number,Gender,School_Year,Distance_M,Stroke,Qualifying_Time,Qualifying_Seconds
1,Girls,Y5,50,Freestyle,35.20,35.20
2,Boys,Junior,50,Backstroke,38.50,38.50
...
15,Girls,Y8,100,Breaststroke,1:31.13,91.13
...
```

### 3. Terminal Console Summary
When executed, the script outputs a color-coded terminal table detailing each event standard, dynamically formatting column headers and widths for all supplied calendar years, flagging extrapolated results with an asterisk (`*`), and summarizing overall dataset statistics.
