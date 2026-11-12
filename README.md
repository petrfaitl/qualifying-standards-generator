# Regional Swimming Qualifying Standards Generator

An automated, data-driven system for generating regional swimming championship qualifying standards for Intermediate School Sports (Year 7 and Year 8 Girls and Boys).

The system balances broad athlete participation against competitive integrity and scheduling efficiency, deriving empirical cutoff times from multi-year meet archives while handling sparse fields and late-heat time blowouts transparently.

---

## Table of Contents
- [Regional Swimming Qualifying Standards Generator](#regional-swimming-qualifying-standards-generator)
  - [Table of Contents](#table-of-contents)
  - [Purpose](#purpose)
  - [Scope](#scope)
    - [Included Events](#included-events)
    - [Excluded Events](#excluded-events)
  - [Sourcing \& Preparing Meet Result Files](#sourcing--preparing-meet-result-files)
    - [1. Exporting from Hy-Tek Meet Manager](#1-exporting-from-hy-tek-meet-manager)
    - [2. Manually Creating a Result File](#2-manually-creating-a-result-file)
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
    - [Custom Input Files \& Output Destinations](#custom-input-files--output-destinations)
    - [Automated Unit Testing](#automated-unit-testing)
  - [Command-Line Flags \& Options](#command-line-flags--options)
  - [Mathematical Methodology](#mathematical-methodology)
    - [1. Dynamic Outlier Blowout Detection](#1-dynamic-outlier-blowout-detection)
    - [2. Algorithmic Extrapolation Models](#2-algorithmic-extrapolation-models)
    - [3. Multi-Year Combination Strategies](#3-multi-year-combination-strategies)
  - [Generated Outputs \& Deliverables](#generated-outputs--deliverables)
    - [1. Formatted Excel Workbook (`.xlsx`)](#1-formatted-excel-workbook-xlsx)
    - [2. Machine-Readable CSV (`.csv`)](#2-machine-readable-csv-csv)
    - [3. Terminal Console Summary](#3-terminal-console-summary)

---

## Purpose

Establishing regional qualifying barriers requires maximizing overall student welfare and athletic access without overwhelming pool session timelines or compromising heat competitiveness. Fixed arbitrary times often produce severe imbalances: either creating unfillable heats in demanding strokes or causing massive over-subscription in popular sprints.

This tool resolves those challenges by:
1. **Rooting benchmarks in real empirical performance** across multiple annual cohorts (2024, 2025, and 2026).
2. **Eliminating cohort bias** by synthesizing multi-year performance using configurable aggregation operators (`average`, `median`, `fastest`).
3. **Protecting against uncompetitive outliers** by dynamically pruning extreme tail drop-offs (blowouts) before cutoffs are calculated.
4. **Providing mathematically consistent extrapolation** when fewer than $n$ athletes completed an event.
5. **Guaranteeing complete institutional transparency** via an accompanying diagnostic audit trail that documents exactly how every threshold was derived.

---

## Scope

### Included Events
The pipeline automatically identifies, standardizes, and calculates qualifying standards for all **36 individual events** contested in Intermediate School Swimming:
- **School Years**: Year 7 (Y7) and Year 8 (Y8).
- **Genders**: Girls and Boys.
- **Distances**: 25m, 50m, and 100m.
- **Strokes**: Butterfly, Backstroke, Breaststroke, Freestyle, and 100m Individual Medley (IM).

### Excluded Events
- **Relay Events (e.g., Events 17 & 18 - 100m Freestyle Relays)**: Relays measure school team aggregate speed rather than individual athletic qualification, and historical scheduling varies across years. The parser automatically detects and filters out relay events from standard calculations.

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
5. Save or rename the exported workbook using standard generic names containing the 4-digit meet year (e.g., `results-2024.xls`, `results-2025.xls`, `results-2026.xls`).

### 2. Manually Creating a Result File
If you do not have Hy-Tek Meet Manager or need to provide results from another source (such as manual timekeeping sheets or custom spreadsheets), you can create an `.xls` or `.xlsx` workbook following this simple layout:

- **Format**: Standard Microsoft Excel (`.xls` or `.xlsx`).
- **Event Header**: Each event section must begin with a descriptive header cell starting with `Event <Number>`, followed by gender, age/school year, distance, and stroke.
  - *Example*: `Event 1  Girls 12 & Over 100 SC Meter Breaststroke Y8 Girls`
  - *Example*: `Event 17 Boys 11-12 50 SC Meter Freestyle Y7 Boys`
- **Results Rows**: Underneath each event header, list finishers in placing order. The row can contain standard column headers or go directly to swimmer entries:
  - **Rank / Placing**: 1st column containing placing integer (`1`, `2`, `3`...) or tie indicator (`*1`, `*2`).
  - **Swimmer Name**: Last name, First name (or First Last).
  - **Year / Age Group**: Optional school year indicator (`Y7`, `Y8`, `11`, `12`).
  - **School / Club**: School or team name.
  - **Finals Time**: The clock time as the final token in the row.
- **Time Format**: Supported formats include `M:SS.ss` (e.g., `1:24.01`, `2:10.84`) and `SS.ss` (e.g., `35.76`, `49.89`).
- **Non-Finishers**: Swimmers marked as `DQ`, `DNF`, `SCR`, `NS`, or `NT` are automatically ignored by the ingestion engine.

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
   cd "C:\Meets\Meets Regional\School Sports\2027\Intermediate\WBOP"
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

### Custom Input Files & Output Destinations
To run the tool against specific historical workbooks or custom output paths:

```powershell
python generate_qualifying_standards.py `
  --inputs "results-2024.xls" "results-2025.xls" "results-2026.xls" `
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
| `--inputs` | | `results-2024.xls ...` | File paths | One or more space-separated `.xls` or `.xlsx` meet result workbooks. If omitted, checks generic names or scans directory. |
| `--input-dir` / `--dir` | `-d` | `None` | Directory path | Path to a folder to automatically scan for `.xls` and `.xlsx` meet result files. |
| `--target-rank` | `-n` | `8` | Positive Integer ($\ge 1$) | The placing rank used as the qualifying cutoff (e.g., 8 for 8th place, 10 for 10th place). |
| `--extrapolate` | | `step-average` | `step-average`, `linear-trend`, `percent-increment` | Mathematical method used to project target times when valid finishers $< n$. |
| `--combine` | | `average` | `average`, `median`, `fastest` | Multi-year aggregation method for synthesizing annual times into a single cutoff. |
| `--gap-threshold`| | `2.0` | Float ($\ge 1.0$) | Multiplier over the median time differential ($\Delta$) used to flag uncompetitive tail blowouts. |
| `--output-excel`| | `qualifying-standards.xlsx` | File path | Destination path for the styled Excel workbook containing Standards and Audit sheets. |
| `--output-csv`  | | `qualifying-standards.csv` | File path | Destination path for the machine-readable CSV file. |
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
For each event, the target rank times $T_{2024}, T_{2025}, T_{2026}$ are synthesized:
- **`average` (Default)**: Arithmetic mean $\frac{1}{k}\sum T_y$. Distributes weighting evenly across all cohorts to smooth year-to-year grade strength variations.
- **`median`**: Middle value. Maximizes stability against single-year weather or timing anomalies.
- **`fastest`**: Minimum value $\min(T_y)$. Defines a strict, aspirational performance standard.

---

## Generated Outputs & Deliverables

### 1. Formatted Excel Workbook (`.xlsx`)
The generated workbook includes two structured tabs:
- **`Qualifying Standards` Sheet**:
  - High-contrast, clean corporate layout designed for printing or posting to regional athletic associations.
  - Columns: Event Number, Gender, School Year, Distance, Stroke, and Qualifying Time (formatted as `MM:SS.ss` or `SS.ss`).
- **`Audit & Diagnostics` Sheet**:
  - Detailed transparency logging for meet directors and school coaches.
  - Columns: Target Rank, Final Standard (formatted & seconds), Multi-Year Spread (Std Dev), Annual Times for 2024, 2025, and 2026 with participant counts, and explicit calculation method flags (e.g., `Direct`, `Extrapolated (Step-Mean)`, or `Pruned Outlier at Rank 6 -> Extrapolated`).

### 2. Machine-Readable CSV (`.csv`)
A standardized comma-separated values file designed for automated import into meet management platforms (e.g., Meet Manager, RaceTec, SportsEngine):
```csv
Event_Number,Gender,School_Year,Distance_M,Stroke,Qualifying_Time,Qualifying_Seconds
1,Boys,Y7,25,Butterfly,25.70,25.70
...
20,Girls,Y8,50,Freestyle,35.76,35.76
...
```

### 3. Terminal Console Summary
When executed, the script outputs a color-coded terminal table detailing each event standard, flagging extrapolated results with an asterisk (`*`) and summarizing overall dataset statistics.
