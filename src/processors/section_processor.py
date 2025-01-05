"""Module for handling section-based editing operations."""

import logging
from typing import Optional, Tuple, Dict, Any, List
from src.core.debug_utils import add_debug_message

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class SectionProcessor:
    """Handles section-based editing operations."""
    
    def __init__(self, score_processor=None, audio_processor=None, tempo_map_processor=None):
        """Initialize section processor.
        
        Args:
            score_processor: Instance of ScoreProcessor for score operations
            audio_processor: Instance of AudioProcessor for audio operations
            tempo_map_processor: Optional instance of TempoMapProcessor for text tempo maps
        """
        self.score_processor = score_processor
        self.audio_processor = audio_processor
        self.tempo_map_processor = tempo_map_processor
        self.sections = {}
        self.edit_points = []
    
    def process_edit_command(self, command: str) -> Tuple[bool, Optional[str]]:
        """Process an edit command for sections.
        
        Args:
            command: Edit command (e.g., 'remove verse 1, keep chorus')
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            add_debug_message("\nDebug: Processing Edit Command")
            add_debug_message(f"Command: {command}")
            
            # Parse command into actions
            actions = {'remove': [], 'keep': []}
            for part in command.lower().split('.'):
                if 'remove' in part:
                    sections = self._extract_sections(part)
                    actions['remove'].extend(sections)
                    add_debug_message(f"Sections to remove: {', '.join(sections)}")
                elif 'keep' in part:
                    sections = self._extract_sections(part)
                    actions['keep'].extend(sections)
                    add_debug_message(f"Sections to keep: {', '.join(sections)}")
            
            # Validate sections exist
            if not self._validate_sections(actions):
                return False, "Invalid section names in command"
            
            # Calculate edit points
            edit_points = self._calculate_edit_points(actions)
            if not edit_points:
                return False, "Failed to calculate edit points"
            
            self.edit_points = edit_points
            return True, None
            
        except Exception as e:
            error_msg = f"Error processing edit command: {str(e)}"
            add_debug_message(f"Debug Error: {error_msg}")
            return False, error_msg
    
    def _extract_sections(self, text: str) -> List[str]:
        """Extract section names from command text.
        
        Args:
            text: Part of command containing section names
            
        Returns:
            List of section names
        """
        # Remove action words and split by commas/and
        text = text.replace('remove', '').replace('keep', '')
        sections = []
        for part in text.split(','):
            for subpart in part.split('and'):
                section = subpart.strip()
                if section:
                    sections.append(section)
        return sections
    
    def _validate_sections(self, actions: Dict[str, List[str]]) -> bool:
        """Validate that all sections in the actions exist.
        
        Args:
            actions: Dictionary of actions with section names
            
        Returns:
            True if all sections are valid
        """
        if not self.score_processor or not self.score_processor.sections:
            add_debug_message("Error: No sections available in score")
            return False
        
        all_sections = set(self.score_processor.sections.keys())
        for action_type, sections in actions.items():
            for section in sections:
                if section not in all_sections:
                    add_debug_message(f"Error: Section '{section}' not found in score")
                    return False
        return True
    
    def get_total_duration(self) -> float:
        """Get the total duration of the audio content.
        
        Returns:
            Total duration in seconds
        """
        # If we have a tempo map, use its duration as the source of truth
        if self.tempo_map_processor:
            duration = self.tempo_map_processor.get_total_duration()
            add_debug_message("\nDebug: Using text tempo map for timing")
            add_debug_message(f"Initial offset: {self.tempo_map_processor.initial_offset:.3f}s")
            add_debug_message(f"Total duration: {duration:.3f}s ({int(duration // 60)}:{int(duration % 60):02d})")
            add_debug_message(f"Adjusted duration: {self.tempo_map_processor.get_adjusted_duration():.3f}s")
            add_debug_message(f"Tempo range: {self.tempo_map_processor.get_tempo_range()}")
            add_debug_message("Note: Score duration calculation skipped when using tempo map")
            return duration
        
        # Only calculate score duration if no tempo map
        if self.score_processor:
            duration = self.score_processor.get_total_duration()
            add_debug_message("\nDebug: Using score timing (constant tempo)")
            add_debug_message(f"Score duration: {duration:.3f}s ({int(duration // 60)}:{int(duration % 60):02d})")
            add_debug_message(f"Constant tempo: {self.score_processor.get_initial_tempo()} BPM")
            return duration
        
        return 0.0
    
    def _calculate_edit_points(self, actions: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Calculate edit points based on actions.
        
        Args:
            actions: Dictionary of actions with section names
            
        Returns:
            List of edit point dictionaries
        """
        try:
            edit_points = []
            timing_info = self.score_processor.get_section_timing()
            
            if not timing_info:
                add_debug_message("Error: No timing information available")
                return []
            
            # Determine timing source and strategy
            using_tempo_map = self.tempo_map_processor is not None
            add_debug_message("\nDebug: Timing Analysis Strategy")
            
            if using_tempo_map:
                # When using tempo map, completely ignore score tempo
                add_debug_message("Using text tempo map (variable tempo)")
                add_debug_message(f"Initial offset: {self.tempo_map_processor.initial_offset:.3f}s")
                add_debug_message(f"Total beats: {self.tempo_map_processor.total_beats}")
                add_debug_message(f"Strong beats (measures): {len(self.tempo_map_processor.strong_beats)}")
                add_debug_message(f"Tempo range: {self.tempo_map_processor.get_tempo_range()}")
                total_duration = self.tempo_map_processor.get_total_duration()
                add_debug_message(f"Using exact beat timings from tempo map")
            else:
                # Only use score tempo if no tempo map is provided
                add_debug_message("Using score timing (constant tempo)")
                add_debug_message(f"Constant tempo: {self.score_processor.get_initial_tempo()} BPM")
                total_duration = self.score_processor.get_total_duration()
                add_debug_message(f"Using constant tempo calculations")
            
            add_debug_message(f"Total duration: {total_duration:.2f}s ({int(total_duration // 60)}:{int(total_duration % 60):02d})")
            
            # Handle sections to remove
            for section in actions.get('remove', []):
                if section in timing_info:
                    info = timing_info[section]
                    add_debug_message(f"\nDebug: Processing section '{section}'")
                    add_debug_message(f"Measures: {info['start_measure']} to {info['end_measure']}")
                    
                    edit_point = {
                        'type': 'remove',
                        'section': section,
                        'start_measure': info['start_measure'],
                        'end_measure': info['end_measure'],
                        'needs_tempo_map': using_tempo_map
                    }
                    
                    if using_tempo_map and 'beat_start' in info and 'beat_end' in info:
                        # Use exact beat timings from tempo map
                        add_debug_message(f"Beat range: {info['beat_start']} to {info['beat_end']}")
                        
                        tempo_timing = self.tempo_map_processor.get_section_timing(
                            info['beat_start'], info['beat_end'])
                        
                        if tempo_timing:
                            # For the last section, extend to the total duration if needed
                            if info['end_measure'] == max(timing_info[s]['end_measure'] for s in timing_info):
                                add_debug_message("Last section detected - extending to total duration")
                                tempo_timing['end'] = total_duration
                            
                            add_debug_message(f"Section timing from tempo map:")
                            add_debug_message(f"  Start: {tempo_timing['start']:.3f}s")
                            add_debug_message(f"  End: {tempo_timing['end']:.3f}s")
                            add_debug_message(f"  Duration: {tempo_timing['duration']:.3f}s")
                            
                            edit_point.update({
                                'start_time': tempo_timing['start'],
                                'end_time': tempo_timing['end'],
                                'duration': tempo_timing['duration'],
                                'beat_start': info['beat_start'],
                                'beat_end': info['beat_end'],
                                'using_tempo_map': True,
                                'initial_offset': tempo_timing['initial_offset']
                            })
                        else:
                            add_debug_message("Error: Failed to get tempo map timing")
                            return []
                    else:
                        if using_tempo_map:
                            add_debug_message("Error: Missing beat information for tempo map timing")
                            return []
                        else:
                            # Only use score timing if no tempo map is provided
                            add_debug_message(f"Using constant tempo timing")
                            edit_point.update({
                                'start_time': info['start'],
                                'end_time': info['end'],
                                'duration': info['end'] - info['start'],
                                'using_tempo_map': False
                            })
                    
                    add_debug_message(f"Final timing for {section}: {edit_point['start_time']:.2f}s to {edit_point['end_time']:.2f}s")
                    edit_points.append(edit_point)
            
            # Sort edit points by start time
            edit_points.sort(key=lambda x: x['start_time'])
            
            # Validate no overlapping edits
            for i in range(1, len(edit_points)):
                if edit_points[i]['start_time'] < edit_points[i-1]['end_time']:
                    add_debug_message("Error: Overlapping edit points detected")
                    return []
            
            return edit_points
            
        except Exception as e:
            add_debug_message(f"Error calculating edit points: {str(e)}")
            return []
    
    def validate_edit_sequence(self, sections: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
        """Validate a sequence of section edits.
        
        Args:
            sections: List of section edit operations
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            if not sections:
                return False, "No edit operations provided"
            
            # Check for valid timing information
            timing_info = self.score_processor.get_section_timing()
            if not timing_info:
                return False, "No timing information available"
            
            # Validate each section exists
            for section in sections:
                if section['section'] not in timing_info:
                    return False, f"Section '{section['section']}' not found"
            
            # Validate edit points are in sequence
            sorted_sections = sorted(sections, key=lambda x: x['start_time'])
            for i in range(1, len(sorted_sections)):
                if sorted_sections[i]['start_time'] < sorted_sections[i-1]['end_time']:
                    return False, "Edit points overlap"
            
            return True, None
            
        except Exception as e:
            error_msg = f"Error validating edit sequence: {str(e)}"
            add_debug_message(f"Debug Error: {error_msg}")
            return False, error_msg
    
    def apply_section_edits(self, edit_points: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Apply section edit operations to the score and audio.
        
        Args:
            edit_points: Dictionary containing edit operations
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            if not edit_points:
                return False, "No edit points provided"
            
            # Validate edit sequence
            success, error = self.validate_edit_sequence(edit_points)
            if not success:
                return False, error
            
            # Apply edits to score
            if self.score_processor:
                # Score editing will be implemented here
                pass
            
            # Apply edits to audio
            if self.audio_processor:
                # Audio editing will be implemented here
                pass
            
            return True, None
            
        except Exception as e:
            error_msg = f"Error applying section edits: {str(e)}"
            add_debug_message(f"Debug Error: {error_msg}")
            return False, error_msg 
    
    def generate_tempo_map_for_edits(self, edit_points: List[Dict[str, Any]]) -> Optional[str]:
        """Generate a new tempo map for edited sections when using variable tempo.
        
        Args:
            edit_points: List of edit points with timing information
            
        Returns:
            Path to new tempo map file, or None if not needed/failed
        """
        if not edit_points:
            return None
            
        # Only generate new tempo map if we're using one
        if not any(point.get('needs_tempo_map', False) for point in edit_points):
            add_debug_message("No tempo map generation needed (constant tempo)")
            return None
            
        try:
            add_debug_message("\nDebug: Generating new tempo map for edited sections")
            
            # Create list of beats to keep
            kept_beats = []
            for point in edit_points:
                if point.get('using_tempo_map') and 'beat_start' in point and 'beat_end' in point:
                    # Get all beats in this section
                    section_beats = []
                    for beat, time in self.tempo_map_processor.beat_timings:
                        if point['beat_start'] <= beat <= point['beat_end']:
                            # Adjust timing relative to section start
                            adjusted_time = time - point['initial_offset']
                            section_beats.append((beat, adjusted_time))
                    kept_beats.extend(section_beats)
            
            if not kept_beats:
                add_debug_message("No beat information available for tempo map generation")
                return None
            
            # Sort beats by time
            kept_beats.sort(key=lambda x: x[1])
            
            # Create new tempo map file
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
            with open(temp_file.name, 'w') as f:
                for beat, time in kept_beats:
                    # Get beat type from original tempo map
                    beat_type = self.tempo_map_processor.get_beat_type(beat) or 'l'
                    f.write(f"{beat}\t{time:.3f}\t{beat_type}\n")
            
            add_debug_message(f"Generated new tempo map with {len(kept_beats)} beats")
            return temp_file.name
            
        except Exception as e:
            add_debug_message(f"Error generating tempo map: {str(e)}")
            return None 
    
    def process_files(self, score_file: str, tempo_map_file: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Process the score and tempo map files.
        
        Args:
            score_file: Path to the score file
            tempo_map_file: Optional path to tempo map file
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            add_debug_message("\nDebug: Processing Files")
            
            # First, determine timing source
            if tempo_map_file:
                timing_source = "text_tempo_map"
                add_debug_message("\nUsing text tempo map for timing (ignoring score tempo)")
            else:
                # Check if score has tempo changes
                score_has_tempo_changes = self._check_score_tempo_changes(score_file)
                timing_source = "score_tempo_map" if score_has_tempo_changes else "constant_tempo"
                add_debug_message(f"\nUsing {'score tempo changes' if score_has_tempo_changes else 'constant tempo'} for timing")
            
            # Process files based on timing source
            if timing_source == "text_tempo_map":
                # 1. Process text tempo map first (source of truth)
                add_debug_message("\nDebug: Loading tempo map file")
                add_debug_message(f"File path: {tempo_map_file}")
                success, error = self.tempo_map_processor.process_tempo_file(tempo_map_file)
                if not success:
                    return False, f"Failed to process tempo map: {error}"
                
                # Log tempo map details
                add_debug_message(f"\nDebug: Text Tempo Map Analysis")
                add_debug_message(f"Initial offset: {self.tempo_map_processor.initial_offset:.3f}s")
                add_debug_message(f"Total duration: {self.tempo_map_processor.get_total_duration():.3f}s")
                add_debug_message(f"Adjusted duration: {self.tempo_map_processor.get_adjusted_duration():.3f}s")
                add_debug_message(f"Total beats: {self.tempo_map_processor.total_beats}")
                add_debug_message(f"Strong beats (measures): {len(self.tempo_map_processor.strong_beats)}")
                add_debug_message(f"Tempo range: {self.tempo_map_processor.get_tempo_range()}")
                
                # 2. Process score only for structure
                add_debug_message("\nDebug: Loading score file (structure only)")
                success, error = self.score_processor.process_score(
                    score_file,
                    timing_source="text_tempo_map"
                )
                
            elif timing_source == "score_tempo_map":
                # Process score with its tempo changes
                add_debug_message("\nDebug: Loading score file (with tempo changes)")
                success, error = self.score_processor.process_score(
                    score_file,
                    timing_source="score_tempo_map"
                )
                if success:
                    add_debug_message("\nDebug: Score Tempo Analysis")
                    add_debug_message(f"Found {len(self.score_processor.tempo_changes)} tempo changes")
                    add_debug_message(f"Duration: {self.score_processor.get_total_duration():.3f}s")
                
            else:  # constant_tempo
                # Process score with constant tempo
                add_debug_message("\nDebug: Loading score file (constant tempo)")
                success, error = self.score_processor.process_score(
                    score_file,
                    timing_source="constant_tempo"
                )
                if success:
                    add_debug_message("\nDebug: Constant Tempo Analysis")
                    add_debug_message(f"Tempo: {self.score_processor.get_initial_tempo()} BPM")
                    add_debug_message(f"Duration: {self.score_processor.get_total_duration():.3f}s")
            
            if not success:
                return False, f"Failed to process score: {error}"
            
            # Log section analysis
            section_count = len(self.score_processor.sections) if self.score_processor.sections else 0
            add_debug_message(f"\nDebug: Section Analysis")
            add_debug_message(f"Found {section_count} sections")
            
            return True, None
            
        except Exception as e:
            error_msg = f"Error processing files: {str(e)}"
            add_debug_message(f"Debug Error: {error_msg}")
            return False, error_msg 