"""Module for handling export of edited audio and scores."""

import logging
import os
import json
from typing import Dict, List, Optional, Tuple
from pydub import AudioSegment
import music21

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class ExportProcessor:
    """Handles export of edited audio and scores."""
    
    def __init__(self):
        """Initialize the export processor."""
        self.supported_audio_formats = ['wav', 'ogg']
        self.supported_score_formats = ['xml', 'musicxml']
        
    def export_audio(self,
                    audio_segment: AudioSegment,
                    output_path: str,
                    format: str = 'wav') -> Tuple[bool, Optional[str]]:
        """Export the edited audio file.
        
        Args:
            audio_segment: The edited audio segment
            output_path: Path to save the exported file
            format: Audio format to export (wav, ogg)
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            if format not in self.supported_audio_formats:
                return False, f"Unsupported audio format: {format}"
                
            # Create output directory if needed
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Export audio
            audio_segment.export(output_path, format=format)
            
            return True, None
            
        except Exception as e:
            return False, f"Failed to export audio: {str(e)}"
            
    def export_score(self,
                    score_data: Dict,
                    output_path: str,
                    format: str = 'xml') -> Tuple[bool, Optional[str]]:
        """Export the edited score.
        
        Args:
            score_data: Dictionary containing score information
            output_path: Path to save the exported file
            format: Score format to export (xml, musicxml)
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            if format not in self.supported_score_formats:
                return False, f"Unsupported score format: {format}"
                
            # Create output directory if needed
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Convert score data to music21 stream
            score = music21.stream.Score()
            # TODO: Implement score data conversion
            
            # Export score
            if format == 'xml':
                score.write('musicxml', output_path)
            
            return True, None
            
        except Exception as e:
            return False, f"Failed to export score: {str(e)}"
            
    def export_project(self,
                      project_data: Dict,
                      output_dir: str) -> Tuple[bool, Optional[str]]:
        """Export the entire project including audio, score, and metadata.
        
        Args:
            project_data: Dictionary containing all project data
            output_dir: Directory to save exported files
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Export audio if available
            if 'audio' in project_data:
                for format in self.supported_audio_formats:
                    output_path = os.path.join(output_dir, f"audio.{format}")
                    success, error = self.export_audio(
                        project_data['audio'],
                        output_path,
                        format
                    )
                    if not success:
                        return False, f"Failed to export {format} audio: {error}"
            
            # Export score if available
            if 'score' in project_data:
                output_path = os.path.join(output_dir, "score.xml")
                success, error = self.export_score(
                    project_data['score'],
                    output_path
                )
                if not success:
                    return False, f"Failed to export score: {error}"
            
            # Export metadata
            metadata = {
                'edit_history': project_data.get('edit_history', []),
                'tempo_map': project_data.get('tempo_map', {}),
                'sections': project_data.get('sections', {})
            }
            
            with open(os.path.join(output_dir, "metadata.json"), 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return True, None
            
        except Exception as e:
            return False, f"Failed to export project: {str(e)}" 