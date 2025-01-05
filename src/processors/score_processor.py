from typing import Dict, Optional, Tuple
import traceback
from src.core.debug_utils import add_debug_message

class ScoreProcessor:
    def __init__(self):
        self.analyzer = None
        self.sections = {}
        self.measure_times = {}
        self.tempo_changes = []
        self.time_signature = None
        self.key_signature = None
        self._total_measures = 0  # Track the actual number of measures
        self._unique_measures = 0  # Track unique measures
        
    def _reset_measure_counts(self):
        """Reset measure counts before processing."""
        self._total_measures = 0
        self._unique_measures = 0
        self.measure_times = {}

    def get_section_timing(self) -> Optional[Dict[str, Dict[str, float]]]:
        """Get timing information for each section.
        
        Returns:
            Dictionary mapping section names to timing information
        """
        try:
            if not self.sections:
                return None
            
            timing_info = {}
            
            # If we have measure times (score tempo), use them
            if self.measure_times:
                valid_measures = set(self.measure_times.keys())
                
                for section_name, (start_measure, end_measure) in self.sections.items():
                    # Only process sections where both start and end measures are from the first part
                    if start_measure in valid_measures and end_measure in valid_measures:
                        timing_info[section_name] = {
                            'start': self.measure_times[start_measure]['start'],
                            'end': self.measure_times[end_measure]['end'],
                            'duration': self.measure_times[end_measure]['end'] - self.measure_times[start_measure]['start'],
                            'start_measure': start_measure,
                            'end_measure': end_measure
                        }
                    else:
                        add_debug_message(f"Warning: Section '{section_name}' contains measures not found in first part")
            else:
                # If no measure times (using tempo map), just provide measure numbers
                for section_name, (start_measure, end_measure) in self.sections.items():
                    timing_info[section_name] = {
                        'start_measure': start_measure,
                        'end_measure': end_measure
                    }
            
            return timing_info
            
        except Exception as e:
            add_debug_message(f"Error getting section timing: {str(e)}")
            return None 

    def _calculate_measure_times(self) -> Tuple[bool, Optional[str]]:
        """Calculate the start and end times for each measure based on tempo changes."""
        try:
            if not self.tempo_changes:
                return False, "No tempo changes available"
            
            # If we're using text tempo map, skip measure time calculation
            if not self.measure_times and not self.tempo_changes:
                add_debug_message("Skipping measure time calculation (using text tempo map)")
                return True, None
            
            # Check for countdown measure
            countdown_info = self.analyzer.has_countdown_measure()
            has_countdown = countdown_info['has_countdown']
            
            # Reset state
            self._reset_measure_counts()
            self.measure_times = {}
            current_time = 0.0
            current_tempo = self.tempo_changes[0]['tempo']
            tempo_index = 0
            
            # Get measures from the first part only
            first_part = self.analyzer.score.parts[0]
            measures = []
            
            # Only get measures from the first part, ignoring any duplicates
            seen_numbers = set()
            for measure in first_part.getElementsByClass('Measure'):
                if measure.number not in seen_numbers:
                    measures.append(measure)
                    seen_numbers.add(measure.number)
            
            # Sort measures by number
            sorted_measures = sorted(measures, key=lambda m: m.number)
            
            if not sorted_measures:
                return False, "No measures found in score"
            
            # Add debug information about parts and measures
            part_count = len(self.analyzer.score.parts)
            add_debug_message(f"\nFound {part_count} parts in score")
            add_debug_message(f"Processing {len(sorted_measures)} measures from first part")
            
            # Calculate time for each measure
            total_duration = 0.0
            processed_measures = set()  # Track which measures we've processed
            
            for measure in sorted_measures:
                measure_number = measure.number
                if measure_number in processed_measures:
                    continue  # Skip if we've already processed this measure
                
                processed_measures.add(measure_number)
                
                # Check for tempo change
                while (tempo_index + 1 < len(self.tempo_changes) and 
                       self.tempo_changes[tempo_index + 1]['measure'] <= measure_number):
                    tempo_index += 1
                    current_tempo = self.tempo_changes[tempo_index]['tempo']
                
                # Get time signature for this measure
                time_sig = None
                for ts in measure.recurse().getElementsByClass('TimeSignature'):
                    time_sig = ts
                    break
                
                if time_sig:
                    # Use actual time signature from measure
                    numerator = time_sig.numerator
                    denominator = time_sig.denominator
                elif self.time_signature:
                    # Use global time signature
                    numerator, denominator = map(int, self.time_signature.split('/'))
                else:
                    # Default to 4/4
                    numerator, denominator = 4, 4
                
                # Special handling for countdown measure
                if has_countdown and measure_number == 1:
                    # For countdown measure, use exactly 5 beats duration
                    measure_duration = (60.0 / current_tempo) * 5  # 5 beats at current tempo
                    effective_tempo = current_tempo
                    beats_per_measure = 5
                else:
                    # Normal measure calculation
                    if denominator == 8:
                        # Compound time signature (e.g., 6/8, 9/8, 12/8)
                        seconds_per_quarter = 60.0 / current_tempo
                        quarters_per_measure = numerator / 2
                        measure_duration = seconds_per_quarter * quarters_per_measure
                        effective_tempo = current_tempo * (2/3)
                        beats_per_measure = numerator / 3
                    elif denominator == 4:
                        # Simple time signature (e.g., 4/4, 3/4)
                        beats_per_measure = numerator
                        effective_tempo = current_tempo
                        seconds_per_beat = 60.0 / effective_tempo
                        measure_duration = beats_per_measure * seconds_per_beat
                    else:
                        # Other time signatures (e.g., 2/2, 3/2)
                        beats_per_measure = numerator * (4 / denominator)
                        effective_tempo = current_tempo * (denominator / 4)
                        seconds_per_beat = 60.0 / effective_tempo
                        measure_duration = beats_per_measure * seconds_per_beat
                
                # Store measure timing
                self.measure_times[measure_number] = {
                    'start': current_time,
                    'end': current_time + measure_duration,
                    'duration': measure_duration,
                    'tempo': current_tempo,
                    'effective_tempo': effective_tempo,
                    'time_signature': f"{numerator}/{denominator}",
                    'beats_per_measure': beats_per_measure,
                    'is_countdown': has_countdown and measure_number == 1
                }
                
                current_time += measure_duration
                total_duration = current_time
            
            # Only show duration information if not using text tempo map
            if self.tempo_changes:
                minutes = int(total_duration // 60)
                seconds = int(total_duration % 60)
                add_debug_message(f"\nScore duration calculated: {minutes}:{seconds:02d}")
                add_debug_message(f"Total duration in seconds: {total_duration:.3f}")
                add_debug_message(f"Average measure duration: {total_duration/len(processed_measures):.3f} seconds")
            
            return True, None
            
        except Exception as e:
            error_msg = f"Error calculating measure times: {str(e)}"
            add_debug_message(f"Debug Error: {error_msg}")
            add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
            return False, error_msg 

    def calculate_section_duration(self, start_measure: int, end_measure: int) -> float:
        """Calculate the duration of a section based on measure timings.
        
        Args:
            start_measure: Starting measure number
            end_measure: Ending measure number
            
        Returns:
            Duration in seconds
        """
        try:
            if not self.measure_times:
                return 0.0
            
            # Get the valid measure numbers from the first part
            valid_measures = set(self.measure_times.keys())
            
            # Check if measures are from the first part
            if start_measure not in valid_measures or end_measure not in valid_measures:
                add_debug_message(f"Warning: Measures {start_measure}-{end_measure} not found in first part")
                return 0.0
            
            return (self.measure_times[end_measure]['end'] - 
                   self.measure_times[start_measure]['start'])
                   
        except Exception as e:
            add_debug_message(f"Error calculating section duration: {str(e)}")
            return 0.0 

    def process_score(self, score_file: str, timing_source: str = "constant_tempo") -> Tuple[bool, Optional[str]]:
        """Process the score to extract timing and section information.
        
        Args:
            score_file: Path to the score file
            timing_source: Source of timing information:
                         - "text_tempo_map": Using external text tempo map (ignore score tempo)
                         - "score_tempo_map": Using tempo changes from MusicXML (ignore score tempo)
                         - "constant_tempo": Using constant tempo from score
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            add_debug_message("\nDebug: Processing score")
            
            # Reset measure counts
            self._reset_measure_counts()
            
            # Load score
            success, error = self.analyzer.load_score(score_file)
            if not success:
                return False, error
            
            # Get time signature (always needed)
            time_analysis = self.analyzer.analyze_time_signature()
            if time_analysis.get('error'):
                return False, time_analysis['error']
            self.time_signature = time_analysis['final']
            add_debug_message(f"Time signature: {self.time_signature}")
            
            # Get key signature (always needed)
            key_analysis = self.analyzer.analyze_key()
            if not key_analysis.get('error'):
                self.key_signature = key_analysis['final']
                add_debug_message(f"Key signature: {self.key_signature}")
            
            # Analyze structure (always needed for sections)
            structure_analysis = self.analyzer.analyze_structure()
            if structure_analysis.get('error'):
                return False, structure_analysis['error']
            self.sections = structure_analysis.get('sections', {})
            
            # Handle timing based on source
            if timing_source == "text_tempo_map":
                # Using text tempo map - ignore ALL score tempo information
                add_debug_message("Using text tempo map - ignoring score tempo information")
                # Only get measure count, skip ALL tempo analysis
                timing_analysis = self.analyzer.analyze_timing(skip_duration_calc=True)
                if timing_analysis.get('error'):
                    return False, timing_analysis['error']
                # Clear all tempo-related data
                self.tempo_changes = []
                self.measure_times = {}
                add_debug_message("Score tempo analysis skipped - using text tempo map timings")
                
            elif timing_source == "score_tempo_map":
                # Using MusicXML tempo changes - ignore score's base tempo
                add_debug_message("Using MusicXML tempo changes - ignoring score base tempo")
                timing_analysis = self.analyzer.analyze_timing(skip_duration_calc=False)
                if timing_analysis.get('error'):
                    return False, timing_analysis['error']
                
                # Extract only the tempo change markers
                tempo_changes = []
                for change in timing_analysis.get('tempo_changes', []):
                    if change['measure'] > 1 or len(timing_analysis.get('tempo_changes', [])) == 1:
                        tempo_changes.append(change)
                
                if not tempo_changes:
                    return False, "No tempo changes found in MusicXML"
                
                self.tempo_changes = tempo_changes
                
                # Calculate measure times based on tempo changes
                success, error = self._calculate_measure_times()
                if not success:
                    return False, error
                    
            else:  # constant_tempo
                # Using constant tempo from score
                add_debug_message("Using constant tempo from score")
                timing_analysis = self.analyzer.analyze_timing(skip_duration_calc=False)
                if timing_analysis.get('error'):
                    return False, timing_analysis['error']
                
                # Only use initial tempo
                initial_tempo = timing_analysis.get('tempo_changes', [{}])[0].get('tempo', 80.0)
                self.tempo_changes = [{
                    'measure': 1,
                    'tempo': initial_tempo
                }]
                
                # Calculate measure times based on constant tempo
                success, error = self._calculate_measure_times()
                if not success:
                    return False, error
            
            return True, None
            
        except Exception as e:
            error_msg = f"Error processing score: {str(e)}"
            add_debug_message(f"Debug Error: {error_msg}")
            add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
            return False, error_msg 