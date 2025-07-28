import os
import json
import pandas as pd
import numpy as np
from fuzzywuzzy import fuzz, process
import glob
from datetime import datetime
import re

class DirectorMatcher:
    def __init__(self, education_file, output_dir="data/company_director_info"):
        """
        Initialize the DirectorMatcher with the education data file
        
        Args:
            education_file (str): Path to the Excel/CSV file with director education data
            output_dir (str): Directory to save the output matching files
        """
        self.output_dir = output_dir
        self.education_data = None
        self.load_education_data(education_file)
        
        # Ensure output directory exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}")
    
    def load_education_data(self, education_file):
        """
        Load the directors' education data from Excel or CSV
        
        Args:
            education_file (str): Path to the file with director education data
        
        Returns:
            self: Returns self for method chaining
        """
        try:
            # Determine file type from extension
            file_extension = os.path.splitext(education_file)[1].lower()
            
            if file_extension == '.xlsx' or file_extension == '.xls':
                self.education_data = pd.read_excel(education_file)
            elif file_extension == '.csv':
                self.education_data = pd.read_csv(education_file)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}. Please use Excel or CSV.")
            
            # Ensure required columns exist
            required_columns = ['first_name', 'last_name']
            missing_columns = [col for col in required_columns if col not in self.education_data.columns]
            
            if missing_columns:
                # Try to adapt if we have 'name' column instead
                if 'name' in self.education_data.columns and ('first_name' in missing_columns or 'last_name' in missing_columns):
                    print("Splitting 'name' column into first and last name...")
                    self.education_data[['first_name', 'last_name']] = self.education_data['name'].str.split(' ', n=1, expand=True)
                else:
                    raise ValueError(f"Missing required columns: {missing_columns}")
            
            # Clean the data - convert to strings and strip whitespace
            for col in ['first_name', 'last_name']:
                self.education_data[col] = self.education_data[col].astype(str).str.strip()
            
            # Add a combined name column for easier matching if it doesn't exist
            if 'full_name' not in self.education_data.columns:
                self.education_data['full_name'] = self.education_data['last_name'] + ', ' + self.education_data['first_name']
            
            # Convert datetime columns to strings to ensure JSON serialization
            for col in self.education_data.columns:
                if pd.api.types.is_datetime64_any_dtype(self.education_data[col]):
                    print(f"Converting datetime column '{col}' to string for JSON compatibility")
                    self.education_data[col] = self.education_data[col].astype(str)
            
            print(f"Loaded {len(self.education_data)} director education records")
            return self
            
        except Exception as e:
            print(f"Error loading education data: {e}")
            raise
    
    def find_json_files(self, directory, pattern="*_long_serving_members.json"):
        """
        Find all JSON files matching a pattern in a directory
        
        Args:
            directory (str): Directory to search
            pattern (str): Glob pattern to match filenames
            
        Returns:
            list: List of file paths
        """
        return glob.glob(os.path.join(directory, pattern))
    
    def normalize_name(self, name):
        """
        Normalize a name string for better matching
        
        Args:
            name (str): Name string to normalize
            
        Returns:
            str: Normalized name
        """
        if pd.isna(name) or name is None:
            return ""
        
        # Convert to string if needed
        name = str(name).strip()
        
        # Convert to lowercase
        name = name.lower()
        
        # Remove common titles and suffixes
        for title in ['dr.', 'dr', 'prof.', 'prof', 'jr.', 'jr', 'sr.', 'sr']:
            name = name.replace(f" {title}", "").replace(f"{title} ", "")
        
        # Remove punctuation (except for hyphenated names)
        name = ''.join(c for c in name if c.isalnum() or c in [' ', '-'])
        
        return name.strip()
    
    def match_directors(self, json_file, threshold=75, max_matches_per_director=5):
        """
        Match directors from a JSON file with education data
        
        Args:
            json_file (str): Path to the JSON file with long-serving board members
            threshold (int): Threshold for fuzzy matching (0-100)
            max_matches_per_director (int): Maximum number of education matches to keep per director
            
        Returns:
            dict: Dictionary with matched directors
        """
        try:
            # Load the JSON file
            with open(json_file, 'r', encoding='utf-8') as f:
                board_members = json.load(f)
            
            company_name = os.path.basename(json_file).split('_')[0]
            print(f"\nProcessing {len(board_members)} board members for {company_name}")
            
            # Create a list to hold the matched results
            matched_results = []
            
            # Prepare education data for matching
            education_names = self.education_data['full_name'].tolist()
            education_first_names = self.education_data['first_name'].tolist()
            education_last_names = self.education_data['last_name'].tolist()
            
            # Process each board member
            for member in board_members:
                member_name = member.get('name', '').strip()
                member_surname = member.get('surname', '').strip()
                member_first_name = member.get('first_name', '').strip()
                member_initials = member.get('initials', '').strip()
                
                # Skip if no valid name information
                if not member_surname and not member_name:
                    print(f"Skipping member with no name information: {member}")
                    continue
                
                # Try different matching approaches
                matches = []
                
                # Approach 1: Match on full name
                if member_name:
                    normalized_member_name = self.normalize_name(member_name)
                    
                    # Full name matching
                    for idx, edu_name in enumerate(education_names):
                        normalized_edu_name = self.normalize_name(edu_name)
                        score = fuzz.token_set_ratio(normalized_member_name, normalized_edu_name)
                        
                        if score >= threshold:
                            matches.append({
                                'education_index': idx,
                                'score': score,
                                'match_type': 'full_name'
                            })
                
                # Approach 2: Match on surname + first name separately
                if member_surname:
                    normalized_surname = self.normalize_name(member_surname)
                    normalized_first_name = self.normalize_name(member_first_name)
                    
                    for idx, (edu_last, edu_first) in enumerate(zip(education_last_names, education_first_names)):
                        normalized_edu_last = self.normalize_name(edu_last)
                        normalized_edu_first = self.normalize_name(edu_first)
                        
                        # Higher weight for surname
                        surname_score = fuzz.token_set_ratio(normalized_surname, normalized_edu_last)
                        
                        # Only check first name if we have both
                        if normalized_first_name and normalized_edu_first:
                            first_name_score = fuzz.token_set_ratio(normalized_first_name, normalized_edu_first)
                            # Combined score with more weight on surname
                            combined_score = (surname_score * 0.7) + (first_name_score * 0.3)
                        else:
                            # If we only have initials, be more lenient
                            if member_initials and normalized_edu_first:
                                if normalized_edu_first.startswith(member_initials.lower()):
                                    combined_score = surname_score * 0.9  # Boost score if initials match
                                else:
                                    combined_score = surname_score * 0.6  # Reduce score if initials don't match
                            else:
                                combined_score = surname_score * 0.8  # Only surname match
                        
                        if combined_score >= threshold:
                            matches.append({
                                'education_index': idx,
                                'score': combined_score,
                                'match_type': 'surname_first_name'
                            })
                
                # Sort matches by score in descending order
                matches.sort(key=lambda x: x['score'], reverse=True)
                
                # Limit the number of matches per director to avoid overly large files
                # Only keep the top matches by score
                matches = matches[:max_matches_per_director]
                
                # For each match, create a result entry
                for match in matches:
                    edu_idx = match['education_index']
                    education_entry = self.education_data.iloc[edu_idx].to_dict()
                    
                    # Create a copy of the member data
                    result_entry = member.copy()
                    
                    # Convert any non-serializable objects to strings
                    def ensure_serializable(obj):
                        if isinstance(obj, (datetime, pd.Timestamp)):
                            return str(obj)
                        elif isinstance(obj, (list, tuple)):
                            return [ensure_serializable(item) for item in obj]
                        elif isinstance(obj, dict):
                            return {key: ensure_serializable(value) for key, value in obj.items()}
                        elif pd.isna(obj):
                            return None
                        return obj
                    
                    # Add education information with serializable values
                    result_entry['education_match'] = {
                        'match_score': float(match['score']),  # Ensure it's a float
                        'match_type': match['match_type'],
                        'education_id': str(education_entry.get('id', '')),
                        'education_name': str(education_entry.get('name', '')),
                        'education_first_name': str(education_entry.get('first_name', '')),
                        'education_last_name': str(education_entry.get('last_name', '')),
                        'birth_date': str(education_entry.get('birth_date', '')),
                        'birth_decade': ensure_serializable(education_entry.get('birth_decade', '')),
                        'occupation': str(education_entry.get('occupation', '')),
                        'has_technical_education': bool(education_entry.get('has_technical_education', False)),
                        'has_business_education': bool(education_entry.get('has_business_education', False)),
                        'has_other_higher_education': bool(education_entry.get('has_other_higher_education', False)),
                        'non_swedish_experience_count': int(education_entry.get('non_swedish_experience_count', 0)),
                        'usa_experience_count': int(education_entry.get('usa_experience_count', 0)),
                        'has_usa_experience': bool(education_entry.get('has_usa_experience', False)),
                        'has_non_swedish_experience': bool(education_entry.get('has_non_swedish_experience', False)),
                        'education': ensure_serializable(education_entry.get('education', '')),
                    }
                    
                    matched_results.append(result_entry)
                
                # If no matches found, add the member with no education match
                if not matches:
                    result_entry = member.copy()
                    result_entry['education_match'] = None
                    matched_results.append(result_entry)
            
            print(f"Found a total of {len(matched_results)} matches for {company_name}")
            return matched_results
            
        except Exception as e:
            print(f"Error matching directors in {json_file}: {e}")
            return []
    
    def process_all_files(self, input_dir, pattern="*_long_serving_members.json", threshold=75, max_matches_per_director=3):
        """
        Process all JSON files in a directory and match directors
        
        Args:
            input_dir (str): Directory containing JSON files
            pattern (str): Glob pattern to match filenames
            threshold (int): Threshold for fuzzy matching (0-100)
            max_matches_per_director (int): Maximum number of education matches to keep per director
            
        Returns:
            dict: Dictionary with company_name -> matched_directors mapping
        """
        json_files = self.find_json_files(input_dir, pattern)
        
        if not json_files:
            print(f"No files found matching pattern {pattern} in {input_dir}")
            return {}
        
        print(f"Found {len(json_files)} JSON files to process")
        results = {}
        
        for json_file in json_files:
            company_name = os.path.basename(json_file).split('_')[0]
            matched_directors = self.match_directors(json_file, threshold)
            
            if matched_directors:
                results[company_name] = matched_directors
                
                # Save to individual company file
                output_file = os.path.join(self.output_dir, f"{company_name}_director_matches.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(matched_directors, f, indent=2, ensure_ascii=False)
                print(f"Saved matches for {company_name} to {output_file}")
        
        return results
    
    def save_all_matches(self, matches, output_file=None):
        """
        Save all matches to a consolidated JSON file
        
        Args:
            matches (dict): Dictionary with company_name -> matched_directors mapping
            output_file (str, optional): Path to save the consolidated file
            
        Returns:
            str: Path to the saved file
        """
        if not matches:
            print("No matches to save")
            return None
        
        # Flatten the matches into a single list with company information
        all_matches = []
        for company, directors in matches.items():
            for director in directors:
                # Add company info to each director
                director_with_company = director.copy()
                all_matches.append(director_with_company)
        
        # Generate file path if not provided
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(self.output_dir, f"all_director_matches_{timestamp}.json")
        
        # Create a custom JSON encoder to handle non-serializable objects
        class CustomJSONEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (datetime, pd.Timestamp)):
                    return str(obj)
                elif pd.isna(obj):
                    return None
                return super().default(obj)
        
        # Save to file with custom encoder
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_matches, f, indent=2, ensure_ascii=False, cls=CustomJSONEncoder)
            
            print(f"Saved {len(all_matches)} total matches to {output_file}")
            return output_file
            
        except TypeError as e:
            print(f"Error serializing to JSON: {e}")
            
            # Try to identify problematic records
            print("Attempting to diagnose serialization issues...")
            problematic_records = []
            
            for i, match in enumerate(all_matches):
                try:
                    # Test serialize each record
                    json.dumps(match, cls=CustomJSONEncoder)
                except TypeError as err:
                    print(f"Record {i} is not serializable: {err}")
                    problematic_records.append(i)
                    
                    # Try to find the problematic key
                    for key, value in match.items():
                        try:
                            json.dumps({key: value}, cls=CustomJSONEncoder)
                        except TypeError:
                            print(f"  - Problem in key: {key}, value type: {type(value)}")
            
            if problematic_records:
                print(f"Found {len(problematic_records)} problematic records. Attempting to save without them...")
                filtered_matches = [match for i, match in enumerate(all_matches) if i not in problematic_records]
                
                if filtered_matches:
                    fallback_file = os.path.join(self.output_dir, f"all_director_matches_filtered_{timestamp}.json")
                    with open(fallback_file, 'w', encoding='utf-8') as f:
                        json.dump(filtered_matches, f, indent=2, ensure_ascii=False, cls=CustomJSONEncoder)
                    print(f"Saved {len(filtered_matches)} filtered matches to {fallback_file}")
                    return fallback_file
            
            return None

if __name__ == "__main__":
    # Input and output directories
    output_dir = "data/company_director_info"
    input_dir = "output_results"  # Directory containing the company_name_long_serving_members.json files
    education_file = "directors_education_data.xlsx"
    
    # Create the matcher
    matcher = DirectorMatcher(education_file, output_dir)
    
    # Process all files and get matches
    matches = matcher.process_all_files(input_dir, threshold=70)
    
    # Save consolidated matches
    consolidated_file = matcher.save_all_matches(matches)
    
    print(f"\nMatching complete! All outputs saved to {output_dir}")
    if consolidated_file:
        print(f"Consolidated matches saved to {consolidated_file}")