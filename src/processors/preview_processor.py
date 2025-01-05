"""Module for handling preview generation of audio and score edits."""

import logging
import os
import tempfile
from typing import Dict, List, Optional, Tuple
from pydub import AudioSegment

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class PreviewProcessor:
    """Handles generation of previews for audio and score edits."""
    
    def __init__(self):
        """Initialize the preview processor."""
        self.temp_dir = tempfile.mkdtemp()
        self.preview_duration = 5  # Default preview duration in seconds
    
    def generate_audio_preview(self, 
                             audio_segment: AudioSegment,
                             edit_point: Dict,
                             preview_id: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Generate a preview audio clip around an edit point.
        
        Args:
            audio_segment: The full audio segment
            edit_point: Dictionary containing edit point information
            preview_id: Unique identifier for this preview
            
        Returns:
            Tuple of (success, error_message, preview_path)
        """
        try:
            # Calculate preview window
            position_ms = edit_point['position_ms']
            start_ms = max(0, position_ms - (self.preview_duration * 1000) // 2)
            end_ms = min(len(audio_segment), position_ms + (self.preview_duration * 1000) // 2)
            
            # Extract preview segment
            preview_segment = audio_segment[start_ms:end_ms]
            
            # Add markers at the edit point
            marker = AudioSegment.silent(duration=50).apply_gain(-20)
            marker_position = position_ms - start_ms
            preview_segment = preview_segment.overlay(marker, position=marker_position)
            
            # Export preview
            preview_path = os.path.join(self.temp_dir, f"preview_{preview_id}.wav")
            preview_segment.export(preview_path, format="wav")
            
            return True, None, preview_path
            
        except Exception as e:
            return False, f"Failed to generate audio preview: {str(e)}", None
            
    def generate_score_preview(self,
                             score_data: Dict,
                             edit_point: Dict,
                             preview_measures: int = 4) -> Tuple[bool, Optional[str], Dict]:
        """Generate a preview of the score around an edit point.
        
        Args:
            score_data: Dictionary containing score information
            edit_point: Dictionary containing edit point information
            preview_measures: Number of measures to show before and after
            
        Returns:
            Tuple of (success, error_message, preview_data)
        """
        try:
            measure = edit_point['position']
            start_measure = max(1, measure - preview_measures)
            end_measure = measure + preview_measures
            
            # Extract relevant measures
            preview_data = {
                'start_measure': start_measure,
                'end_measure': end_measure,
                'edit_point': measure,
                'measures': {}  # Will contain measure data
            }
            
            return True, None, preview_data
            
        except Exception as e:
            return False, f"Failed to generate score preview: {str(e)}", {}
            
    def cleanup(self):
        """Remove temporary preview files."""
        try:
            for file in os.listdir(self.temp_dir):
                os.remove(os.path.join(self.temp_dir, file))
            os.rmdir(self.temp_dir)
        except Exception as e:
            logging.error(f"Failed to cleanup preview files: {str(e)}") 