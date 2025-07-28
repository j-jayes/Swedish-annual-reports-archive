import os
import json
import glob
from collections import Counter
from statistics import mode
import argparse

class DirectorSummarizer:
    def __init__(self, input_dir, output_dir, threshold=90):
        """
        Initialize the summarizer with input/output directories and matching threshold
        
        Args:
            input_dir (str): Directory containing matched director JSON files
            output_dir (str): Directory to save summary files
            threshold (int): Minimum match score threshold to consider (0-100)
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.threshold = threshold
        
        # Ensure output directory exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}")
    
    def find_match_files(self, pattern="*_director_matches.json"):
        """
        Find all director match JSON files
        
        Args:
            pattern (str): Glob pattern to match filenames
            
        Returns:
            list: List of file paths
        """
        return glob.glob(os.path.join(self.input_dir, pattern))
    
    def get_most_common_value(self, values, prefer_true=True):
        """
        Get the most common value from a list, with tiebreaker logic
        
        Args:
            values (list): List of values
            prefer_true (bool): If True and there's a tie with boolean values, return True
            
        Returns:
            The most common value
        """
        if not values:
            return None
            
        # Handle special case for booleans with ties
        if all(isinstance(v, bool) for v in values):
            true_count = sum(1 for v in values if v)
            false_count = len(values) - true_count
            
            if true_count == false_count:
                return True if prefer_true else False
        
        # For numeric values, if there's a tie, take the higher value
        if all(isinstance(v, (int, float)) for v in values):
            counts = Counter(values)
            most_common = counts.most_common()
            
            # Find the highest count
            max_count = most_common[0][1]
            
            # Get all values with that count
            ties = [val for val, count in most_common if count == max_count]
            
            if ties:
                return max(ties)
        
        # Default case: return mode (most common)
        try:
            return mode(values)
        except:
            # If mode fails (e.g., multiple modes), return the first value
            return values[0]
    
    def summarize_director(self, director_data, threshold):
        """
        Summarize matches for a single director
        
        Args:
            director_data (list): List of match records for a director
            threshold (float): Match score threshold
            
        Returns:
            dict: Summarized education data
        """
        # Filter matches by threshold
        qualified_matches = [
            match for match in director_data 
            if match.get('education_match') and 
               match['education_match'].get('match_score', 0) >= threshold
        ]
        
        # Basic director information - take from first record
        if not director_data:
            return None
            
        base_info = {
            'name': director_data[0]['name'],
            'company': director_data[0]['company'],
            'first_year': director_data[0]['first_year'],
            'last_year': director_data[0]['last_year'],
            'tenure': director_data[0]['tenure'],
            'positions': director_data[0]['positions'],
            'match_count': len(qualified_matches)
        }
        
        # If no qualified matches, return basic info only
        if not qualified_matches:
            return base_info
        
        # If only one qualified match, use its values directly
        if len(qualified_matches) == 1:
            match = qualified_matches[0]['education_match']
            education_info = {
                'has_technical_education': match.get('has_technical_education', False),
                'has_business_education': match.get('has_business_education', False),
                'has_other_higher_education': match.get('has_other_higher_education', False),
                'birth_decade': match.get('birth_decade')
            }
            
            # Add international experience if available
            if 'non_swedish_experience_count' in match:
                education_info['non_swedish_experience_count'] = match.get('non_swedish_experience_count', 0)
                education_info['has_non_swedish_experience'] = match.get('has_non_swedish_experience', False)
            
            if 'usa_experience_count' in match:
                education_info['usa_experience_count'] = match.get('usa_experience_count', 0)
                education_info['has_usa_experience'] = match.get('has_usa_experience', False)
                
            base_info.update(education_info)
            return base_info
        
        # Multiple matches - calculate mode/aggregated values
        tech_edu_values = [m['education_match'].get('has_technical_education', False) for m in qualified_matches]
        bus_edu_values = [m['education_match'].get('has_business_education', False) for m in qualified_matches]
        other_edu_values = [m['education_match'].get('has_other_higher_education', False) for m in qualified_matches]
        
        # Get decades, filtering out None/NaN values
        decades = [m['education_match'].get('birth_decade') for m in qualified_matches]
        decades = [d for d in decades if d is not None and str(d).lower() != 'nan']
        
        education_info = {
            'has_technical_education': self.get_most_common_value(tech_edu_values, prefer_true=True),
            'has_business_education': self.get_most_common_value(bus_edu_values, prefer_true=True),
            'has_other_higher_education': self.get_most_common_value(other_edu_values, prefer_true=True),
            'birth_decade': self.get_most_common_value(decades) if decades else None
        }
        
        # Add international experience if available
        if any('non_swedish_experience_count' in m['education_match'] for m in qualified_matches):
            non_swedish_values = [
                m['education_match'].get('non_swedish_experience_count', 0) 
                for m in qualified_matches 
                if 'non_swedish_experience_count' in m['education_match']
            ]
            
            has_non_swedish_values = [
                m['education_match'].get('has_non_swedish_experience', False) 
                for m in qualified_matches 
                if 'has_non_swedish_experience' in m['education_match']
            ]
            
            education_info['non_swedish_experience_count'] = self.get_most_common_value(non_swedish_values)
            education_info['has_non_swedish_experience'] = self.get_most_common_value(has_non_swedish_values, prefer_true=True)
        
        if any('usa_experience_count' in m['education_match'] for m in qualified_matches):
            usa_values = [
                m['education_match'].get('usa_experience_count', 0) 
                for m in qualified_matches 
                if 'usa_experience_count' in m['education_match']
            ]
            
            has_usa_values = [
                m['education_match'].get('has_usa_experience', False) 
                for m in qualified_matches 
                if 'has_usa_experience' in m['education_match']
            ]
            
            education_info['usa_experience_count'] = self.get_most_common_value(usa_values)
            education_info['has_usa_experience'] = self.get_most_common_value(has_usa_values, prefer_true=True)
        
        base_info.update(education_info)
        return base_info
    
    def process_director_file(self, file_path):
        """
        Process a single director match file and create summary
        
        Args:
            file_path (str): Path to the director match JSON file
            
        Returns:
            list: List of summarized director records
        """
        company_name = os.path.basename(file_path).split('_')[0]
        print(f"Processing {company_name} director matches...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                all_directors = json.load(f)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return []
        
        # Group matches by director name
        director_groups = {}
        for match in all_directors:
            name = match.get('name')
            if not name:
                continue
                
            if name not in director_groups:
                director_groups[name] = []
                
            director_groups[name].append(match)
        
        # Process each director group to create summaries
        summaries = []
        for name, matches in director_groups.items():
            summary = self.summarize_director(matches, self.threshold)
            if summary:
                summaries.append(summary)
        
        # Sort by tenure (descending)
        summaries.sort(key=lambda x: x.get('tenure', 0), reverse=True)
        return summaries
    
    def process_all_files(self):
        """
        Process all director match files and create summaries
        
        Returns:
            dict: Dictionary mapping company names to lists of summary records
        """
        match_files = self.find_match_files()
        
        if not match_files:
            print(f"No director match files found in {self.input_dir}")
            return {}
        
        print(f"Found {len(match_files)} director match files to process")
        print(f"Using match threshold: {self.threshold}")
        
        results = {}
        for file_path in match_files:
            company_name = os.path.basename(file_path).split('_')[0]
            
            # Process the file and get summaries
            summaries = self.process_director_file(file_path)
            
            if summaries:
                results[company_name] = summaries
                
                # Save to company-specific output file
                output_file = os.path.join(self.output_dir, f"{company_name}_education_summary.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(summaries, f, indent=2, ensure_ascii=False)
                
                print(f"Saved {len(summaries)} director summaries for {company_name}")
            else:
                print(f"No valid director summaries found for {company_name}")
        
        # Create a consolidated file with all companies
        all_directors = []
        for company, directors in results.items():
            all_directors.extend(directors)
            
        if all_directors:
            consolidated_file = os.path.join(self.output_dir, f"all_directors_education_summary.json")
            with open(consolidated_file, 'w', encoding='utf-8') as f:
                json.dump(all_directors, f, indent=2, ensure_ascii=False)
            
            print(f"Saved consolidated summary with {len(all_directors)} directors")
        
        return results

def main():
    parser = argparse.ArgumentParser(description='Summarize director education matches')
    parser.add_argument('--input-dir', default='data/company_director_info',
                        help='Directory containing director match JSON files')
    parser.add_argument('--output-dir', default='data/director_education_summaries',
                        help='Directory to save summary files')
    parser.add_argument('--threshold', type=float, default=90,
                        help='Minimum match score threshold (0-100)')
    
    args = parser.parse_args()
    
    print(f"\nDirector Education Summarizer")
    print(f"=============================")
    print(f"Input directory: {args.input_dir}")
    print(f"Output directory: {args.output_dir}")
    print(f"Match threshold: {args.threshold}")
    
    summarizer = DirectorSummarizer(args.input_dir, args.output_dir, args.threshold)
    results = summarizer.process_all_files()
    
    total_directors = sum(len(directors) for directors in results.values())
    print(f"\nSummary generation complete!")
    print(f"Processed {len(results)} companies")
    print(f"Created summaries for {total_directors} unique directors")
    print(f"All outputs saved to {args.output_dir}")

if __name__ == "__main__":
    main()