#!/usr/bin/env python3
# Sample config.yaml structure:
# ---
# source: "tpb_companies.csv"
# target: "salesforce_companies.csv"
# source_id: "ID"
# source_name: "Trading Name|Agent|Name"
# target_id: "Company Name"
# api_key: "YOUR_GOOGLE_API_KEY"
# match_threshold: 50
# batch_size: 10
# model: "gemini-2.5-flash-preview-05-20"
# fuzzy_output: "result_fuzzy_matches.csv"
# ai_output: "ai_matching_results.csv"
# match_status: "match_status.csv"
# only_fuzzy: false
# resume_ai: false
# batch_sizes: [1, 5, 10]

from fuzzy import perform_fuzzy_matching
from ai_matchings import perform_ai_matching
import yaml
import os
import argparse

def load_config(config_path="config.yaml"):
    """Load configuration from a YAML file."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    # Set defaults if not present
    config.setdefault('match_threshold', 50)
    config.setdefault('model', "gemini-2.0-flash")
    config.setdefault('fuzzy_output', "fuzzy_output.csv")
    config.setdefault('match_status', "match_status.csv")
    config.setdefault('run_fuzzy', True)
    config.setdefault('run_ai', True)
    config.setdefault('batch_sizes', [10,5,1])
    config.setdefault('common_terms_pattern', [])
    config.setdefault('ai_prompt', "")
    return config



def main():
    """Main function to run the matching process"""
    parser = argparse.ArgumentParser(description="Run company matching with a specified config file.")
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to the config YAML file (default: config.yaml)')
    args = parser.parse_args()

    config = load_config(args.config)
    
    print("Starting company matching process")

    if config['run_fuzzy']:
        if os.path.exists(config['fuzzy_output']):
            print(f"Error: Fuzzy output file {config['fuzzy_output']} already exists. Aborting fuzzy matching.")
        else:
            print("Starting fuzzy matching...")
            perform_fuzzy_matching(config)
    if config['run_ai']:
        print("Starting AI matching...")
        perform_ai_matching(config)

    print("Company matching process finished.")

if __name__ == "__main__":
    main() 