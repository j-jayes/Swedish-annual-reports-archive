import os
import sys
from director_matcher import DirectorMatcher

def main():
    # Configure paths
    output_dir = "data/company_director_info_all"
    input_dir = "output_results"  # Directory containing the company_name_long_serving_members.json files
    # education_file = "data/directors_education_data_deduplicated.xlsx"
    education_file = "data/all_education_data_deduplicated.xlsx"

    
    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")
    
    print(f"\nDirector Education Matcher")
    print(f"=========================")
    print(f"Education data: {education_file}")
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    
    # Create the matcher
    try:
        matcher = DirectorMatcher(education_file, output_dir)
    except Exception as e:
        print(f"Error initializing matcher: {e}")
        sys.exit(1)
    
    # Process all files and get matches
    try:
        # Use a lower matching threshold (70)
        matches = matcher.process_all_files(input_dir, threshold=70)
    except Exception as e:
        print(f"Error processing files: {e}")
        sys.exit(1)
    
    # Save consolidated matches
    try:
        consolidated_file = matcher.save_all_matches(matches)
    except Exception as e:
        print(f"Error saving consolidated matches: {e}")
        sys.exit(1)
    
    print(f"\nMatching complete! All outputs saved to {output_dir}")
    if consolidated_file:
        print(f"Consolidated matches saved to {consolidated_file}")

if __name__ == "__main__":
    main()