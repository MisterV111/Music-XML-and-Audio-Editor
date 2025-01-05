"""Module for handling text-based tempo map files."""

import logging
from typing import Dict, List, Tuple, Optional, Union
import pandas as pd
from src.core.debug_utils import add_debug_message
import traceback

logger = logging.getLogger(__name__)

class TextTempoProcessor:
    """Handles processing of text-based tempo map files."""
    
    def __init__(self):
        """Initialize text tempo processor."""
        self.beat_timings = []
        self.strong_beats = []
        self.measure_map = {}
        self.initial_offset = 0
        self.total_duration = 0
        self.time_signature = None
        
    def process_tempo_file(self, file_path: str, time_signature: Tuple[int, int]) -> Tuple[bool, Optional[str]]:
        """Process a text tempo file and map beats to measures.
        
        Args:
            file_path: Path to the text tempo file
            time_signature: Tuple of (beats_per_measure, beat_unit)
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Read the tempo file with explicit encoding and line endings
            try:
                tempo_data = pd.read_csv(file_path, sep='\t', header=None, 
                                       names=['beat', 'time', 'beat_type'],
                                       encoding='utf-8', lineterminator='\n')
            except UnicodeDecodeError:
                # Try alternate encoding if UTF-8 fails
                tempo_data = pd.read_csv(file_path, sep='\t', header=None, 
                                       names=['beat', 'time', 'beat_type'],
                                       encoding='latin1', lineterminator='\n')
            
            # Log raw data for debugging
            add_debug_message("\nDebug: First few rows of tempo data:")
            add_debug_message(str(tempo_data.head()))
            
            # Validate tempo data
            if tempo_data.empty:
                add_debug_message("Error: Empty tempo file")
                return False, "Empty tempo file"
            
            if not all(col in tempo_data.columns for col in ['beat', 'time', 'beat_type']):
                add_debug_message("Error: Invalid tempo file format - missing required columns")
                return False, "Invalid tempo file format - missing required columns"
            
            # Validate data types and clean beat types
            try:
                tempo_data['beat'] = tempo_data['beat'].astype(float)
                tempo_data['time'] = tempo_data['time'].astype(float)
                # Clean and normalize beat types
                tempo_data['beat_type'] = (tempo_data['beat_type']
                                         .astype(str)
                                         .str.strip()
                                         .str.lower())  # Convert to lowercase
            except Exception as e:
                add_debug_message(f"Error: Invalid data types in tempo file - {str(e)}")
                return False, f"Invalid data types in tempo file - {str(e)}"
            
            # Debug log unique beat types
            unique_beat_types = set(tempo_data['beat_type'].unique())
            add_debug_message(f"Debug: Found beat types in file: {unique_beat_types}")
            
            # Validate beat types
            valid_beat_types = {'s', 'w', 'l'}  # strong, weak, and light beats
            invalid_types = [bt for bt in unique_beat_types if bt not in valid_beat_types]
            if invalid_types:
                add_debug_message(f"Error: Invalid beat types found: {invalid_types}")
                return False, f"Invalid beat types in tempo file - must be 's', 'w', or 'l'. Found: {invalid_types}"
            
            # Store initial offset
            self.initial_offset = float(tempo_data['time'].iloc[0])
            add_debug_message(f"\nDebug: Initial offset in text tempo file: {self.initial_offset:.3f} seconds")
            
            # Store time signature
            self.time_signature = time_signature
            
            # Process beat timings
            self._process_beat_timings(tempo_data)
            
            # Validate we have strong beats
            if not self.strong_beats:
                add_debug_message("Error: No strong beats found in tempo file")
                return False, "No strong beats found in tempo file"
            
            # Map measures to timings
            self.map_measures_to_time()
            
            # Validate measure map
            if not self.measure_map:
                add_debug_message("Error: Failed to create measure map")
                return False, "Failed to create measure map"
            
            add_debug_message("Successfully processed tempo file")
            return True, None
            
        except Exception as e:
            error_msg = f"Error processing text tempo file: {str(e)}"
            add_debug_message(f"Debug Error: {error_msg}")
            add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
            return False, error_msg
    
    def _process_beat_timings(self, tempo_data: pd.DataFrame) -> None:
        """Process beat timings from tempo data.
        
        Args:
            tempo_data: DataFrame with beat, time, and beat_type columns
        """
        # Store beat timings (adjusted for initial offset)
        self.beat_timings = list(zip(
            tempo_data['beat'],
            tempo_data['time'] - self.initial_offset  # Adjust times
        ))
        
        # Identify strong beats (measure starts)
        self.strong_beats = tempo_data[tempo_data['beat_type'] == 's']['beat'].tolist()
        
        # Calculate total duration
        if self.beat_timings:
            self.total_duration = self.beat_timings[-1][1]
        
        add_debug_message(f"Processed {len(self.beat_timings)} beats")
        add_debug_message(f"Found {len(self.strong_beats)} strong beats (measures)")
        add_debug_message(f"Total duration (adjusted): {self.total_duration:.3f} seconds")
    
    def map_measures_to_time(self) -> None:
        """Map measure numbers to their exact timings using strong beats."""
        if not self.strong_beats:
            logger.error("No strong beats found to map measures")
            return
        
        current_measure = 1
        
        # Map each pair of strong beats to a measure
        for i in range(len(self.strong_beats) - 1):
            start_beat = self.strong_beats[i]
            end_beat = self.strong_beats[i + 1]
            
            # Get exact timings
            start_time = self._get_beat_time(start_beat)
            end_time = self._get_beat_time(end_beat)
            
            if start_time is not None and end_time is not None:
                self.measure_map[current_measure] = {
                    'start_beat': start_beat,
                    'end_beat': end_beat - 1,
                    'start_time': start_time,
                    'end_time': end_time,
                    'real_start_time': start_time + self.initial_offset,
                    'real_end_time': end_time + self.initial_offset,
                    'duration': end_time - start_time
                }
            
            current_measure += 1
        
        # Handle last measure
        if self.strong_beats:
            last_beat = self.strong_beats[-1]
            last_time = self._get_beat_time(last_beat)
            final_time = self.beat_timings[-1][1]  # Last timing in file
            
            if last_time is not None:
                self.measure_map[current_measure] = {
                    'start_beat': last_beat,
                    'end_beat': self.beat_timings[-1][0],
                    'start_time': last_time,
                    'end_time': final_time,
                    'real_start_time': last_time + self.initial_offset,
                    'real_end_time': final_time + self.initial_offset,
                    'duration': final_time - last_time
                }
        
        add_debug_message(f"Mapped {len(self.measure_map)} measures to exact timings")
    
    def _get_beat_time(self, beat_number: int) -> Optional[float]:
        """Get the timing for a specific beat.
        
        Args:
            beat_number: The beat number to find timing for
            
        Returns:
            Time in seconds (adjusted) or None if not found
        """
        for beat, time in self.beat_timings:
            if beat == beat_number:
                return time
        return None
    
    def get_measure_timing(self, measure_number: int) -> Optional[Dict[str, float]]:
        """Get timing information for a specific measure.
        
        Args:
            measure_number: The measure number to get timing for
            
        Returns:
            Dictionary with timing information or None if not found
        """
        measure_info = self.measure_map.get(measure_number)
        if not measure_info:
            return None
        
        return {
            'start_time': measure_info['real_start_time'],
            'end_time': measure_info['real_end_time'],
            'duration': measure_info['duration'],
            'beat_start': measure_info['start_beat'],
            'beat_end': measure_info['end_beat']
        }
    
    def get_section_timing(self, start_measure: int, end_measure: int) -> Optional[Dict[str, float]]:
        """Get timing information for a section.
        
        Args:
            start_measure: Starting measure number
            end_measure: Ending measure number
            
        Returns:
            Dictionary with section timing information or None if not found
        """
        start_info = self.measure_map.get(start_measure)
        end_info = self.measure_map.get(end_measure)
        
        if not start_info or not end_info:
            return None
        
        return {
            'start': start_info['real_start_time'],
            'end': end_info['real_end_time'],
            'duration': end_info['real_end_time'] - start_info['real_start_time'],
            'start_measure': start_measure,
            'end_measure': end_measure
        } 