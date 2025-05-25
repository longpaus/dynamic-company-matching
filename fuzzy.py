import pandas as pd
import os
from tqdm import tqdm
from rapidfuzz import process, fuzz
import re

def _find_matches(name:str, candidates:list, threshold:int=None):
    """Find fuzzy matches for a company name"""
    if pd.isna(name) or not name:
        return []
    
    matches = process.extract(
        str(name),
        candidates,
        scorer=fuzz.token_sort_ratio,
        score_cutoff=threshold,
        limit=None
    )
    
    return [(match[0], match[1]) for match in matches]

def _build_common_terms_pattern(common_terms_list):
    # Escape each term for regex, join with |, and wrap with word boundaries
    pattern = r'\\b(' + '|'.join(re.escape(term) for term in common_terms_list) + r')\\b'
    return pattern

def _clean_company_name(name:str, common_terms_pattern:str):
    """Clean company name by removing common terms and normalizing whitespace"""
    if pd.isna(name):
        return ""
    name = name.lower()
    # Remove common company suffixes and business terms
    name = re.sub(common_terms_pattern, '', name, flags=re.IGNORECASE)
    # Remove extra spaces
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

def _get_value_from_fallback_columns(row:pd.Series, column_names:str)->str:
    """Get value from fallback columns (col1|col2|col3)"""
    columns = column_names.split('|')
    for col in columns:
        col = col.strip()
        if col in row and not pd.isna(row[col]):
            return row[col]
    return None

def perform_fuzzy_matching(args:dict):
    """Perform fuzzy matching between source and target files"""
    print(f"Loading source file: {args['source']}")
    try:
        source_df = pd.read_csv(args['source'], encoding='utf-8')
    except UnicodeDecodeError:
        source_df = pd.read_csv(args['source'], encoding='latin1')
        
    print(f"Loading target file: {args['target']}")
    try:
        target_df = pd.read_csv(args['target'], encoding='utf-8')
    except UnicodeDecodeError:
        target_df = pd.read_csv(args['target'], encoding='latin1')
    
    common_terms_pattern = _build_common_terms_pattern(args['common_terms_pattern'])
    print(f"Source rows to process for fuzzy matching: {len(source_df)}")
    
    cleaned_to_originals_map = {}
    if args['target_id'] not in target_df.columns:
        print(f"Error: Target ID column '{args['target_id']}' (expected to contain names) not found in target file {args['target']}.")
        return
        
    for original_name in target_df[args['target_id']].dropna().unique():
        cleaned_name = _clean_company_name(original_name, common_terms_pattern)
        if cleaned_name:
            cleaned_to_originals_map.setdefault(cleaned_name, []).append(original_name)
    
    clean_target_names = list(cleaned_to_originals_map.keys())
    print(f"Unique cleaned target names for matching: {len(clean_target_names)}")
    
    CHUNK_SIZE = 1000
    results_list = []
    
    for idx, row in tqdm(source_df.iterrows(), total=len(source_df), desc="Processing source entries for fuzzy match"):
        source_name = _get_value_from_fallback_columns(row, args['source_name'])
        if not source_name:
            continue
            
        source_name_clean = _clean_company_name(source_name, common_terms_pattern)
        if not source_name_clean:
            continue
            
        clean_matches = _find_matches(source_name_clean, clean_target_names, threshold=args['match_threshold'])
        
        original_matches = []
        for cleaned_match, _ in clean_matches:
            original_matches.extend(cleaned_to_originals_map[cleaned_match])
        
        if original_matches:  # Only save if matches found
            new_row_data = {
                'id':row[args['source_id']],
                'name':source_name,
                'matches': ','.join(original_matches)
            }
            results_list.append(new_row_data)
        
        # save to file
        if (idx + 1) % CHUNK_SIZE == 0:
            if results_list:
                temp_df = pd.DataFrame(results_list)
                file_exists = os.path.exists(args['fuzzy_output'])
                temp_df.to_csv(
                    args['fuzzy_output'],
                    index=False,
                    encoding='utf-8',
                    mode='a' if file_exists else 'w',
                    header=not file_exists
                )
                print("Saved {} samples...".format(idx + 1))
                results_list = []
    
    # Final save for remaining entries
    if results_list:
        temp_df = pd.DataFrame(results_list)
        file_exists = os.path.exists(args['fuzzy_output'])
        temp_df.to_csv(
            args['fuzzy_output'],
            index=False,
            encoding='utf-8',
            mode='a' if file_exists else 'w',
            header=not file_exists
        )
        print("Saved final {} entries.".format(len(results_list)))
    
    print(f"Fuzzy matching complete. Results are in {args['fuzzy_output']}")
