import os
import json
import time
import pandas as pd
from google import genai
from google.genai import types
from tqdm import tqdm

def perform_ai_matching(args:dict):
    """Perform AI matching on fuzzy matches"""
    print("Setting up Google AI client...")
    try:
        client = genai.Client(api_key=args['api_key'])
    except Exception as e:
        print(f"Failed to initialize Google AI client: {e}. Check API key and genai library installation.")
        return

    print(f"Loading fuzzy matches from {args['fuzzy_output']}")
    try:
        fuzzy_matches_df = pd.read_csv(args['fuzzy_output'], encoding='utf-8', dtype={'id': str})
    except FileNotFoundError:
        print(f"Error: Fuzzy matches file {args['fuzzy_output']} not found. Run fuzzy matching first or provide correct path.")
        return
    except UnicodeDecodeError:
        fuzzy_matches_df = pd.read_csv(args['fuzzy_output'], encoding='latin1', dtype={'id': str})
    except Exception as e:
        print(f"Error loading fuzzy_matches_df {args['fuzzy_output']}: {e}")
        return

    # Check if the fuzzy matches file has the required columns
    if 'id' not in fuzzy_matches_df.columns:
        print(f"Error: The fuzzy matches file {args['fuzzy_output']} must contain an 'id' column.")
        return
    if 'name' not in fuzzy_matches_df.columns:
        print(f"Error: The fuzzy matches file {args['fuzzy_output']} must contain a 'name' column.")
        return
    if 'matches' not in fuzzy_matches_df.columns:
        print(f"Error: The fuzzy matches file {args['fuzzy_output']} must contain a 'matches' column.")
        return

    match_status_columns = ['id', 'name', 'status', 'last_batch_size', 'ai_match', 'ai_confidence', 'ai_explanation']


    print(f"Loading matching status from {args['match_status']}")
    try:
        # Try to read the file
        match_status_df = pd.read_csv(args['match_status'], encoding='utf-8', dtype={'id': str, 'input_name': str, 'last_batch_size': 'Int64'})
        print(f"Found {args['match_status']}, resuming from where we left off.")
    except UnicodeDecodeError:
        match_status_df = pd.read_csv(args['match_status'], encoding='latin1', dtype={'id': str, 'input_name': str, 'last_batch_size': 'Int64'})
        print(f"Found {args['match_status']}, resuming from where we left off.")
    except FileNotFoundError: # Catch other potential pd.read_csv errors
        print(f"Error loading {args['match_status']}: {e}. Will attempt to create a new one based on fuzzy matches.")
        # Fallback: create from scratch as if file was not found
        match_status_df = pd.DataFrame([
            {'id': row['id'], 'name': row['name'], 'status': False, 'last_batch_size': pd.NA,
                'ai_match': pd.NA, 'ai_confidence': pd.NA, 'ai_explanation': pd.NA}
            for _, row in fuzzy_matches_df.iterrows()
        ], columns=match_status_columns)
        match_status_df['last_batch_size'] = match_status_df['last_batch_size'].astype('Int64') # Ensure correct dtype for pd.NA
        match_status_df.to_csv(args['match_status'], index=False, encoding='utf-8')
    except Exception as e:
        print(f"Error loading {args['match_status']}: {e}")
        return

    # Filter out fuzzy rows whose ids have status True in match_status_df
    finished_ids = set(match_status_df.loc[match_status_df['status'] == True, 'id'].astype(str))
    fuzzy_matches = fuzzy_matches_df[~fuzzy_matches_df['id'].astype(str).isin(finished_ids)]  # Filter out fuzzy rows whose ids have status True in match_status_df
    
    for batch_sz in args['batch_sizes']:
        # Get IDs that haven't been processed or had smaller previous batches
        eligible_ids = match_status_df[
            (match_status_df['status'] == False) &
            (match_status_df['last_batch_size'].isna() | (match_status_df['last_batch_size'] > batch_sz))
        ]['id'].astype(str).tolist()
        
        # Filter fuzzy matches to only eligible IDs for this batch size
        batch_fuzzy_matches = fuzzy_matches[fuzzy_matches['id'].astype(str).isin(eligible_ids)]
        
        if not batch_fuzzy_matches.empty:
            print(f"Processing batch of size {batch_sz} for {len(batch_fuzzy_matches)} rows")
            perform_batch_ai_matching(args, batch_sz, batch_fuzzy_matches, match_status_df, client)
    
def _normalize_name(name:str):
    """Normalize name by removing extra whitespaces"""
    if pd.isna(name):
        return ""
    words = name.split()
    return ' '.join(words)

def _update_match_status(match_status_df, row_id:str, status:bool, last_batch_size:int, ai_match:str, ai_confidence:str, ai_explanation:str):
    """Update match status for a given id"""
    match_status_df.loc[match_status_df['id'] == row_id, 'status'] = status
    match_status_df.loc[match_status_df['id'] == row_id, 'last_batch_size'] = last_batch_size
    match_status_df.loc[match_status_df['id'] == row_id, 'ai_match'] = ai_match
    match_status_df.loc[match_status_df['id'] == row_id, 'ai_confidence'] = ai_confidence
    match_status_df.loc[match_status_df['id'] == row_id, 'ai_explanation'] = ai_explanation
    

def perform_batch_ai_matching(
    args,
    batch_sz:int,
    fuzzy_matches:pd.DataFrame,
    match_status_df:pd.DataFrame,
    client:genai.Client,
    ):
   
    
    total_rows = len(fuzzy_matches)
    
    for i in range(0, total_rows, batch_sz):
        batch = fuzzy_matches.iloc[i:i+batch_sz]
        matching_tasks = []
        ids_in_batch = [] # Store actual IDs being sent in this batch
        
        for _, row in batch.iterrows():
            task = {
                "input_name": row['name'],
                "company_list": json.loads(row['matches']) if isinstance(row['matches'], str) else []
            }
            matching_tasks.append(task)
            ids_in_batch.append(row['id'])
        
        content = args['ai_prompt'].format(batch_matching_tasks=json.dumps(matching_tasks, indent=2))

        print(f"Calling AI API for sample {i} to {i+batch_sz}")
        try:
            response = client.models.generate_content(
                model=args['model'],
                contents=content,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type='application/json',
                    top_p=1.0,
                    top_k=0
                ),
            )
            time.sleep(6) # Rate limiting
        except Exception as e:
            print(f"Error calling AI API for sample {i} to {i+batch_sz}: {str(e)}")
            for row_id in ids_in_batch: 
                row = match_status_df[match_status_df['id'] == row_id]
                if not row.empty:
                    _update_match_status(match_status_df, row_id, False, batch_sz, pd.NA, pd.NA,pd.NA)
            match_status_df.to_csv(args['match_status'], index=False, encoding='utf-8')
            continue
        try:
            # Parse the response text as JSON
            results = json.loads(str(response.text))

            # record all the ids that have been matched
            matched_ids = set()
            # For each result in the batch
            for result in results:
                # Find the corresponding row in the original data
                normalized_input = _normalize_name(result['Input Name Processed'])
                # Find the best match in the batch
                found_original_row_info = None
                for _, row in batch.iterrows():
                    if _normalize_name(row['name']) == normalized_input:
                        found_original_row_info = row
                        matched_ids.add(row['id'])
                        break
                if found_original_row_info is not None:
                    ai_match = result['Match']
                    ai_confidence = result['Confidence']
                    ai_explanation = result['Explanation']
                    _update_match_status(match_status_df, found_original_row_info['id'], True, batch_sz, ai_match, ai_confidence, ai_explanation)
                else:
                    print(f"Warning: AI returned 'Input Name Processed' ('{result['Input Name Processed']}') which did not match any input name in this batch. Skipping this result.")
            
            # Update all the ids that have not been matched into match_status_df
            for _, row in batch.iterrows():
                if row['id'] not in matched_ids:
                    _update_match_status(match_status_df, row['id'], False, batch_sz, pd.NA, pd.NA, pd.NA)
            
            match_status_df.to_csv(args['match_status'], index=False, encoding='utf-8')
        except Exception as e:
            print(f"Error processing batch {i}: {str(e)}")
            for row_id in ids_in_batch: 
                row = match_status_df[match_status_df['id'] == row_id]
                if not row.empty:
                    _update_match_status(match_status_df, row_id, False,batch_sz, pd.NA, pd.NA,pd.NA)
            match_status_df.to_csv(args['match_status'], index=False, encoding='utf-8')
            continue 
    
    print(f"Detailed processing status saved to {args['match_status']}")
