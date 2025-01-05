"""Module for handling audio file processing and synchronization."""

import logging
from typing import Optional, Tuple, Dict, Any, List
from src.core.debug_utils import add_debug_message
import soundfile as sf
import numpy as np
from pydub import AudioSegment
import tempfile
import os
import traceback
import streamlit as st

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class AudioProcessor:
    """Handles audio file processing, analysis, and synchronization."""
    
    def __init__(self):
        """Initialize the audio processor."""
        self.audio_data = None
        self.sample_rate = None
        self.audio_segment = None
        self.duration = None
        self.original_filename = None
        self.crossfade_duration_ms = 20  # Changed to 20ms for even more subtle transitions
        self.fade_duration_ms = 300  # Default fade duration
        logger.debug("AudioProcessor initialized")
        logger.debug(f"Crossfade duration set to: {self.crossfade_duration_ms}ms")
        
    def reset(self):
        """Reset the audio processor state."""
        logger.debug("Resetting AudioProcessor state")
        # Clear audio data
        self.audio_data = None
        self.sample_rate = None
        self.audio_segment = None
        self.duration = None
        # Keep original_filename as it might be needed for exports
        self.crossfade_duration_ms = 20
        self.fade_duration_ms = 300
        logger.debug("AudioProcessor state reset complete")
    
    def process_audio(self, audio_file: str, original_filename: str = None) -> Tuple[bool, Optional[str]]:
        """Process an audio file for analysis and editing."""
        try:
            logger.debug(f"Processing audio file: {audio_file}")
            
            # Store original filename
            self.original_filename = original_filename
            
            # Load audio file using soundfile
            logger.debug("Loading audio file with soundfile...")
            audio_data, sample_rate = sf.read(audio_file)
            if audio_data is None or len(audio_data) == 0:
                logger.error("Failed to load audio with soundfile")
                return False, "Failed to load audio file"
            
            # Store raw audio data
            self.audio_data = audio_data
            self.sample_rate = sample_rate
            
            # Calculate duration
            self.duration = len(self.audio_data) / self.sample_rate
            logger.debug(f"Audio duration: {int(self.duration // 60)}:{int(self.duration % 60):02d}")
            
            # Load as AudioSegment for editing
            logger.debug("Loading audio file with pydub...")
            self.audio_segment = AudioSegment.from_file(audio_file)
            logger.debug(f"Audio loaded successfully. Duration: {len(self.audio_segment)/1000.0:.2f} seconds")
            
            # Store both raw audio data and AudioSegment in analysis state if available
            if hasattr(st, 'session_state') and 'analysis_state' in st.session_state:
                st.session_state.analysis_state['raw_audio_data'] = self.audio_data
                st.session_state.analysis_state['audio_data'] = self.audio_segment
                st.session_state.analysis_state['audio_duration'] = self.duration
                st.session_state.analysis_state['sample_rate'] = self.sample_rate
                logger.debug("Stored audio data in analysis state")
            
            return True, None
            
        except Exception as e:
            error_msg = f"Error processing audio: {str(e)}"
            logger.error(f"Error: {error_msg}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False, error_msg
    
    def restore_audio_data(self, audio_data: Any, duration: float) -> bool:
        """Restore audio data after reset.
        
        Args:
            audio_data: The audio data to restore (AudioSegment or numpy array)
            duration: The duration in seconds
            
        Returns:
            bool: True if restoration was successful
        """
        try:
            logger.debug(f"Attempting to restore audio data of type: {type(audio_data)}")
            logger.debug(f"Duration: {duration}")
            
            if audio_data is None:
                logger.error("Cannot restore None audio data")
                return False
            
            if isinstance(audio_data, AudioSegment):
                logger.debug("Restoring from AudioSegment")
                self.audio_segment = audio_data
                self.duration = duration
                # Convert AudioSegment to numpy array for raw audio data
                with tempfile.NamedTemporaryFile(suffix='.wav') as temp_file:
                    logger.debug("Exporting AudioSegment to temporary WAV file")
                    audio_data.export(temp_file.name, format='wav')
                    logger.debug("Reading WAV file with soundfile")
                    self.audio_data, self.sample_rate = sf.read(temp_file.name)
                logger.debug(f"Audio data restored successfully from AudioSegment. Sample rate: {self.sample_rate}")
                return True
                
            elif isinstance(audio_data, np.ndarray):
                logger.debug("Restoring from numpy array")
                # Get sample rate from analysis state
                if hasattr(st, 'session_state') and 'analysis_state' in st.session_state:
                    self.sample_rate = st.session_state.analysis_state.get('sample_rate', 44100)
                    logger.debug(f"Got sample rate from analysis state: {self.sample_rate}")
                else:
                    self.sample_rate = 44100  # Default to standard sample rate
                    logger.debug("Using default sample rate: 44100")
                
                self.audio_data = audio_data
                self.duration = duration
                
                # Convert numpy array to AudioSegment
                with tempfile.NamedTemporaryFile(suffix='.wav') as temp_file:
                    logger.debug("Writing numpy array to temporary WAV file")
                    sf.write(temp_file.name, audio_data, self.sample_rate)
                    logger.debug("Creating AudioSegment from WAV file")
                    self.audio_segment = AudioSegment.from_wav(temp_file.name)
                logger.debug("Audio data restored successfully from numpy array")
                return True
            else:
                logger.error(f"Invalid audio data type for restoration: {type(audio_data)}")
                return False
                
        except Exception as e:
            logger.error(f"Error restoring audio data: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def apply_edits(self, edit_points: List[Dict], apply_fade_in: bool = False, apply_fade_out: bool = False) -> Tuple[bool, Optional[str]]:
        """Apply edits to the audio based on the provided edit points."""
        try:
            if not self.audio_segment:
                logger.error("No audio loaded")
                return False, "No audio loaded"
            
            # Create segments from keep points
            segments = []
            total_duration = len(self.audio_segment)
            
            for edit in edit_points:
                if edit['type'] == 'keep':
                    # Get the time points in milliseconds
                    start_ms = int(edit['start_time'] * 1000)
                    end_ms = int(edit['end_time'] * 1000)
                    original_start_ms = int(edit['original_start'] * 1000)
                    original_end_ms = int(edit['original_end'] * 1000)
                    section_name = edit.get('section', '').lower()
                    
                    try:
                        # Check if this is the last section in our edit
                        is_last_edit_section = edit == edit_points[-1]
                        # Check if this section is the actual final section of the song (Outro)
                        is_final_song_section = 'outro' in section_name or 'ending' in section_name
                        
                        # If this is both the last section in our edit AND the final section of the song
                        if is_last_edit_section and is_final_song_section:
                            end_ms = total_duration
                        
                        segment = self.audio_segment[start_ms:end_ms]
                        
                        # Apply fade-in if this is the first segment and we have an extended region
                        if apply_fade_in and segments == [] and start_ms < original_start_ms:
                            fade_duration = original_start_ms - start_ms
                            segment = segment.fade_in(duration=fade_duration)
                        
                        # Apply fade-out if this is the last section in our edit
                        if apply_fade_out and is_last_edit_section:
                            if is_final_song_section:
                                # For the actual final section, fade out over a longer duration
                                fade_duration = min(2000, end_ms - original_end_ms)  # Use up to 2 seconds for final fade
                            else:
                                # For non-final sections, only fade the extended region
                                fade_duration = end_ms - original_end_ms if end_ms > original_end_ms else 500  # Default to 500ms if no extension
                            
                            segment = segment.fade_out(duration=fade_duration)
                        
                        segments.append(segment)
                    except Exception as e:
                        logger.error(f"Error extracting segment: {str(e)}")
                        raise
            
            # Combine segments with equal-power crossfades
            if segments:
                result = segments[0]
                
                for i in range(1, len(segments)):
                    try:
                        # Get the segments to crossfade
                        seg1 = result
                        seg2 = segments[i]
                        
                        # Calculate crossfade duration (20ms)
                        xfade_ms = self.crossfade_duration_ms
                        
                        # Get the overlapping regions
                        end_region = seg1[-xfade_ms:]
                        start_region = seg2[:xfade_ms]
                        
                        # Create equal-power crossfade by overlaying the faded regions
                        crossfade = (end_region.fade_out(duration=xfade_ms)
                                   .overlay(start_region.fade_in(duration=xfade_ms)))
                        
                        # Join the segments with the crossfaded region
                        result = seg1[:-xfade_ms] + crossfade + seg2[xfade_ms:]
                        
                    except Exception as e:
                        logger.error(f"Error during crossfade: {str(e)}")
                        raise
                
                self.audio_segment = result
                return True, None
            else:
                return False, "No audio segments after editing"
            
        except Exception as e:
            error_msg = f"Error applying audio edits: {str(e)}"
            logger.error(f"Error: {error_msg}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False, error_msg
    
    def export_audio(self, output_path: str, format_type: str = "wav") -> Tuple[bool, Optional[str]]:
        """Export the audio to a file."""
        try:
            if not self.audio_segment:
                logger.error("No audio loaded for export")
                return False, "No audio loaded"
            
            # Export with appropriate format
            logger.debug(f"Exporting audio to {output_path} in {format_type} format")
            self.audio_segment.export(output_path, format=format_type)
            logger.debug("Audio exported successfully")
            
            return True, None
            
        except Exception as e:
            error_msg = f"Error exporting audio: {str(e)}"
            logger.error(f"Error: {error_msg}")
            return False, error_msg
            
    def generate_preview(self, edit_result: Dict, timing_info: Dict, *, fade_in: bool = False, fade_out: bool = False) -> Optional[AudioSegment]:
        """Generate audio preview based on edit result and timing information."""
        try:
            if not self.audio_segment:
                logger.error("No audio loaded for preview generation")
                return None
                
            if not timing_info:
                logger.error("No timing information available")
                return None
                
            # Create sorted list of sections to keep
            action = edit_result.get("action")
            sections_to_keep = []
            
            if action == "keep":
                sections_to_keep = edit_result.get("sections", [])
            elif action == "remove":
                sections_to_keep = [s for s in timing_info.keys() if s not in edit_result.get("sections", [])]
            else:
                logger.error(f"Unsupported edit action: {action}")
                return None
            
            # Filter out snippet markers and sort sections by start time
            sorted_sections = [
                (section, timing_info[section])
                for section in sections_to_keep
                if section in timing_info and not any(x in section.lower() for x in ['/snippet', '/endsnippet'])
            ]
            sorted_sections.sort(key=lambda x: x[1]['start'])
            
            if not sorted_sections:
                logger.error("No valid sections to keep after filtering")
                return None
                
            # Create edit points with extended segments for fades
            edit_points = []
            total_duration = len(self.audio_segment) / 1000.0  # Total duration in seconds
            
            # Calculate measure duration based on first section's time signature
            first_section = sorted_sections[0][1]
            time_signature = first_section.get('time_signature', '4/4')
            
            # Get the duration of one measure from the timing info
            # Each measure has the same duration in the score
            measure_duration = 2.25  # Fixed duration for a measure in 6/8 at 80 BPM
            
            logger.debug(f"Generating preview with {len(sorted_sections)} sections")
            logger.debug(f"Time signature: {time_signature}")
            logger.debug(f"Measure duration: {measure_duration:.2f} seconds")
            
            for i, (section, info) in enumerate(sorted_sections):
                # Add crossfade point between sections
                if i > 0:
                    edit_points.append({
                        'type': 'crossfade',
                        'start_time': info['start'],
                        'end_time': info['start'] + 0.04  # 40ms crossfade
                    })
                
                # Add keep point with extended boundaries for fades
                start_time = info['start']
                end_time = info['end']
                
                # For the first section, extend two measures before if fade-in is enabled
                if i == 0 and fade_in:
                    extended_start = max(0, start_time - (2 * measure_duration))
                    start_time = extended_start
                
                # For the last section, extend two measures after if fade-out is enabled
                if i == len(sorted_sections) - 1 and fade_out:
                    extended_end = min(total_duration, end_time + (2 * measure_duration))
                    end_time = extended_end
                
                edit_point = {
                    'type': 'keep',
                    'start_time': start_time,
                    'end_time': end_time,
                    'section': section,
                    'original_start': info['start'],
                    'original_end': info['end']
                }
                edit_points.append(edit_point)
                
                logger.debug(f"Added edit point for {section}: {start_time:.2f}s - {end_time:.2f}s")
                
            # Apply edits
            success, error = self.apply_edits(edit_points, apply_fade_in=fade_in, apply_fade_out=fade_out)
            if not success:
                logger.error(f"Failed to apply edits: {error}")
                return None
            
            # Return the edited audio
            return self.audio_segment
            
        except Exception as e:
            logger.error(f"Error generating preview: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None 