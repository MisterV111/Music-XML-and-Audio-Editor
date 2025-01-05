"""Module for handling audio editing operations."""

import logging
from typing import Optional, Tuple, Dict, List
from pydub import AudioSegment
from src.core.debug_utils import add_debug_message

class AudioEditor:
    """Handles audio editing operations including fades and crossfades."""
    
    def __init__(self):
        """Initialize the audio editor."""
        self.crossfade_ms = 40  # Default crossfade duration in milliseconds
        self.fade_duration_ms = 300  # Default fade duration in milliseconds
        self.audio = None
        
    def load_audio(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Load an audio file for editing.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            self.audio = AudioSegment.from_file(file_path)
            return True, None
        except Exception as e:
            return False, f"Failed to load audio: {str(e)}"
    
    def apply_edits(self, sections: List[Dict], fade_in: bool = False, fade_out: bool = False) -> Tuple[bool, Optional[str]]:
        """Apply edits to the audio including fades and crossfades.
        
        Args:
            sections: List of section dictionaries with start and end times
            fade_in: Whether to apply fade in
            fade_out: Whether to apply fade out
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            if not self.audio:
                return False, "No audio loaded"
            
            # Sort sections by start time
            sorted_sections = sorted(sections, key=lambda x: x['start'])
            
            # Create segments
            segments = []
            for section in sorted_sections:
                start_ms = int(section['start'] * 1000)
                end_ms = int(section['end'] * 1000)
                segment = self.audio[start_ms:end_ms]
                segments.append(segment)
            
            # Combine segments with crossfades
            if segments:
                result = segments[0]
                for segment in segments[1:]:
                    result = result.append(segment, crossfade=self.crossfade_ms)
                
                # Apply fade in/out if requested
                if fade_in:
                    result = result.fade_in(self.fade_duration_ms)
                if fade_out:
                    result = result.fade_out(self.fade_duration_ms)
                
                self.audio = result
                return True, None
            
            return False, "No segments to combine"
            
        except Exception as e:
            return False, f"Failed to apply edits: {str(e)}"
    
    def generate_preview(self, position: float, duration: float = 5.0) -> Tuple[bool, Optional[str], Optional[AudioSegment]]:
        """Generate a preview around a specific position.
        
        Args:
            position: Position in seconds
            duration: Preview duration in seconds
            
        Returns:
            Tuple of (success, error_message, preview_audio)
        """
        try:
            if not self.audio:
                return False, "No audio loaded", None
            
            position_ms = int(position * 1000)
            duration_ms = int(duration * 1000)
            
            start_ms = max(0, position_ms - duration_ms // 2)
            end_ms = min(len(self.audio), position_ms + duration_ms // 2)
            
            preview = self.audio[start_ms:end_ms]
            return True, None, preview
            
        except Exception as e:
            return False, f"Failed to generate preview: {str(e)}", None
    
    def export_audio(self, output_path: str, format_type: str = 'wav') -> Tuple[bool, Optional[str]]:
        """Export the edited audio.
        
        Args:
            output_path: Path to save the file
            format_type: Output format (wav/ogg)
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            if not self.audio:
                return False, "No audio to export"
            
            self.audio.export(output_path, format=format_type)
            return True, None
            
        except Exception as e:
            return False, f"Failed to export audio: {str(e)}"