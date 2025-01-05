import logging
from typing import Dict, List, Optional, Tuple
import openai

class EditProcessor:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the edit processor.
        
        Args:
            api_key: Optional OpenAI API key. If not provided, must be set later.
        """
        self.api_key = api_key
        self.sections = {}  # Original section data
        self.tempo_data = {}  # Original tempo data
        self.edit_points = []  # List of edit points
        self.crossfade_ms = 40  # Default crossfade duration in ms
        self.fade_in = False
        self.fade_out = False
        self.fade_duration_ms = 300  # Default fade duration in ms
        
    def set_api_key(self, api_key: str):
        """Set the OpenAI API key."""
        self.api_key = api_key
        
    def initialize_from_analysis(self, analysis_data: Dict):
        """Initialize processor with analysis results.
        
        Args:
            analysis_data: Dictionary containing section and tempo information
        """
        self.sections = analysis_data.get('sections', {})
        self.tempo_data = analysis_data.get('tempo_data', {})
        
    def parse_edit_command(self, command: str) -> Tuple[bool, Optional[str], List[Dict]]:
        """Parse user edit command using OpenAI API.
        
        Args:
            command: User's edit instruction
            
        Returns:
            Tuple of (success, error_message, edit_points)
            where edit_points is a list of dictionaries containing:
            {
                'action': 'cut'|'join',
                'position': measure_number,
                'crossfade': bool,
                'section_before': str,
                'section_after': str
            }
        """
        if not self.api_key:
            return False, "OpenAI API key not set", []
            
        try:
            # Format the sections data for the prompt
            sections_str = "\n".join([
                f"{name}: measures {start}-{end}"
                for name, (start, end) in self.sections.items()
            ])
            
            # Create the prompt
            prompt = f"""Given a song with the following structure:
{sections_str}

The user wants to: {command}

Analyze this request and provide:
1. List of sections to keep in order
2. List of sections to remove
3. Exact measure numbers where cuts need to be made
4. Whether crossfades are needed at each cut point

Format the response as a JSON object."""

            # Call OpenAI API
            openai.api_key = self.api_key
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a music editing assistant. Analyze edit requests and provide precise cut points."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse response and create edit points
            # This is a placeholder - we'll implement the full parsing logic
            edit_points = []
            
            return True, None, edit_points
            
        except Exception as e:
            return False, f"Failed to parse edit command: {str(e)}", []
            
    def validate_edit_points(self, edit_points: List[Dict]) -> Tuple[bool, Optional[str]]:
        """Validate that edit points are valid and won't create issues.
        
        Args:
            edit_points: List of edit point dictionaries
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not edit_points:
            return False, "No edit points provided"
            
        try:
            # Validate each edit point
            for point in edit_points:
                # Check required fields
                if not all(k in point for k in ['action', 'position']):
                    return False, "Invalid edit point format"
                    
                # Validate measure numbers
                if point['position'] < 1:
                    return False, "Invalid measure number"
                    
                # Validate actions
                if point['action'] not in ['cut', 'join']:
                    return False, "Invalid edit action"
                    
            return True, None
            
        except Exception as e:
            return False, f"Edit point validation failed: {str(e)}" 