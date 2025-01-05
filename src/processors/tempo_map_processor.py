"""Module for handling text-based tempo map files."""

import logging
from typing import Dict, List, Tuple, Optional, Union
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TempoMapProcessor:
    """Handles processing of text-based tempo map files."""
    
    def __init__(self):
        """Initialize tempo map processor."""
        self.beat_timings = []
        self.strong_beats = []
        self.beat_types = {}
        self.total_beats = 0
        self.measure_map = {}  # Maps measure numbers to beat ranges
        self.time_signature = None  # Will store beats per measure
        self.total_duration = 0  # Total duration in seconds
        self.initial_offset = 0  # Time before first beat
        
    def process_tempo_file(self, file_path: str, time_signature: Tuple[int, int] = (4, 4)) -> Tuple[bool, Optional[str]]:
        """Process a tempo map text file.
        
        Args:
            file_path: Path to the tempo map text file
            time_signature: Tuple of (beats_per_measure, beat_unit)
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Read the tempo map file
            tempo_data = pd.read_csv(file_path, sep='\t', header=None, 
                                   names=['beat', 'time', 'beat_type'])
            
            # Store initial offset (time of first beat)
            if not tempo_data.empty:
                self.initial_offset = float(tempo_data['time'].iloc[0])
                logger.debug(f"Initial offset in text tempo file: {self.initial_offset:.3f} seconds")
                
                # Calculate total duration from the raw tempo data (last time point)
                self.total_duration = float(tempo_data['time'].iloc[-1])
                logger.debug(f"Total duration from tempo file: {self.total_duration:.3f} seconds")
            
            # Adjust timings by subtracting the initial offset
            tempo_data['adjusted_time'] = tempo_data['time'] - self.initial_offset
            
            # Store beat timings using adjusted time
            self.beat_timings = list(zip(tempo_data['beat'], tempo_data['adjusted_time']))
            
            # Store beat types
            self.beat_types = dict(zip(tempo_data['beat'], tempo_data['beat_type']))
            
            # Identify strong beats
            self.strong_beats = tempo_data[tempo_data['beat_type'] == 's']['beat'].tolist()
            
            # Store total beats
            self.total_beats = len(tempo_data)
            
            # Store time signature
            self.time_signature = time_signature
            
            # Create measure mapping
            self._create_measure_mapping()
            
            # Log summary
            logger.debug(f"Processed tempo file with {self.total_beats} beats")
            logger.debug(f"Found {len(self.strong_beats)} strong beats")
            logger.debug(f"Initial offset: {self.initial_offset:.3f} seconds")
            logger.debug(f"Total duration: {self.total_duration:.3f} seconds")
            logger.debug(f"Adjusted duration: {self.total_duration - self.initial_offset:.3f} seconds")
            
            return True, None
            
        except Exception as e:
            error_msg = f"Error processing tempo map file: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
    def _create_measure_mapping(self):
        """Create mapping between measures and beats based on strong beats."""
        if not self.strong_beats:
            return
            
        beats_per_measure = self.time_signature[0]
        current_measure = 1
        
        # Group beats into measures
        for i in range(len(self.strong_beats) - 1):
            start_beat = self.strong_beats[i]
            end_beat = self.strong_beats[i + 1]
            
            # Get all beats in this measure
            measure_beats = []
            measure_times = []
            for beat, time in self.beat_timings:
                if start_beat <= beat < end_beat:
                    measure_beats.append(beat)
                    measure_times.append(time)
            
            # Calculate average tempo for this measure
            if len(measure_times) > 1:
                beat_durations = [measure_times[i+1] - measure_times[i] for i in range(len(measure_times)-1)]
                avg_beat_duration = sum(beat_durations) / len(beat_durations)
                tempo_bpm = 60.0 / avg_beat_duration
            else:
                tempo_bpm = 0  # Unable to calculate tempo for this measure
            
            # Store measure information
            self.measure_map[current_measure] = {
                'start_beat': start_beat,
                'end_beat': end_beat - 1,  # Exclusive end
                'start_time': self.get_beat_timing(start_beat),
                'end_time': self.get_beat_timing(end_beat),
                'tempo': tempo_bpm
            }
            current_measure += 1
            
        # Handle last measure
        if self.strong_beats:
            last_start = self.strong_beats[-1]
            last_beats = []
            last_times = []
            for beat, time in self.beat_timings:
                if beat >= last_start:
                    last_beats.append(beat)
                    last_times.append(time)
            
            # Calculate tempo for last measure
            if len(last_times) > 1:
                beat_durations = [last_times[i+1] - last_times[i] for i in range(len(last_times)-1)]
                avg_beat_duration = sum(beat_durations) / len(beat_durations)
                tempo_bpm = 60.0 / avg_beat_duration
            else:
                tempo_bpm = 0
            
            self.measure_map[current_measure] = {
                'start_beat': last_start,
                'end_beat': self.total_beats - 1,
                'start_time': self.get_beat_timing(last_start),
                'end_time': self.get_beat_timing(self.total_beats - 1),
                'tempo': tempo_bpm
            }
    
    def get_tempo_changes(self) -> List[Dict[str, Union[int, float]]]:
        """Get list of tempo changes from the text tempo file.
        
        Returns:
            List of dictionaries containing measure numbers and their tempos
        """
        tempo_changes = []
        for measure, info in sorted(self.measure_map.items()):
            if info['tempo'] > 0:  # Only include measures where we could calculate tempo
                tempo_changes.append({
                    'measure': measure,
                    'tempo': info['tempo']
                })
        return tempo_changes
    
    def get_measure_timing(self, measure_number: int) -> Optional[Dict[str, float]]:
        """Get timing information for a specific measure.
        
        Args:
            measure_number: The measure number to get timing for
            
        Returns:
            Dictionary with start_time and end_time in seconds, or None if not found
        """
        measure_info = self.measure_map.get(measure_number)
        if not measure_info:
            return None
            
        return {
            'start_time': measure_info['start_time'],
            'end_time': measure_info['end_time'],
            'duration': measure_info['end_time'] - measure_info['start_time']
        }
    
    def get_beat_timing(self, beat_number: int) -> Optional[float]:
        """Get the timing for a specific beat.
        
        Args:
            beat_number: The beat number to get timing for
            
        Returns:
            Timestamp in seconds for the beat, or None if not found
        """
        for beat, time in self.beat_timings:
            if beat == beat_number:
                return time
        return None
    
    def get_nearest_strong_beat(self, beat_number: int) -> Optional[int]:
        """Get the nearest strong beat to a given beat number.
        
        Args:
            beat_number: The beat number to find nearest strong beat for
            
        Returns:
            Nearest strong beat number, or None if not found
        """
        if not self.strong_beats:
            return None
            
        # Find the closest strong beat
        return min(self.strong_beats, key=lambda x: abs(x - beat_number))
    
    def get_section_timing(self, start_beat: int, end_beat: int) -> Dict[str, float]:
        """Get timing information for a section defined by beat numbers.
        
        Args:
            start_beat: Starting beat number
            end_beat: Ending beat number
            
        Returns:
            Dictionary with start and end times in seconds, accounting for initial offset
        """
        # Get raw timings from beat_timings (these are already adjusted by initial_offset)
        start_time = self.get_beat_timing(start_beat)
        end_time = self.get_beat_timing(end_beat)
        
        if start_time is None or end_time is None:
            return {}
        
        # Add back the initial offset to get actual file positions
        actual_start = start_time + self.initial_offset
        actual_end = end_time + self.initial_offset
        
        return {
            'start': actual_start,
            'end': actual_end,
            'duration': actual_end - actual_start,
            'adjusted_start': start_time,  # Store adjusted times for debugging
            'adjusted_end': end_time,
            'initial_offset': self.initial_offset
        }
    
    def get_beat_type(self, beat_number: int) -> Optional[str]:
        """Get the type of a specific beat (strong 's' or light 'l').
        
        Args:
            beat_number: The beat number to get type for
            
        Returns:
            Beat type ('s' or 'l'), or None if not found
        """
        return self.beat_types.get(beat_number) 
    
    def get_total_duration(self) -> float:
        """Get the total duration of the audio file according to the tempo map.
        
        Returns:
            Total duration in seconds, including initial offset
        """
        return self.total_duration
    
    def get_adjusted_duration(self) -> float:
        """Get the duration of the actual musical content (excluding initial offset).
        
        Returns:
            Duration in seconds, excluding initial offset
        """
        return self.total_duration - self.initial_offset 
    
    def get_tempo_range(self) -> str:
        """Get the range of tempos in the tempo map.
        
        Returns:
            String describing the tempo range (e.g., "72.7 - 117.2 BPM")
        """
        if not self.measure_map:
            return "Unknown"
            
        tempos = [info['tempo'] for info in self.measure_map.values() if info['tempo'] > 0]
        if not tempos:
            return "Unknown"
            
        min_tempo = min(tempos)
        max_tempo = max(tempos)
        
        if min_tempo == max_tempo:
            return f"{min_tempo:.1f} BPM"
        else:
            return f"{min_tempo:.1f} - {max_tempo:.1f} BPM" 