import streamlit as st
import streamlit.components.v1 as components
import music21
from music21 import converter, stream, tempo, expressions, note, chord, key, analysis
import tempfile
import os
import io
import traceback
import logging
from src.core.debug_utils import add_debug_message, clear_debug_messages, display_debug_messages, initialize_debug
from typing import Union, Tuple, Optional, Dict, Any
from src.core.score_analyzer import ScoreAnalyzer
from src.processors.tempo_map_processor import TempoMapProcessor
from src.processors.text_tempo_processor import TextTempoProcessor
import plotly.graph_objects as go

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class ScoreProcessor:
    """Handles all MusicXML score processing operations"""
    
    def __init__(self):
        self.score = None
        self.tempo_map = None
        self.tempo_changes = []
        self.sections = {}
        self.measure_times = {}
        self.time_signature = None
        self.key_signature = None
        self.analyzer = ScoreAnalyzer()

    def load_tempo_map(self, tempo_map_file: str) -> Tuple[bool, Optional[str]]:
        """Load a tempo map from a MusicXML file.
        
        Args:
            tempo_map_file: Path to the tempo map MusicXML file
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            add_debug_message("\nDebug: Loading tempo map file")
            add_debug_message(f"File path: {tempo_map_file}")
            
            # Load the tempo map score
            self.tempo_map = music21.converter.parse(tempo_map_file)
            if not self.tempo_map:
                error_msg = "Failed to load tempo map: File could not be parsed"
                add_debug_message(error_msg)
                return False, error_msg
            
            # Extract tempo changes
            self.tempo_changes = []
            for measure in self.tempo_map.recurse().getElementsByClass('Measure'):
                measure_number = measure.number
                
                # Look for tempo markings
                for tempo_mark in measure.recurse().getElementsByClass(['MetronomeMark', 'TempoIndication']):
                    tempo = None
                    if hasattr(tempo_mark, 'number'):
                        tempo = tempo_mark.number
                    elif hasattr(tempo_mark, 'bpm'):
                        tempo = tempo_mark.bpm
                    
                    if tempo is None:
                        error_msg = f"Invalid tempo marking found in measure {measure_number}"
                        add_debug_message(error_msg)
                        return False, error_msg
                    
                    self.tempo_changes.append({
                        'measure': measure_number,
                        'tempo': float(tempo)
                    })
            
            if not self.tempo_changes:
                error_msg = "No tempo markings found in tempo map"
                add_debug_message(error_msg)
                return False, error_msg
            
            add_debug_message(f"Successfully loaded tempo map with {len(self.tempo_changes)} tempo changes")
            return True, None
            
        except Exception as e:
            error_msg = f"Error loading tempo map: {str(e)}"
            add_debug_message(f"Debug Error: {error_msg}")
            add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
            return False, error_msg

    def process_score(self, use_tempo_map: bool = False) -> Tuple[bool, Optional[str]]:
        """Process the score to extract timing and section information."""
        try:
            add_debug_message("\nDebug: Processing score")
            
            # Get time signature
            time_analysis = self.analyzer.analyze_time_signature()
            if time_analysis.get('error'):
                return False, time_analysis['error']
            self.time_signature = time_analysis['final']
            add_debug_message(f"Time signature: {self.time_signature}")
            
            # Get key signature
            key_analysis = self.analyzer.analyze_key()
            if key_analysis.get('error'):
                return False, key_analysis['error']
            self.key_signature = key_analysis['final']
            add_debug_message(f"Key signature: {self.key_signature}")
            
            # Get tempo changes
            if use_tempo_map:
                if not self.tempo_changes:
                    return False, "No tempo information available from tempo map"
                add_debug_message("Using tempo changes from tempo map")
            else:
                timing_analysis = self.analyzer.analyze_timing()
                if timing_analysis.get('error'):
                    return False, timing_analysis['error']
                if not timing_analysis.get('tempo_changes'):
                    return False, "No tempo information found in score"
                
                # Use the clean summary instead of raw tempo changes
                if 'summary' in timing_analysis:
                    self.tempo_changes = timing_analysis['summary']['tempo_summary']
                    add_debug_message(f"Using {timing_analysis['summary']['unique_tempo_changes']} unique tempo changes from score")
                else:
                    self.tempo_changes = timing_analysis['tempo_changes']
                    add_debug_message(f"Using {len(self.tempo_changes)} tempo changes from score")
            
            # Calculate measure times
            success, error = self._calculate_measure_times()
            if not success:
                return False, error
            
            # Get sections
            structure_analysis = self.analyzer.analyze_structure()
            if structure_analysis.get('error'):
                return False, structure_analysis['error']
            self.sections = structure_analysis.get('sections', {})
            
            return True, None
            
        except Exception as e:
            error_msg = f"Error processing score: {str(e)}"
            add_debug_message(f"Debug Error: {error_msg}")
            add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
            return False, error_msg

    def _calculate_measure_times(self) -> Tuple[bool, Optional[str]]:
        """Calculate the start and end times for each measure based on tempo changes."""
        try:
            if not self.tempo_changes:
                return False, "No tempo changes available"
            
            self.measure_times = {}
            current_time = 0.0
            current_tempo = self.tempo_changes[0]['tempo']
            tempo_index = 0
            last_effective_tempo = None
            
            # Get all measures
            measures = list(self.analyzer.score.recurse().getElementsByClass('Measure'))
            if not measures:
                return False, "No measures found in score"
            
            # Calculate time for each measure
            for i, measure in enumerate(measures):
                measure_number = measure.number
                
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
                
                # Calculate beats per measure and duration based on time signature type
                if denominator == 8:
                    # Compound time signature (e.g., 6/8, 9/8, 12/8)
                    # In compound time, each dotted quarter note gets one beat
                    # So we divide numerator by 3 to get the number of beats
                    beats_per_measure = numerator / 3
                    
                    # Convert quarter note tempo to dotted quarter note tempo
                    # Dotted quarter = 1.5 * quarter, so we multiply by 2/3 to get the effective tempo
                    effective_tempo = current_tempo * (2/3)
                    
                    # Calculate duration using dotted quarter note beats
                    seconds_per_beat = 60.0 / effective_tempo
                    measure_duration = beats_per_measure * seconds_per_beat
                    
                    add_debug_message(f"Compound Time: Measure {measure_number}")
                    add_debug_message(f"- {numerator}/{denominator} time")
                    add_debug_message(f"- {beats_per_measure} dotted quarter note beats")
                    add_debug_message(f"- Quarter note tempo: {current_tempo} → Dotted quarter tempo: {effective_tempo}")
                    
                elif denominator == 4:
                    # Simple time signature (e.g., 4/4, 3/4)
                    beats_per_measure = numerator
                    effective_tempo = current_tempo
                    seconds_per_beat = 60.0 / effective_tempo
                    measure_duration = beats_per_measure * seconds_per_beat
                    
                else:
                    # Other time signatures (e.g., 2/2, 3/2)
                    # Convert to quarter note equivalent
                    beats_per_measure = numerator * (4 / denominator)
                    effective_tempo = current_tempo * (denominator / 4)
                    seconds_per_beat = 60.0 / effective_tempo
                    measure_duration = beats_per_measure * seconds_per_beat
                
                # Only log tempo conversion if it has changed
                if effective_tempo != last_effective_tempo:
                    if denominator == 8:
                        add_debug_message(f"Measure {measure_number}: Converting quarter note tempo {current_tempo} to dotted quarter note tempo {effective_tempo}")
                    elif current_tempo != effective_tempo:
                        add_debug_message(f"Measure {measure_number}: Converting tempo {current_tempo} to effective tempo {effective_tempo}")
                    last_effective_tempo = effective_tempo
                
                # Store measure timing
                self.measure_times[measure_number] = {
                    'start': current_time,
                    'end': current_time + measure_duration,
                    'duration': measure_duration,
                    'tempo': current_tempo,
                    'effective_tempo': effective_tempo,
                    'time_signature': f"{numerator}/{denominator}",
                    'beats_per_measure': beats_per_measure
                }
                
                current_time += measure_duration
            
            # Add debug information about total duration
            total_duration = current_time
            minutes = int(total_duration // 60)
            seconds = int(total_duration % 60)
            add_debug_message(f"\nScore duration calculated: {minutes}:{seconds:02d}")
            
            # Add detailed timing debug information
            add_debug_message("\nDetailed timing information:")
            add_debug_message(f"Total measures: {len(measures)}")
            add_debug_message(f"Time signature: {self.time_signature}")
            add_debug_message(f"Initial tempo: {self.tempo_changes[0]['tempo']} BPM (quarter notes)")
            if len(self.tempo_changes) > 1:
                add_debug_message(f"Tempo changes: {len(self.tempo_changes)}")
                for change in self.tempo_changes[:3]:  # Show first 3 changes
                    if denominator == 8:
                        effective = change['tempo'] * (2/3)
                        add_debug_message(f"- Measure {change['measure']}: {change['tempo']} BPM (quarter notes) = {effective:.1f} BPM (dotted quarter notes)")
                    else:
                        add_debug_message(f"- Measure {change['measure']}: {change['tempo']} BPM")
                if len(self.tempo_changes) > 3:
                    add_debug_message("...")
            
            return True, None
            
        except Exception as e:
            error_msg = f"Error calculating measure times: {str(e)}"
            add_debug_message(f"Debug Error: {error_msg}")
            add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
            return False, error_msg

    def get_section_timing(self) -> Optional[Dict[str, Dict[str, float]]]:
        """Get timing information for each section."""
        try:
            if not self.sections or not self.measure_times:
                return None
            
            section_timing = {}
            
            for section_name, (start_measure, end_measure) in self.sections.items():
                if start_measure in self.measure_times and end_measure in self.measure_times:
                    section_timing[section_name] = {
                        'start': self.measure_times[start_measure]['start'],
                        'end': self.measure_times[end_measure]['end'],
                        'duration': (self.measure_times[end_measure]['end'] - 
                                   self.measure_times[start_measure]['start']),
                        'start_measure': start_measure,
                        'end_measure': end_measure
                    }
            
            return section_timing
            
        except Exception as e:
            add_debug_message(f"Error getting section timing: {str(e)}")
            add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
            return None

class CommandProcessor:
    """Handles interpretation and validation of user commands"""
    
    def parse_command(self, command_text):
        """Parse user commands like 'remove X, keep Y'"""
        try:
            add_debug_message("\nDebug: Parsing Command")
            add_debug_message(f"Command text: {command_text}")
            
            # Split into actions (remove/keep)
            actions = {}
            for part in command_text.lower().split('.'):
                if 'remove' in part:
                    actions['remove'] = self._extract_sections(part)
                    add_debug_message(f"- Sections to remove: {', '.join(actions['remove'])}")
                elif 'keep' in part:
                    actions['keep'] = self._extract_sections(part)
                    add_debug_message(f"- Sections to keep: {', '.join(actions['keep'])}")
            
            return actions, None
        except Exception as e:
            error_msg = f"Error parsing command: {str(e)}"
            add_debug_message(f"Debug Error: {error_msg}")
            add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
            return None, error_msg
    
    def _extract_sections(self, text):
        """Extract section names from command text"""
        # Remove action words and split by commas/and
        text = text.replace('remove', '').replace('keep', '')
        sections = []
        for part in text.split(','):
            for subpart in part.split('and'):
                section = subpart.strip()
                if section:
                    sections.append(section)
        return sections

class EditPlanner:
    """Plans and validates edit operations"""
    
    def plan_edits(self, timing_info, actions):
        """Plan edits based on command actions"""
        try:
            add_debug_message("\nDebug: Planning Edits")
            
            # Identify consecutive sections
            consecutive_keeps = self._find_consecutive_sections(timing_info, actions.get('keep', []))
            consecutive_removes = self._find_consecutive_sections(timing_info, actions.get('remove', []))
            
            add_debug_message("Consecutive sections to keep:")
            for group in consecutive_keeps:
                add_debug_message(f"- {' + '.join(group)}")
            
            add_debug_message("Consecutive sections to remove:")
            for group in consecutive_removes:
                add_debug_message(f"- {' + '.join(group)}")
            
            # Determine cut points
            cut_points = []
            for section_group in consecutive_removes:
                start_time = timing_info[section_group[0]]['start']
                end_time = timing_info[section_group[-1]]['end']
                cut_points.append({
                    'start': start_time,
                    'end': end_time,
                    'crossfade_before': section_group[0],
                    'crossfade_after': section_group[-1]
                })
                add_debug_message(f"Cut point: {start_time:.2f}s to {end_time:.2f}s")
            
            return cut_points, None
        except Exception as e:
            error_msg = f"Error planning edits: {str(e)}"
            add_debug_message(f"Debug Error: {error_msg}")
            add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
            return None, error_msg
    
    def _find_consecutive_sections(self, timing_info, sections):
        """Find groups of consecutive sections"""
        if not sections:
            return []
        
        # Sort sections by start time
        sorted_sections = sorted(sections, key=lambda x: timing_info[x]['start'])
        
        # Group consecutive sections
        groups = []
        current_group = [sorted_sections[0]]
        
        for i in range(1, len(sorted_sections)):
            current_section = sorted_sections[i]
            prev_section = sorted_sections[i-1]
            
            # Check if sections are consecutive
            if timing_info[current_section]['start'] == timing_info[prev_section]['end']:
                current_group.append(current_section)
            else:
                groups.append(current_group)
                current_group = [current_section]
        
        groups.append(current_group)
        return groups

class MusicEditor:
    """Main application class that coordinates all components"""
    
    def __init__(self):
        """Initialize music editor"""
        self.score_processor = ScoreProcessor()
        self.command_processor = CommandProcessor()
        self.edit_planner = EditPlanner()
        self.text_tempo_processor = None
        self.tempo_map_processor = None
        self.audio_processor = None
        self.using_text_tempo = False
        self.sections = {}
        self.tempo_changes = []
    
    def get_score_data(self):
        """Get the analyzed score data."""
        try:
            if self.score_processor:
                return {
                    'score': self.score_processor.analyzer.score,
                    'time_signature': self.score_processor.time_signature,
                    'key_signature': self.score_processor.key_signature
                }
            return None
        except Exception as e:
            add_debug_message(f"Error getting score data: {str(e)}")
            return None
        
    def get_sections(self):
        """Get section information."""
        try:
            if self.score_processor:
                return self.score_processor.sections
            return None
        except Exception as e:
            add_debug_message(f"Error getting sections: {str(e)}")
            return None
        
    def get_measure_times(self):
        """Get measure timing information."""
        try:
            if self.using_text_tempo and self.text_tempo_processor:
                add_debug_message("\nDebug: Converting text tempo measure times")
                # Convert text tempo measure map to the expected format
                measure_times = {}
                
                # Get time signature from score processor
                time_sig_str = self.score_processor.time_signature
                if not time_sig_str:
                    add_debug_message("Warning: No time signature found, using 4/4")
                    beats_in_measure = 4
                else:
                    try:
                        beats_in_measure = int(time_sig_str.split('/')[0])
                    except:
                        add_debug_message("Warning: Invalid time signature format, using 4/4")
                        beats_in_measure = 4
                
                for measure_num, measure_info in self.text_tempo_processor.measure_map.items():
                    # Validate required keys exist
                    if not all(key in measure_info for key in ['duration', 'real_start_time', 'real_end_time']):
                        add_debug_message(f"Warning: Missing timing info for measure {measure_num}")
                        continue
                        
                    # Calculate tempo based on measure duration
                    duration_minutes = measure_info['duration'] / 60.0
                    tempo = beats_in_measure / duration_minutes
                    
                    measure_times[measure_num] = {
                        'start': measure_info['real_start_time'],  # Use real time with offset
                        'end': measure_info['real_end_time'],      # Use real time with offset
                        'duration': measure_info['duration'],
                        'tempo': tempo,
                        'effective_tempo': tempo,
                        'time_signature': self.score_processor.time_signature or '4/4',
                        'beats_per_measure': beats_in_measure
                    }
                
                add_debug_message(f"Converted {len(measure_times)} measure times")
                if measure_times:
                    first_measure = next(iter(measure_times.values()))
                    add_debug_message(f"First measure timing: start={first_measure['start']:.3f}, end={first_measure['end']:.3f}")
                    add_debug_message(f"First measure tempo: {first_measure['tempo']:.1f} BPM")
                return measure_times
                
            elif self.score_processor:
                add_debug_message("\nDebug: Getting measure times from score processor")
                times = self.score_processor.measure_times
                if times:
                    add_debug_message(f"Found {len(times)} measure times")
                    first_measure = next(iter(times.values()))
                    add_debug_message(f"First measure timing: start={first_measure['start']:.3f}, end={first_measure['end']:.3f}")
                return times
                
            add_debug_message("No measure times available")
            return None
            
        except Exception as e:
            add_debug_message(f"Error getting measure times: {str(e)}")
            add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
            return None
        
    def get_timing_info(self):
        """Get timing information for sections."""
        try:
            if not self.sections:
                add_debug_message("No sections found in get_timing_info")
                return None
                
            timing_info = {}
            
            if self.using_text_tempo and self.text_tempo_processor:
                # Use text tempo timing
                measure_map = self.text_tempo_processor.measure_map
                add_debug_message(f"\nDebug: Building timing info from text tempo")
                add_debug_message(f"Found {len(self.sections)} sections")
                add_debug_message(f"Measure map has {len(measure_map)} measures")
                
                for section_name, (start_measure, end_measure) in self.sections.items():
                    if start_measure in measure_map and end_measure in measure_map:
                        timing_info[section_name] = {
                            'start': measure_map[start_measure]['real_start_time'],
                            'end': measure_map[end_measure]['real_end_time'],
                            'duration': measure_map[end_measure]['real_end_time'] - measure_map[start_measure]['real_start_time'],
                            'start_measure': start_measure,
                            'end_measure': end_measure
                        }
                        add_debug_message(f"Section {section_name}: {timing_info[section_name]}")
            else:
                # Use score timing
                if self.score_processor:
                    add_debug_message("\nDebug: Getting timing info from score processor")
                    return self.score_processor.get_section_timing()
                    
            add_debug_message(f"Returning timing info with {len(timing_info)} sections")
            return timing_info
            
        except Exception as e:
            add_debug_message(f"Error getting timing info: {str(e)}")
            add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
            return None
        
    def get_tempo_data(self):
        """Get tempo data based on the current timing source."""
        try:
            if self.using_text_tempo and self.text_tempo_processor:
                add_debug_message("\nDebug: Getting tempo data from text tempo")
                
                # Get time signature
                try:
                    beats_in_measure = int(self.score_processor.time_signature.split('/')[0])
                except:
                    add_debug_message("Warning: Invalid time signature format, using 4/4")
                    beats_in_measure = 4
                
                # Get tempo changes from text tempo processor
                tempo_changes = []
                for measure_num, measure_info in sorted(self.text_tempo_processor.measure_map.items()):
                    if 'duration' in measure_info and measure_info['duration'] > 0:
                        # Calculate tempo based on beats per minute
                        duration_minutes = measure_info['duration'] / 60.0
                        tempo = beats_in_measure / duration_minutes
                        
                        tempo_changes.append({
                            'measure': measure_num,
                            'tempo': tempo,
                            'dotted_quarter_tempo': tempo * 2/3
                        })
                
                # Convert beat timings to the expected format
                beat_times = []
                for beat, time in self.text_tempo_processor.beat_timings:
                    beat_times.append({
                        'beat': beat,
                        'time': time + self.text_tempo_processor.initial_offset  # Add back the offset
                    })
                
                # Convert measure map to the expected format
                measure_times = {}
                for measure_num, measure_info in self.text_tempo_processor.measure_map.items():
                    # Validate required keys exist
                    if not all(key in measure_info for key in ['duration', 'real_start_time', 'real_end_time', 'start_beat', 'end_beat']):
                        add_debug_message(f"Warning: Missing timing info for measure {measure_num}")
                        continue
                        
                    measure_times[measure_num] = {
                        'start': measure_info['real_start_time'],
                        'end': measure_info['real_end_time'],
                        'duration': measure_info['duration'],
                        'start_beat': measure_info['start_beat'],
                        'end_beat': measure_info['end_beat']
                    }
                
                # Validate we have data
                if not measure_times:
                    add_debug_message("Error: No valid measure times created")
                    return None
                    
                if not beat_times:
                    add_debug_message("Error: No beat times available")
                    return None
                    
                if not tempo_changes:
                    add_debug_message("Error: No tempo changes calculated")
                    return None
                
                result = {
                    'measure_times': measure_times,
                    'beat_times': beat_times,
                    'tempo_changes': tempo_changes,
                    'total_duration': self.text_tempo_processor.total_duration,
                    'initial_offset': self.text_tempo_processor.initial_offset,
                    'source': 'text_tempo_map'
                }
                
                add_debug_message(f"Returning text tempo data:")
                add_debug_message(f"- {len(result['measure_times'])} measure times")
                add_debug_message(f"- {len(result['beat_times'])} beat times")
                add_debug_message(f"- {len(result['tempo_changes'])} tempo changes")
                add_debug_message(f"- Total duration: {result['total_duration']:.3f} seconds")
                add_debug_message(f"- Initial offset: {result['initial_offset']:.3f} seconds")
                add_debug_message(f"- Using {beats_in_measure} beats per measure")
                
                return result
                
            elif self.score_processor:
                add_debug_message("\nDebug: Getting tempo data from score processor")
                result = {
                    'tempo_changes': self.score_processor.tempo_changes,
                    'measure_times': self.score_processor.measure_times,
                    'source': 'score_tempo'
                }
                add_debug_message(f"Returning score tempo data:")
                add_debug_message(f"- {len(result['tempo_changes'])} tempo changes")
                add_debug_message(f"- {len(result['measure_times'])} measure times")
                return result
                
            add_debug_message("No tempo data available")
            return None
            
        except Exception as e:
            add_debug_message(f"Error getting tempo data: {str(e)}")
            add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
            return None
            
    def get_score_tempo_data(self):
        """Get tempo data from the score processor."""
        try:
            if self.score_processor:
                return {
                    'tempo_changes': self.score_processor.tempo_changes,
                    'measure_times': self.score_processor.measure_times,
                    'source': 'score_tempo'
                }
            return None
        except Exception as e:
            add_debug_message(f"Error getting score tempo data: {str(e)}")
            return None
            
    def get_audio_data(self):
        """Get the processed audio data."""
        try:
            if self.audio_processor:
                return self.audio_processor.audio_segment
            return None
        except Exception as e:
            add_debug_message(f"Error getting audio data: {str(e)}")
            return None
        
    def get_audio_duration(self):
        """Get the audio duration in seconds."""
        try:
            if self.audio_processor and self.audio_processor.audio_segment:
                return len(self.audio_processor.audio_segment) / 1000.0
            return None
        except Exception as e:
            add_debug_message(f"Error getting audio duration: {str(e)}")
            return None
            
    def process_files(self, score_file, tempo_file=None):
        """Process uploaded files.
        
        Args:
            score_file: Path to the MusicXML score file
            tempo_file: Optional path to tempo file (text or MusicXML)
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            add_debug_message("\nDebug: Processing Files")
            
            # Load score file
            success, error = self.score_processor.analyzer.load_score(score_file)
            if not success:
                return False, error
            
            # First analyze the score structure
            structure = self.score_processor.analyzer.analyze_structure()
            if structure.get('error'):
                return False, structure['error']
            
            # Store the sections
            self.sections = structure['sections']
            self.score_processor.sections = structure['sections']
            
            if not self.sections:
                return False, "No sections found in score"
            
            # Get time signature first as it's needed for both paths
            time_sig = self.score_processor.analyzer.analyze_time_signature()
            if time_sig.get('error'):
                return False, time_sig['error']
            self.score_processor.time_signature = time_sig['final']
            
            # Get key signature
            key_sig = self.score_processor.analyzer.analyze_key()
            if not key_sig.get('error'):
                self.score_processor.key_signature = key_sig['final']
            
            # Handle tempo information
            if tempo_file:
                # Check if it's a text tempo file
                if str(tempo_file).lower().endswith('.txt'):
                    add_debug_message("\nProcessing text tempo file")
                    # Process as text tempo file
                    success, error = self.process_text_tempo(tempo_file)
                    if not success:
                        return False, error
                    self.using_text_tempo = True
                    
                    # Update score processor's measure times from text tempo
                    measure_times = {}
                    for measure_num, measure_info in self.text_tempo_processor.measure_map.items():
                        # Calculate tempo based on measure duration
                        try:
                            beats_in_measure = int(self.score_processor.time_signature.split('/')[0])
                        except:
                            add_debug_message("Warning: Invalid time signature format, using 4/4")
                            beats_in_measure = 4
                            
                        duration_minutes = measure_info['duration'] / 60.0
                        tempo = beats_in_measure / duration_minutes
                        
                        measure_times[measure_num] = {
                            'start': measure_info['real_start_time'],
                            'end': measure_info['real_end_time'],
                            'duration': measure_info['duration'],
                            'tempo': tempo,
                            'effective_tempo': tempo,
                            'time_signature': self.score_processor.time_signature,
                            'beats_per_measure': beats_in_measure
                        }
                    
                    self.score_processor.measure_times = measure_times
                    add_debug_message("Successfully processed text tempo file")
                else:
                    add_debug_message("\nProcessing MusicXML tempo map")
                    # Process as MusicXML tempo map
                    success, error = self.score_processor.load_tempo_map(tempo_file)
                    if not success:
                        return False, error
                    self.using_text_tempo = False
                    
                    # Process score with tempo map
                    success, error = self.score_processor.process_score(use_tempo_map=True)
                if not success:
                        return False, error
                    
                add_debug_message("Successfully processed MusicXML tempo map")
            else:
                # No tempo file - use score tempo
                add_debug_message("\nUsing score tempo")
                self.using_text_tempo = False
                
                # Process score with its own tempo
                success, error = self.score_processor.process_score(use_tempo_map=False)
                if not success:
                    return False, error
            
            # Verify we have timing information
            if self.using_text_tempo:
                if not self.text_tempo_processor or not self.text_tempo_processor.measure_map:
                    return False, "Failed to get timing information from text tempo file"
                # Verify measure times were created
                if not self.score_processor.measure_times:
                    return False, "Failed to convert text tempo timings"
            else:
                if not self.score_processor.measure_times:
                    return False, "Failed to get timing information from score"
            
            add_debug_message("\nProcessing complete")
            add_debug_message(f"Using timing source: {'text_tempo_map' if self.using_text_tempo else 'score_tempo'}")
            
            return True, None
            
        except Exception as e:
            error_msg = f"Error processing files: {str(e)}"
            add_debug_message(f"Debug Error: {error_msg}")
            add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
            return False, error_msg
    
    def process_text_tempo(self, text_tempo_path: str) -> Tuple[bool, Optional[str]]:
        """Process a text tempo file.
        
        This is a separate path from MusicXML tempo processing.
        It uses the TextTempoProcessor to handle beat-by-beat timing.
        
        Args:
            text_tempo_path: Path to the text tempo file
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            if not text_tempo_path:
                return True, None
            
            # Get time signature from score
            time_sig = self.score_processor.analyzer.analyze_time_signature()
            if time_sig.get('error'):
                return False, f"Error getting time signature: {time_sig['error']}"
            
            # Parse time signature (e.g., "4/4" -> (4, 4))
            try:
                num, denom = map(int, time_sig['final'].split('/'))
                time_signature = (num, denom)
                add_debug_message(f"\nDebug: Using time signature {num}/{denom}")
            except:
                add_debug_message("Warning: Invalid time signature format, using 4/4")
                time_signature = (4, 4)  # Default to 4/4 if parsing fails
            
            # Initialize text tempo processor
            self.text_tempo_processor = TextTempoProcessor()
            success, error = self.text_tempo_processor.process_tempo_file(
                text_tempo_path,
                time_signature=time_signature
            )
            if not success:
                return False, error
            
            # Validate we have the required data
            if not self.text_tempo_processor.beat_timings:
                return False, "No beat timings found in tempo file"
            
            if not self.text_tempo_processor.strong_beats:
                return False, "No strong beats found in tempo file"
            
            if not self.text_tempo_processor.measure_map:
                return False, "Failed to create measure map from tempo file"
            
            # Mark that we're using text tempo timing
            self.using_text_tempo = True
            
            # Clear any existing tempo changes in score processor
            self.score_processor.tempo_changes = []
            
            # Calculate tempo changes from text tempo data
            measure_map = self.text_tempo_processor.measure_map
            tempo_changes = []
            
            for measure_num, measure_info in sorted(measure_map.items()):
                # Validate measure info has required data
                if not all(key in measure_info for key in ['duration', 'real_start_time', 'real_end_time']):
                    add_debug_message(f"Warning: Missing timing info for measure {measure_num}")
                    continue
                    
                # Calculate tempo for this measure
                if measure_info['duration'] > 0:
                    # Calculate tempo based on beats per minute
                    beats_in_measure = time_signature[0]  # numerator from time signature
                    duration_minutes = measure_info['duration'] / 60.0  # convert seconds to minutes
                    tempo = beats_in_measure / duration_minutes
                    
                    tempo_changes.append({
                        'measure': measure_num,
                        'tempo': tempo,
                        'dotted_quarter_tempo': tempo * 2/3
                    })
            
            # Validate we have tempo changes
            if not tempo_changes:
                return False, "Failed to calculate tempo changes from tempo file"
            
            # Store tempo changes for reference
            self.tempo_changes = tempo_changes
            
            add_debug_message(f"\nDebug: Initial offset in text tempo file: {self.text_tempo_processor.initial_offset:.3f} seconds")
            add_debug_message(f"Processed {len(self.text_tempo_processor.beat_timings)} beats")
            add_debug_message(f"Found {len(measure_map)} strong beats (measures)")
            add_debug_message(f"Total duration (adjusted): {self.text_tempo_processor.total_duration:.3f} seconds")
            add_debug_message(f"Mapped {len(measure_map)} measures to exact timings")
            add_debug_message(f"Using {time_signature[0]} beats per measure")
            
            # Log tempo changes
            add_debug_message("\nUpdated tempo changes from text tempo file:")
            add_debug_message(f"Found {len(tempo_changes)} tempo changes")
            if tempo_changes:
                min_tempo = min(c['tempo'] for c in tempo_changes)
                max_tempo = max(c['tempo'] for c in tempo_changes)
                add_debug_message(f"Tempo range: {min_tempo:.1f} - {max_tempo:.1f} BPM")
            
            return True, None
            
        except Exception as e:
            error_msg = f"Error processing text tempo map: {str(e)}"
            add_debug_message(f"Debug Error: {error_msg}")
            add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
            return False, error_msg
    
    def get_section_timing(self, section_name: str) -> Optional[Dict[str, float]]:
        """Get timing information for a section.
        
        This method handles both MusicXML and text tempo timing sources.
        
        Args:
            section_name: Name of the section to get timing for
            
        Returns:
            Dictionary with timing information or None if not found
        """
        if not self.sections or section_name not in self.sections:
            return None
            
        start_measure, end_measure = self.sections[section_name]
        
        if self.using_text_tempo and self.text_tempo_processor:
            # Use text tempo timing
            return self.text_tempo_processor.get_section_timing(start_measure, end_measure)
        else:
            # Use score/MusicXML timing
            return self.score_processor.get_section_timing().get(section_name)
    
    def process_command(self, command_text):
        """Process edit command"""
        try:
            add_debug_message("\nDebug: Processing Command")
            
            # Parse command
            actions, error = self.command_processor.parse_command(command_text)
            if error:
                return None, error
            
            # Get current section timing based on source
            if self.using_text_tempo and self.text_tempo_processor:
                # Use text tempo timing
                timing_info = {}
                for section_name, (start_measure, end_measure) in self.sections.items():
                    section_timing = self.text_tempo_processor.get_section_timing(start_measure, end_measure)
                    if section_timing:
                        timing_info[section_name] = section_timing
                
                if not timing_info:
                    return None, "Failed to calculate section timings from text tempo"
            else:
                # Use score/MusicXML timing
                timing_info = self.score_processor.get_section_timing()
                if not timing_info:
                    return None, "No section timing information available"
            
            # Plan edits
            cut_points, error = self.edit_planner.plan_edits(timing_info, actions)
            if error:
                return None, error
            
            # Validate edits using the same timing source
            if not self._validate_edits(cut_points, timing_info):
                return None, "Invalid edit sequence"
            
            return cut_points, None
            
        except Exception as e:
            error_msg = f"Error processing command: {str(e)}"
            add_debug_message(f"Debug Error: {error_msg}")
            add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
            return None, error_msg
    
    def _validate_edits(self, cut_points, timing_info):
        """Validate that edit sequence maintains synchronization"""
        try:
            # Check for overlapping cuts
            sorted_cuts = sorted(cut_points, key=lambda x: x['start'])
            for i in range(1, len(sorted_cuts)):
                if sorted_cuts[i]['start'] < sorted_cuts[i-1]['end']:
                    add_debug_message(f"Error: Overlapping cuts detected")
                    return False
            
            # Check that all cut points align with measure boundaries
            for cut in cut_points:
                # Verify start point
                if not any(info['start'] == cut['start'] for info in timing_info.values()):
                    add_debug_message(f"Error: Cut start point {cut['start']} does not align with measure boundary")
                    return False
                # Verify end point
                if not any(info['end'] == cut['end'] for info in timing_info.values()):
                    add_debug_message(f"Error: Cut end point {cut['end']} does not align with measure boundary")
                    return False
            
            return True
            
        except Exception as e:
            add_debug_message(f"Error validating edits: {str(e)}")
            return False 