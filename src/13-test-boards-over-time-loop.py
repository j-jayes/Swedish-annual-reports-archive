import json
import os
import re
import pandas as pd
import numpy as np
from fuzzywuzzy import fuzz, process
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

class BoardMemberTracker:
    def __init__(self, base_dir="new data/structured", company_name=None):
        """
        Initialize the BoardMemberTracker with a base directory and optional company name.
        
        Args:
            base_dir (str): Base directory containing the JSON data files
            company_name (str, optional): Company name to track. If provided, files will be 
                                          loaded automatically for this company.
        """
        self.base_dir = base_dir
        self.company_name = company_name
        self.file_paths = []
        self.raw_data = {}
        self.board_members = {}
        self.board_timeline = pd.DataFrame()
        self.fuzzy_match_threshold = 85  # Default threshold for fuzzy matching
        
        # If company name is provided, automatically find relevant files
        if company_name:
            self.find_company_files()
    
    def find_company_files(self, company_name=None):
        """
        Find all JSON files for a specific company with suffix '_1.json'.
        
        Args:
            company_name (str, optional): Company name to search for.
                                         If None, uses the instance's company_name.
                                         
        Returns:
            self: Returns self for method chaining
        """
        if company_name:
            self.company_name = company_name
            
        if not self.company_name:
            raise ValueError("Company name must be provided")
            
        # Pattern to match: COMPANY-YEAR_1.json
        pattern = rf"{re.escape(self.company_name)}-\d+_1\.json"
        
        self.file_paths = []
        
        # Walk through the directory structure
        for root, _, files in os.walk(self.base_dir):
            for file in files:
                if re.match(pattern, file):
                    self.file_paths.append(os.path.join(root, file))
        
        # Sort files by year
        self.file_paths.sort(key=lambda x: self._extract_year_from_filename(x))
        
        print(f"Found {len(self.file_paths)} files for {self.company_name}")
        return self
    
    def _extract_year_from_filename(self, filename):
        """Extract year from a filename"""
        match = re.search(r'-(\d+)_', filename)
        if match:
            return int(match.group(1))
        return 0
        
    def load_data(self):
        """
        Load data from all found JSON files
        
        Returns:
            self: Returns self for method chaining
        """
        if not self.file_paths:
            print("No files found. Call find_company_files() first.")
            return self
            
        self.raw_data = {}
        
        for file_path in self.file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    fiscal_year = data.get('fiscal_year')
                    
                    if fiscal_year:
                        # Ensure board is a list or None, never anything else
                        board = data.get('board')
                        if board is not None and not isinstance(board, list):
                            print(f"Warning: Board data in {file_path} is not a list. Setting to empty list.")
                            board = []
                            
                        self.raw_data[fiscal_year] = {
                            'company_name': data.get('company_name'),
                            'board': board,
                            'file_path': file_path
                        }
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
        
        print(f"Loaded data for {len(self.raw_data)} years")
        return self
    
    def _preprocess_name(self, name):
        """Standardize name format for better matching"""
        if not name:
            return ""
        return name.lower().strip()
    
    def _create_full_name(self, member):
        """Create a standardized full name from a board member record"""
        surname = self._preprocess_name(member.get('surname', ''))
        first_name = self._preprocess_name(member.get('first_name', ''))
        initials = self._preprocess_name(member.get('initials', ''))
        
        if surname and first_name:
            return f"{surname}, {first_name} {initials}".strip()
        elif surname:
            return surname
        return ""
    
    def _is_likely_same_person(self, member1, member2):
        """
        Use fuzzy matching to determine if two records likely refer to the same person
        
        Args:
            member1 (dict): First board member record
            member2 (dict): Second board member record
            
        Returns:
            bool: True if likely the same person, False otherwise
        """
        name1 = self._create_full_name(member1)
        name2 = self._create_full_name(member2)
        
        if not name1 or not name2:
            return False
        
        # Calculate similarity score using token sort ratio
        # This helps handle cases where name parts are in different orders
        score = fuzz.token_sort_ratio(name1, name2)
        
        # For very short names, use a higher threshold to avoid false matches
        if len(name1) < 6 or len(name2) < 6:
            return score >= (self.fuzzy_match_threshold + 10)
            
        return score >= self.fuzzy_match_threshold
    
    def track_board_membership(self):
        """
        Track board membership across years using fuzzy matching
        
        Returns:
            self: Returns self for method chaining
        """
        if not self.raw_data:
            print("No data loaded. Run load_data() first.")
            return self
            
        all_members = []
        years = sorted(self.raw_data.keys())
        
        # First pass: collect all members with uniqueness check
        for year in years:
            board = self.raw_data[year].get('board', [])
            
            # Skip if board is None
            if board is None:
                print(f"Warning: Board data for year {year} is None")
                continue
                
            for member in board:
                # Skip if empty data
                if not member.get('surname'):
                    continue
                
                # Check if this person already exists in our master list
                found = False
                
                for existing_member in all_members:
                    if self._is_likely_same_person(member, existing_member):
                        # This is likely the same person, just update their record
                        existing_member['years'][year] = {
                            'position': member.get('position'),
                            'representation': {
                                'surname': member.get('surname'),
                                'first_name': member.get('first_name'),
                                'initials': member.get('initials'),
                                'position': member.get('position')
                            }
                        }
                        found = True
                        break
                
                # If not found, add as a new member
                if not found:
                    new_member = {
                        'surname': member.get('surname'),
                        'first_name': member.get('first_name'),
                        'initials': member.get('initials'),
                        'years': {
                            year: {
                                'position': member.get('position'),
                                'representation': {
                                    'surname': member.get('surname'),
                                    'first_name': member.get('first_name'),
                                    'initials': member.get('initials'),
                                    'position': member.get('position')
                                }
                            }
                        }
                    }
                    all_members.append(new_member)
        
        self.board_members = all_members
        return self
    
    def create_timeline(self):
        """
        Create a timeline DataFrame of board membership
        
        Returns:
            pd.DataFrame: DataFrame with board membership timeline
        """
        if not self.board_members:
            print("No board members tracked yet. Run track_board_membership() first.")
            return None
        
        # Get all years in the dataset
        all_years = sorted(self.raw_data.keys())
        
        # Create a DataFrame to represent the timeline
        data = []
        
        for member in self.board_members:
            name = f"{member['surname']}, {member['first_name'] or ''}"
            name = name.strip(", ")
            
            row = {'Name': name}
            positions = set()
            
            # Add a column for each year
            for year in all_years:
                if year in member['years']:
                    position = member['years'][year]['position']
                    row[str(year)] = position
                    if position:
                        positions.add(position)
                else:
                    row[str(year)] = None
            
            # Calculate tenure
            years_present = [year for year in all_years if year in member['years']]
            if years_present:
                row['First Year'] = min(years_present)
                row['Last Year'] = max(years_present)
                row['Tenure'] = len(years_present)
                row['Consecutive'] = self._is_consecutive_tenure(years_present)
            else:
                row['First Year'] = None
                row['Last Year'] = None
                row['Tenure'] = 0
                row['Consecutive'] = False
                
            row['Positions'] = " | ".join(positions) if positions else ""
            data.append(row)
        
        # Create the DataFrame and sort by tenure and name
        timeline_df = pd.DataFrame(data)
        if not timeline_df.empty:
            timeline_df = timeline_df.sort_values(by=['Tenure', 'Name'], ascending=[False, True])
        
        self.board_timeline = timeline_df
        return timeline_df
    
    def _is_consecutive_tenure(self, years):
        """Check if a list of years represents consecutive tenure"""
        if not years:
            return False
            
        years = sorted(years)
        return all(years[i] + 1 == years[i+1] for i in range(len(years) - 1))
    
    def visualize_timeline(self, output_file=None, figsize=(12, None)):
        """
        Create a visual representation of board member tenures
        
        Args:
            output_file (str, optional): Path to save the visualization. If None, display instead.
            figsize (tuple, optional): Figure size (width, height). If height is None, it's calculated.
            
        Returns:
            matplotlib.figure.Figure: The matplotlib figure
        """
        if self.board_timeline.empty:
            self.create_timeline()
            
        if self.board_timeline.empty:
            print("No timeline data available.")
            return None
        
        # Prepare data for visualization
        years = [str(year) for year in sorted(self.raw_data.keys())]
        members = self.board_timeline['Name'].tolist()
        
        # Calculate height based on number of members if not specified
        if figsize[1] is None:
            height = max(6, len(members) * 0.4)
            figsize = (figsize[0], height)
        
        # Create a binary matrix for the heatmap
        presence_data = []
        for _, row in self.board_timeline.iterrows():
            member_presence = [1 if pd.notna(row[year]) else 0 for year in years]
            presence_data.append(member_presence)
        
        # Create the heatmap
        plt.figure(figsize=figsize)
        ax = sns.heatmap(
            presence_data, 
            cmap=['white', 'steelblue'],
            cbar=False,
            linewidths=1,
            linecolor='gray',
            yticklabels=members,
            xticklabels=years
        )
        
        plt.title(f'Board Member Tenure Timeline - {self.company_name}')
        plt.xlabel('Year')
        plt.tight_layout()
        
        if output_file:
            plt.savefig(output_file)
        else:
            plt.show()
            
        return plt.gcf()
    
    def export_to_csv(self, file_path=None):
        """
        Export the board timeline to a CSV file
        
        Args:
            file_path (str, optional): Path to save the CSV file. If None, generates a path.
            
        Returns:
            str: Path to the saved CSV file, or None if export failed
        """
        if self.board_timeline.empty:
            self.create_timeline()
            
        if self.board_timeline.empty:
            print("No timeline data available to export.")
            return None
        
        # Generate file path if not provided
        if not file_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = f"{self.company_name}_board_timeline_{timestamp}.csv"
        
        try:
            self.board_timeline.to_csv(file_path, index=False)
            print(f"Timeline exported to {file_path}")
            return file_path
        except Exception as e:
            print(f"Error exporting to CSV: {e}")
            return None
    
    def export_long_serving_members_to_json(self, output_file=None, min_tenure=3):
        """
        Export members who have served for more than the specified minimum tenure to JSON
        
        Args:
            output_file (str, optional): Path to save the JSON file. If None, generates a path.
            min_tenure (int): Minimum years of tenure to include in the export
            
        Returns:
            str: Path to the saved JSON file, or None if export failed
        """
        if self.board_timeline.empty:
            self.create_timeline()
            
        if self.board_timeline.empty:
            print("No timeline data available to export.")
            return None
        
        # Filter for members with tenure > min_tenure
        long_serving_members = self.board_timeline[self.board_timeline['Tenure'] > min_tenure]
        
        if long_serving_members.empty:
            print(f"No members found with tenure > {min_tenure} years.")
            return None
        
        # Prepare data for export
        export_data = []
        for _, member in long_serving_members.iterrows():
            # Find the original board member data to get all details
            original_member = None
            for m in self.board_members:
                name = f"{m['surname']}, {m['first_name'] or ''}".strip(", ")
                if name == member['Name']:
                    original_member = m
                    break
            
            if original_member:
                member_data = {
                    'name': member['Name'],
                    'company': self.company_name,
                    'surname': original_member['surname'],
                    'first_name': original_member['first_name'] or '',
                    'initials': original_member['initials'] or '',
                    'first_year': int(member['First Year']),
                    'last_year': int(member['Last Year']),
                    'tenure': int(member['Tenure']),
                    'positions': member['Positions'],
                    'consecutive': bool(member['Consecutive'])
                }
                export_data.append(member_data)
        
        # Generate file path if not provided
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"{self.company_name}_long_serving_members_{timestamp}.json"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            print(f"Long-serving members exported to {output_file}")
            return output_file
        except Exception as e:
            print(f"Error exporting to JSON: {e}")
            return None
            
    def get_board_changes(self):
        """
        Analyze and report changes in board composition between years
        
        Returns:
            dict: Dictionary with board changes information
        """
        if not self.board_members:
            print("No board members tracked yet. Run track_board_membership() first.")
            return None
            
        years = sorted(self.raw_data.keys())
        changes = {}
        
        for i in range(len(years) - 1):
            current_year = years[i]
            next_year = years[i+1]
            
            # Get board members for each year
            current_members = set()
            next_members = set()
            
            for member in self.board_members:
                name = f"{member['surname']}, {member['first_name'] or ''}".strip(", ")
                
                if current_year in member['years']:
                    current_members.add(name)
                
                if next_year in member['years']:
                    next_members.add(name)
            
            # Calculate changes
            joined = next_members - current_members
            left = current_members - next_members
            stayed = current_members.intersection(next_members)
            
            # Position changes
            position_changes = []
            for member in self.board_members:
                name = f"{member['surname']}, {member['first_name'] or ''}".strip(", ")
                
                if current_year in member['years'] and next_year in member['years']:
                    current_pos = member['years'][current_year]['position']
                    next_pos = member['years'][next_year]['position']
                    
                    if current_pos != next_pos:
                        position_changes.append({
                            'name': name,
                            'from': current_pos,
                            'to': next_pos
                        })
            
            changes[f"{current_year}-{next_year}"] = {
                'joined': sorted(list(joined)),
                'left': sorted(list(left)),
                'stayed': sorted(list(stayed)),
                'position_changes': position_changes
            }
        
        return changes
    
    def print_board_changes_summary(self):
        """
        Print a human-readable summary of board changes
        
        Returns:
            self: Returns self for method chaining
        """
        changes = self.get_board_changes()
        if not changes:
            return self
            
        print(f"\n==== Board Changes for {self.company_name} ====")
        
        for period, change_data in changes.items():
            print(f"\nChanges from {period}:")
            
            if change_data['joined']:
                print(f"  Joined: {', '.join(change_data['joined'])}")
            
            if change_data['left']:
                print(f"  Left: {', '.join(change_data['left'])}")
            
            if change_data['position_changes']:
                print("  Position changes:")
                for change in change_data['position_changes']:
                    print(f"    {change['name']}: {change['from'] or '(none)'} → {change['to'] or '(none)'}")
        
        return self
    
    def print_tenure_statistics(self):
        """
        Print statistics about board member tenures
        
        Returns:
            self: Returns self for method chaining
        """
        if self.board_timeline.empty:
            self.create_timeline()
            
        if self.board_timeline.empty:
            print("No timeline data available.")
            return self
            
        # Calculate statistics
        stats = {
            'total_members': len(self.board_timeline),
            'avg_tenure': self.board_timeline['Tenure'].mean(),
            'max_tenure': self.board_timeline['Tenure'].max(),
            'min_tenure': self.board_timeline['Tenure'].min(),
            'median_tenure': self.board_timeline['Tenure'].median()
        }
        
        # Members with longest tenures
        longest_serving = self.board_timeline.nlargest(3, 'Tenure')
        
        print(f"\n==== Board Tenure Statistics for {self.company_name} ====")
        print(f"Total board members: {stats['total_members']}")
        print(f"Average tenure: {stats['avg_tenure']:.2f} years")
        print(f"Median tenure: {stats['median_tenure']:.1f} years")
        print(f"Tenure range: {stats['min_tenure']} to {stats['max_tenure']} years")
        
        print("\nLongest serving members:")
        for _, member in longest_serving.iterrows():
            print(f"  {member['Name']}: {member['Tenure']} years ({member['First Year']}-{member['Last Year']})")
            
        return self
    
    def get_company_summary(self):
        """
        Generate a comprehensive summary of the company's board
        
        Returns:
            dict: Summary information
        """
        if self.board_timeline.empty:
            self.create_timeline()
            
        years = sorted(self.raw_data.keys())
        
        # Calculate board size over time
        board_size_by_year = {}
        for year in years:
            board_size = sum(1 for _, row in self.board_timeline.iterrows() if pd.notna(row[str(year)]))
            board_size_by_year[year] = board_size
        
        # Calculate turnover rate
        changes = self.get_board_changes()
        turnover_by_period = {}
        
        for period, change_data in changes.items():
            year1, year2 = map(int, period.split('-'))
            joined = len(change_data['joined'])
            left = len(change_data['left'])
            stayed = len(change_data['stayed'])
            
            # Turnover rate = (Joined + Left) / (2 * Average board size)
            avg_board_size = (board_size_by_year[year1] + board_size_by_year[year2]) / 2
            turnover_rate = (joined + left) / (2 * avg_board_size) if avg_board_size > 0 else 0
            
            turnover_by_period[period] = {
                'joined': joined,
                'left': left,
                'stayed': stayed,
                'turnover_rate': turnover_rate
            }
        
        # Average board size
        avg_board_size = sum(board_size_by_year.values()) / len(board_size_by_year) if board_size_by_year else 0
        
        # Average turnover rate
        avg_turnover = sum(d['turnover_rate'] for d in turnover_by_period.values()) / len(turnover_by_period) if turnover_by_period else 0
        
        return {
            'company_name': self.company_name,
            'years_covered': f"{min(years)}-{max(years)}" if years else "N/A",
            'total_years': len(years),
            'total_members': len(self.board_timeline),
            'avg_board_size': avg_board_size,
            'avg_tenure': self.board_timeline['Tenure'].mean() if not self.board_timeline.empty else 0,
            'median_tenure': self.board_timeline['Tenure'].median() if not self.board_timeline.empty else 0,
            'avg_turnover_rate': avg_turnover,
            'board_size_by_year': board_size_by_year,
            'turnover_by_period': turnover_by_period
        }

def process_company(company_name, base_dir="new data/structured", output_dir=None, min_tenure=3):
    """
    Process a single company's board data
    
    Args:
        company_name (str): Company name
        base_dir (str): Base directory containing data files
        output_dir (str, optional): Directory to save outputs
        min_tenure (int): Minimum years of tenure for exporting long-serving members
        
    Returns:
        BoardMemberTracker: The configured tracker instance
    """
    # Create output directory if it doesn't exist
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Initialize and run the tracker
    tracker = BoardMemberTracker(base_dir, company_name)
    tracker.load_data()
    
    # Check if we have any data
    if not tracker.raw_data:
        print(f"No data found for company: {company_name}")
        return tracker
    
    tracker.track_board_membership().create_timeline()
    
    # Check if timeline was created successfully
    if tracker.board_timeline.empty:
        print(f"No timeline data created for company: {company_name}")
        return tracker
    
    # Generate outputs
    if output_dir:
        try:
            # Save timeline to CSV
            csv_path = os.path.join(output_dir, f"{company_name}_board_timeline.csv")
            tracker.export_to_csv(csv_path)
            
            # Save long-serving members to JSON
            json_path = os.path.join(output_dir, f"{company_name}_long_serving_members.json")
            tracker.export_long_serving_members_to_json(json_path, min_tenure)
            
            # Create and save visualization
            viz_path = os.path.join(output_dir, f"{company_name}_board_timeline.png")
            tracker.visualize_timeline(viz_path)
            
            # Save summary as JSON
            summary = tracker.get_company_summary()
            summary_path = os.path.join(output_dir, f"{company_name}_board_summary.json")
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)
        except Exception as e:
            print(f"Error generating outputs for {company_name}: {e}")
    
    # Print summary information
    try:
        tracker.print_tenure_statistics().print_board_changes_summary()
    except Exception as e:
        print(f"Error printing statistics for {company_name}: {e}")
    
    return tracker

def process_multiple_companies(company_names, base_dir="new data/structured", output_dir=None, min_tenure=3):
    """
    Process multiple companies' board data
    
    Args:
        company_names (list): List of company names
        base_dir (str): Base directory containing data files
        output_dir (str, optional): Directory to save outputs
        min_tenure (int): Minimum years of tenure for exporting long-serving members
        
    Returns:
        dict: Company name -> BoardMemberTracker mapping
    """
    results = {}
    successful = 0
    failed = 0
    
    for i, company in enumerate(company_names):
        print(f"\n\n======== Processing {company} ({i+1}/{len(company_names)}) ========")
        try:
            tracker = process_company(company, base_dir, output_dir, min_tenure)
            results[company] = tracker
            successful += 1
        except Exception as e:
            print(f"Error processing {company}: {e}")
            failed += 1
            # Continue with next company
            continue
    
    print(f"\nProcessing complete: {successful} successful, {failed} failed")
    return results

def get_company_names_from_csv(csv_path):
    """
    Extract company names from CSV file
    
    Args:
        csv_path (str): Path to the CSV file containing company names
        
    Returns:
        list: List of company names
    """
    try:
        if not os.path.exists(csv_path):
            print(f"Warning: CSV file {csv_path} not found.")
            return []
            
        df = pd.read_csv(csv_path)
        
        # Assuming the column name is 'company_name'
        if 'company_name' in df.columns:
            company_names = df['company_name'].dropna().tolist()
        else:
            # If column name is different, try the first column
            company_names = df.iloc[:, 0].dropna().tolist()
            
        # Filter out any empty strings or non-string values
        company_names = [str(name).strip() for name in company_names if name]
        
        print(f"Found {len(company_names)} companies in CSV file.")
        return company_names
    except Exception as e:
        print(f"Error reading company names from CSV: {e}")
        return []

def create_consolidated_json(output_dir, output_file="all_long_serving_members.json"):
    """
    Consolidate all individual company long-serving member JSON files into a single file
    
    Args:
        output_dir (str): Directory containing individual JSON files
        output_file (str): Name of the consolidated output file
        
    Returns:
        str: Path to the consolidated JSON file, or None if consolidation failed
    """
    if not os.path.exists(output_dir):
        print(f"Output directory {output_dir} does not exist.")
        return None
    
    all_members = []
    
    # Find all long-serving member JSON files
    for file in os.listdir(output_dir):
        if file.endswith("_long_serving_members.json"):
            try:
                with open(os.path.join(output_dir, file), 'r', encoding='utf-8') as f:
                    members = json.load(f)
                    all_members.extend(members)
            except Exception as e:
                print(f"Error reading {file}: {e}")
    
    if not all_members:
        print("No long-serving member data found to consolidate.")
        return None
    
    # Write the consolidated file
    output_path = os.path.join(output_dir, output_file)
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_members, f, indent=2, ensure_ascii=False)
        print(f"Consolidated {len(all_members)} members into {output_path}")
        return output_path
    except Exception as e:
        print(f"Error writing consolidated file: {e}")
        return None

# Example usage
if __name__ == "__main__":
    # Set up directories
    base_dir = "new data/structured"
    output_dir = "output_results"
    
    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Get company names from CSV
    company_names = get_company_names_from_csv("data/company_names.csv")
    
    if not company_names:
        print("No company names found in CSV. Using default examples.")
        company_names = ["AGA", "ASEA", "Atlas"]
    
    print(f"Processing {len(company_names)} companies: {', '.join(company_names[:5])}{'...' if len(company_names) > 5 else ''}")
    
    # Process all companies
    trackers = process_multiple_companies(
        company_names,
        base_dir=base_dir,
        output_dir=output_dir,
        min_tenure=3
    )
    
    # Create consolidated JSON of all long-serving members
    consolidated_file = create_consolidated_json(output_dir)
    
    print("\nProcessing complete!")
    print(f"Processed {len(trackers)} companies")
    print(f"All outputs saved to {output_dir}")
    if consolidated_file:
        print(f"Consolidated long-serving members saved to {consolidated_file}")