
## Prerequisites

*   Python 3.7+
*   A Google AI API Key (if using Google's Generative AI models)

## Setup

1.  **Clone the repository (if applicable) or download the scripts.**

2.  **Create a Python virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install the required Python libraries:**
    ```bash
    pip install pandas rapidfuzz tqdm PyYAML google-generativeai
    ```

4.  **Prepare your input data:**
    *   Have your source and target company lists ready as CSV files.
    *   Ensure these files have header rows and clearly defined columns for company IDs and names.

5.  **Create output directory (optional but recommended):**
    ```bash
    mkdir data
    ```

## Configuration

All operational parameters are controlled via the `config.yaml` file. Create this file in the root directory of the project.

```yaml
# Configuration for dynamic_company_matching.py
source: "path/to/your/source_companies.csv"  # CSV file with companies to match
target: "path/to/your/target_companies.csv"  # CSV file with companies to match against
source_id: "SourceCompanyID"                  # Column name for unique ID in source_df
source_name: "SourceCompanyName|AlternateName" # Column name(s) for company name in source_df (use | for fallbacks)
target_id: "TargetCompanyName"                # Column name in target_df containing the company names to build the match list from

api_key: "YOUR_GOOGLE_AI_API_KEY"          # Your Google AI API key
match_threshold: 50                        # Fuzzy match score cutoff (0-100)
model: "gemini-2.0-flash"                  # AI model to use (e.g., gemini-1.0-pro, gemini-1.5-flash)

fuzzy_output: "data/fuzzy_matches.csv"     # Path to save fuzzy matching results
match_status: "data/match_status.csv"      # Path to save AI matching status and results

run_fuzzy: true                            # Set to true to run the fuzzy matching stage
run_ai: true                               # Set to true to run the AI matching stage

# Batch sizes for AI matching. Tries larger batches first, then smaller for retries.
batch_sizes:
  - 10
  - 5
  - 1

# List of common terms/suffixes to remove/ignore during name cleaning for fuzzy matching
common_terms_list:
  - pty
  - ltd
  - limited
  # ... (add more as needed, see example in provided config.yaml)

# Prompt for the AI model. {batch_matching_tasks} will be replaced with the JSON tasks.
ai_prompt: |
  You are a highly skilled data matching assistant. Your primary function is to process a list of company matching tasks. For each task, you must determine whether the given `input_name` refers to the same entity as any company in its corresponding `company_list`. You need to consider variations like abbreviations, trading names, legal suffixes (e.g., Ltd, Inc, PLC), missing/extra words, and minor formatting differences.

  You will be provided with a list of tasks, where each task contains:
  - An `input_name` (the company name to be matched).
  - A `company_list` (a list of potential company names to match against).
  For each task you process, you must return the following information:
  - Input Name Processed: The original `input_name` for that task.
  - Match: The best matching company name from the `company_list`. If no reasonable match is found, return "No match."
  - Confidence: A confidence level for the match (High / Medium / Low). Indicates how confident you are in your answer.
  - Explanation: A brief explanation for your decision, highlighting why it's a match (e.g., abbreviation, strong keyword overlap, common trading name) or why it's not.

  Process all tasks provided in the input.

  Here are the company matching tasks:
  {batch_matching_tasks}

  # Example Input and Output format (ensure your AI model can follow this if you change the prompt)
  # ... (refer to the example in the originally provided config.yaml for full example format)

  Please return only the JSON array, with no markdown formatting, no triple backticks, and no extra commentary. Do not wrap the output in ```json or any other code block.

```

**Key Configuration Options:**

*   `source`, `target`: Paths to your input CSV files.
*   `source_id`, `source_name`, `target_id`: Specify the relevant column names from your CSVs. `source_name` can accept multiple pipe-separated column names as fallbacks.
*   `api_key`: **Crucial for AI matching.** Obtain this from your Google AI Studio or Google Cloud Console.
*   `match_threshold`: The minimum similarity score (0-100) for a fuzzy match to be considered a candidate.
*   `model`: The specific Generative AI model you want to use.
*   `fuzzy_output`: Where the intermediate fuzzy match results will be saved. The `ai_matchings.py` script uses this as input.
*   `match_status`: Tracks the progress and final results of the AI matching stage. This allows the AI process to be resumed.
*   `run_fuzzy`, `run_ai`: Boolean flags to control whether to execute the fuzzy matching and/or AI matching stages.
*   `batch_sizes`: The AI matching process iterates through these batch sizes. It attempts to match records using larger batches first. Unmatched records or those that failed in a larger batch can be retried with smaller batch sizes. This can help optimize API calls and costs.
*   `common_terms_list`: A list of words (like "Ltd", "Inc", "Pty", "Services") that will be removed from names before fuzzy matching to improve accuracy by focusing on more distinctive parts of the names.
*   `ai_prompt`: The detailed instructions given to the AI model. You can customize this prompt to fine-tune the AI's behavior, the expected output format, or the matching criteria.

## How to Run

1.  **Ensure your `config.yaml` is correctly set up**, especially file paths and your `api_key`.
2.  **Open your terminal or command prompt**, navigate to the project's root directory.
3.  **Activate your virtual environment** (if you created one).
4.  **Execute the main script:**
    ```bash
    python dynamic_company_matching.py --config config.yaml
    ```
    If `config.yaml` is in the same directory as the script, you can also run:
    ```bash
    python dynamic_company_matching.py
    ```

**Execution Flow:**

*   If `run_fuzzy` is `true`:
    *   The `fuzzy.py` script will process your `source` and `target` files.
    *   It will generate a `fuzzy_matches.csv` (or the path specified in `fuzzy_output`) containing source company IDs, original names, and a comma-separated list of potential matches from the target file.
    *   **Important:** If `fuzzy_output` file already exists, the fuzzy matching step will be aborted by `dynamic_company_matching.py` to prevent accidental overwriting. Delete or rename the existing file if you intend to re-run fuzzy matching from scratch.
*   If `run_ai` is `true`:
    *   The `ai_matchings.py` script will read the `fuzzy_matches.csv`.
    *   It will also read or create the `match_status.csv` to track progress and allow resumption.
    *   It will send batches of company names and their fuzzy-matched candidates to the configured AI model using the `ai_prompt`.
    *   Results (best match, confidence, explanation) will be saved in `match_status.csv`.

## Output Files

*   **`data/fuzzy_matches.csv` (or configured `fuzzy_output` path):**
    *   Columns: `id`, `name`, `matches`
    *   Contains the initial set of candidate matches generated by the fuzzy matching algorithm.
*   **`data/match_status.csv` (or configured `match_status` path):**
    *   Columns: `id`, `name`, `status`, `last_batch_size`, `ai_match`, `ai_confidence`, `ai_explanation`
    *   This is the final output of the AI matching stage.
        *   `status`: `True` if a conclusive match was made by the AI (or if AI determined "No match"), `False` if an error occurred or if it's pending for a smaller batch retry.
        *   `ai_match`: The company name chosen by the AI, or "No match".
        *   `ai_confidence`: Confidence level (e.g., High, Medium, Low).
        *   `ai_explanation`: The AI's reasoning for its decision.

## Customization

*   **Fuzzy Matching Logic (`fuzzy.py`):** You can adjust the `scorer` (e.g., `fuzz.WRatio`, `fuzz.partial_ratio`) used in `rapidfuzz.process.extract` or the `_clean_company_name` logic for different preprocessing needs.
*   **AI Prompt (`config.yaml`):** The `ai_prompt` is critical. Tailor it to guide the AI effectively. Ensure the example input/output format within the prompt matches what your chosen AI model performs best with and what the `ai_matchings.py` script expects when parsing the JSON response.
*   **AI Model (`config.yaml`):** Experiment with different Generative AI models available through the Google AI API to find the best balance of accuracy, speed, and cost for your needs.
