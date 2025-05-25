# Dynamic Company Matching

A tool that performs fuzzy matching and AI-based entity matching between two CSV files containing company names.

## Requirements

- Python 3.6+
- Required Python packages:
  ```
  pandas
  rapidfuzz
  tqdm
  google-generativeai
  ```

Install dependencies with:
```
pip install pandas rapidfuzz tqdm google-generativeai
```

## Features

- Fuzzy matching to find potential matches between company names
- AI-based verification using Google's Gemini API
- Support for fallback columns using pipe notation (col1|col2|col3)
- Batch processing with resume capability
- Progress tracking to handle large datasets
- Configurable matching parameters

## Usage

### Basic Example

```bash
python dynamic_company_matching.py \
  --source source_data.csv \
  --target target_data.csv \
  --source-id "Registration Number" \
  --source-name "Trading Name|Agent|Name" \
  --target-name "Account Name" \
  --api-key "YOUR_GEMINI_API_KEY"
```

### Command Line Arguments

| Argument | Description |
|----------|-------------|
| `--source` | Path to source CSV file |
| `--target` | Path to target CSV file |
| `--source-id` | Column name in source file to use as ID |
| `--source-name` | Column name(s) in source file for company names<br>Use pipe '|' to separate fallback columns |
| `--target-name` | Column name in target file for company names |
| `--api-key` | Google AI API key for Gemini model |
| `--target-filter` | Optional column:value filter for target file<br>Example: 'Referral Partner Type:Accountant\|Bookkeeper' |
| `--match-threshold` | Fuzzy match threshold (default: 50) |
| `--batch-size` | AI batch size (default: 10) |
| `--model` | Google AI model to use |
| `--fuzzy-output` | Output file for fuzzy matches |
| `--ai-output` | Output file for AI matches |
| `--only-fuzzy` | Only perform fuzzy matching, skip AI matching |
| `--resume-ai` | Resume AI matching from previously saved fuzzy matches |

## Using Fallback Columns

The script supports using multiple columns in the source file with a fallback mechanism. For example, if you specify:

```
--source-name "Trading Name|Agent|Name"
```

The script will:
1. First try to use "Trading Name"
2. If it's empty/NA, try "Agent"
3. If both are empty/NA, try "Name"

## Process

1. **Fuzzy Matching**: Identifies potential matches between source and target companies using fuzzy string matching
2. **AI Matching**: Uses Google's Gemini model to verify fuzzy matches with contextual understanding
3. **Results**: Saves both fuzzy matches and AI-verified matches to CSV files

## Examples

### Run Only Fuzzy Matching

```bash
python dynamic_company_matching.py \
  --source tpb_register.csv \
  --target salesforce_report.csv \
  --source-id "Registration Number" \
  --source-name "Trading Name (Agent) (Organisation)|Trading Name (Agent) (Individual)|Agent" \
  --target-name "Account Name" \
  --api-key "YOUR_API_KEY" \
  --only-fuzzy
```

### Resume AI Matching

```bash
python dynamic_company_matching.py \
  --source tpb_register.csv \
  --target salesforce_report.csv \
  --source-id "Registration Number" \
  --source-name "Trading Name (Agent) (Organisation)|Trading Name (Agent) (Individual)|Agent" \
  --target-name "Account Name" \
  --api-key "YOUR_API_KEY" \
  --resume-ai
```

## Output Files

- `result_fuzzy_matches.csv`: Results from fuzzy matching
- `ai_matching_results.csv`: Final AI-verified matching results
- `processed_ids.csv`: IDs that have been processed (to resume later)
- `ai_failed_batches.csv`: Records of any failed AI processing batches # dynamic-company-matching
