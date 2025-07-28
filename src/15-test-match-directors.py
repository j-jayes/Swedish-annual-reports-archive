import sys
import os
from director_matcher import DirectorMatcher

# Ensure output directory exists
output_dir = "data/company_director_info"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
    print(f"Created output directory: {output_dir}")

# Set paths
education_file = "data/directors_education_data_deduplicated.xlsx"
asea_json = "output_results/ASEA_long_serving_members.json"

# Test with a single file first
print(f"Testing matching using {asea_json} as input")
matcher = DirectorMatcher(education_file, output_dir)

# Test matching with a single file - limit to top 3 matches per director
matched_directors = matcher.match_directors(asea_json, threshold=70, max_matches_per_director=3)

# Save the results
if matched_directors:
    output_file = os.path.join(output_dir, "ASEA_director_matches.json")
    import json
    
    # Create a custom JSON encoder to handle non-serializable objects
    class CustomJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            import pandas as pd
            from datetime import datetime
            
            if isinstance(obj, (datetime, pd.Timestamp)):
                return str(obj)
            elif pd.isna(obj):
                return None
            return super().default(obj)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(matched_directors, f, indent=2, ensure_ascii=False, cls=CustomJSONEncoder)
    print(f"Saved {len(matched_directors)} matches to {output_file}")
    
    # Print some sample matches
    print("\nSample matches:")
    for i, match in enumerate(matched_directors[:3]):
        print(f"\nMatch {i+1}:")
        print(f"  Board Member: {match.get('name', '')}")
        print(f"  Tenure: {match.get('first_year', '')} - {match.get('last_year', '')} ({match.get('tenure', '')} years)")
        
        education_match = match.get('education_match')
        if education_match:
            print(f"  Matched with: {education_match.get('education_name', '')}")
            print(f"  Match Score: {education_match.get('match_score', '')}")
            print(f"  Birth: {education_match.get('birth_date', '')} (Decade: {education_match.get('birth_decade', '')})")
            
            # Safely print education info
            education_info = education_match.get('education', '')
            if education_info:
                if isinstance(education_info, str) and len(education_info) > 100:
                    print(f"  Education: {education_info[:100]}...")
                else:
                    print(f"  Education: {education_info}")
        else:
            print("  No education match found")
else:
    print("No matches found!")

print("\nTest complete!")