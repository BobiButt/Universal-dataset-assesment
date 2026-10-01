# Dataset Project

## Setup on Windows PowerShell

```powershell
cd "C:\Users\BM MOBILE\Desktop\data-analyst\dataset_project"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If the activation command says the file does not exist, create the environment first with the setup commands above. You can always run the project without activation by using the environment's Python directly:

```powershell
.\.venv\Scripts\python.exe main.py --data data/raw --output reports
```

Place input files in `data/raw`.

## Setup on Linux / macOS

```bash
cd "/path/to/dataset_project"
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

You can also run the project without activation by using the environment's Python directly:

```bash
venv/bin/python main.py --data data/raw --output reports
```

## Run the full assessment

`compileall` only checks Python syntax. It does not inspect or analyze data.

Place the original dataset in `data/raw`, then run the orchestrator:

```powershell
python main.py --data data/raw --output reports
```

This runs the applicable inventory, tabular quality, statistics, duplicate, and outlier checks. It preserves the raw data and writes:

- `reports/assessment.json` for machine-readable results
- `reports/dataset_report.md` for a readable summary
- `reports/dataset_report.html` for the visual dashboard
- `reports/assets/report.css` and `reports/assets/report.js` for the dashboard styling and interactions

Open the visual report after the command finishes:

```powershell
Start-Process .\reports\dataset_report.html
```

If the target column is known, pass it explicitly. This enables label auditing and the baseline model; the tool never guesses the target:

```powershell
python main.py --data data/raw --target target_column --output reports
```

For a single input file:

```powershell
python main.py --data data/raw/my_dataset.csv --output reports
```

## Clean & optimize the data from the HTML report

The visual report (`reports/dataset_report.html`) includes a **Clean & Optimize Data** button. It cleans **every modality it finds** — tabular tables, images, audio, video, and text — and writes a training-ready copy of each plus a new "fixed" report. The original raw files are never modified.

The button calls a small local server that uses only the Python standard library and Pillow (no extra dependency), so start it first:

```powershell
python main.py --data data/raw --output reports --serve
```

Then open the URL it prints (for example `http://127.0.0.1:8000/reports/dataset_report.html`) and click **Clean & Optimize Data**. The panel lets you choose which fixes to apply, optionally name the target column, and toggle media cleaning.

### What gets cleaned, per modality

| Modality | Extensions (auto-detected) | Cleaning applied |
| --- | --- | --- |
| Tabular | `.csv` `.tsv` `.xlsx` `.xls` `.parquet` `.json` | drop duplicate & empty rows, drop empty columns, fix missing values (median/mode), trim whitespace, fix column data types, optional categorical encoding |
| Image | every format Pillow can decode (`.png` `.jpg` `.jpeg` `.gif` `.bmp` `.webp` `.tiff` `.avif` `.ico` `.jp2` …) | detect corrupted files, remove byte-identical duplicates, normalize to RGB PNG (optional max side) |
| Audio | `.wav` `.mp3` `.flac` `.ogg` `.m4a` | validate decodability (WAV frame check + header check), remove corrupted and duplicate files |
| Video | `.mp4` `.avi` `.mov` `.mkv` `.webm` | validate container header, remove corrupted and duplicate files |
| Text | `.txt` `.md` `.jsonl` `.xml` `.html` `.rst` `.log` `.yaml` | strip HTML markup and whitespace, remove duplicates |

A folder can contain any mix of these modalities; each is cleaned into its own subfolder. The exact list of decodable image formats is printed in the fixed report, since it depends on your Pillow build.

### Outputs

- `data/processed/<name>_cleaned.csv` — cleaned tabular data (one file per table)
- `data/processed/images/`, `data/processed/audio/`, `data/processed/video/`, `data/processed/text/` — cleaned media
- `reports/dataset_report_fixed.html` — before/after report for every modality
- `reports/assessment_fixed.json` — machine-readable summary

### Run it without the browser

```powershell
python main.py --data data/raw --output reports --clean
python main.py --data data/raw --output reports --target mpg --clean --encode
```

`--data` may point at a folder (mixed modalities) or a single file. If the report is opened directly as a `file://` page (without `--serve`), clicking the button explains how to start the server.

## Run an individual module

Inspect the raw-data folder:

```powershell
python -c "from analysis.inspect_dataset import DatasetInspector; print(DatasetInspector('data/raw').create_inventory())"
```

Run a syntax check for the whole project:

```powershell
python -m compileall -q .
```

The orchestrator currently handles the supplied analysis modules plus the clean-and-optimize pipeline for tabular, image, audio, video, and text data. The pasted specification also mentions dedicated visualization, normalization, database/API ingestion, leakage checks, and advanced model training; those still need dedicated implementations before those capabilities can be claimed.
