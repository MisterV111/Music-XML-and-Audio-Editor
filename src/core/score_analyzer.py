import partitura as pt
import music21
from typing import Dict, Optional, Tuple, Union, Any, List
from src.core.debug_utils import add_debug_message
import tempfile
import os
from pathlib import Path
import traceback
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class ScoreAnalyzer:
    def __init__(self):
        self.score = None  # music21 score
        self.partitura_score = None  # partitura score 

    def load_score(self, score_file: str) -> Tuple[bool, Optional[str]]:
        """Load a MusicXML score file using both music21 and partitura.
        
        Args:
            score_file: Path to the MusicXML file
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            add_debug_message("\nDebug: Loading score file")
            add_debug_message(f"File path: {score_file}")
            
            # Load with music21
            self.score = music21.converter.parse(score_file)
            if not self.score:
                return False, "Failed to load score with music21"
            
            # Validate score has parts
            if not self.score.parts:
                return False, "Score contains no parts"
            
            # Validate first part has measures
            if not self.score.parts[0].getElementsByClass('Measure'):
                return False, "First part contains no measures"
            
            # Try to load with partitura, but continue if it fails
            try:
                self.partitura_score = pt.load_musicxml(score_file)
                add_debug_message("Successfully loaded score with both music21 and partitura")
            except Exception as e:
                add_debug_message(f"Warning: Could not load score with partitura: {str(e)}")
                add_debug_message("Continuing with music21 only")
                self.partitura_score = None
            
            return True, None
            
        except Exception as e:
            error_msg = f"Error loading score: {str(e)}"
            add_debug_message(f"Debug Error: {error_msg}")
            add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
            return False, error_msg

    def analyze_structure(self) -> Dict[str, Any]:
        """Analyze the structure of the score, identifying sections and their measure ranges."""
        try:
            if not self.score:
                return {'error': 'No score loaded'}
            
            sections = {}
            current_section = None
            current_start = None
            
            # Define valid section keywords and patterns
            section_keywords = [
                'verse', 'chorus', 'bridge', 'intro', 'outro', 'solo', 
                'pre-chorus', 'interlude', 'refrain', 'coda'
            ]
            
            # Get measures from the first part only, avoiding duplicates
            first_part = self.score.parts[0]
            unique_measures = {}
            measure_count = 0
            for measure in first_part.getElementsByClass('Measure'):
                measure_count += 1
                if measure.number not in unique_measures:
                    unique_measures[measure.number] = measure
            
            # Sort measures by number
            measures = [unique_measures[num] for num in sorted(unique_measures.keys())]
            
            # Add debug information about measure counts
            add_debug_message(f"\nMeasure count analysis in structure:")
            add_debug_message(f"Total measures in first part: {measure_count}")
            add_debug_message(f"Unique measure numbers: {len(unique_measures)}")
            
            # Iterate through measures
            for measure in measures:
                measure_number = measure.number
                
                # Look for section markers
                for expression in measure.recurse().getElementsByClass(['TextExpression', 'RehearsalMark']):
                    text = expression.content if hasattr(expression, 'content') else str(expression)
                    text_lower = text.lower().strip()
                    
                    # Skip snippet annotations and empty text
                    if not text_lower or any(x in text_lower for x in ['/snippet', '/endsnippet']):
                        continue
                    
                    # Skip if text contains chord-like characters
                    if any(x in text for x in ['7', '9', 'maj', 'min', 'm7', 'dim', 'aug', 'sus']):
                        continue
                    
                    # Check if this is a valid section marker
                    is_section = any(
                        keyword in text_lower and (
                            keyword == text_lower or  # Exact match
                            text_lower.startswith(f"{keyword} ") or  # Keyword with number/modifier
                            text_lower.endswith(f" {keyword}") or
                            f" {keyword} " in text_lower
                        )
                        for keyword in section_keywords
                    )
                    
                    if is_section:
                        # If we found a new section and had a previous one
                        if current_section:
                            sections[current_section] = (current_start, measure_number - 1)
                        
                        current_section = text
                        current_start = measure_number
            
            # Handle the last section
            if current_section:
                last_measure = max(m.number for m in measures)
                sections[current_section] = (current_start, last_measure)
            
            # Add debug information
            add_debug_message(f"\nFound {len(measures)} unique measures in structure analysis")
            add_debug_message(f"Found {len(sections)} sections")
            
            return {'sections': sections}
            
        except Exception as e:
            add_debug_message(f"Error analyzing structure: {str(e)}")
            add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
            return {'error': f"Failed to analyze structure: {str(e)}"}

    def analyze_timing(self, skip_duration_calc: bool = False) -> Dict[str, Any]:
        """Analyze tempo and timing information in the score.
        
        Args:
            skip_duration_calc: Whether to skip duration calculation (when using tempo map)
            
        Returns:
            Dictionary with timing analysis results
        """
        try:
            if not self.score:
                return {'error': 'No score loaded'}
            
            # Get measures from the first part only
            first_part = self.score.parts[0]
            unique_measures = {}
            measure_count = 0
            
            # Only process measures from the first part
            for measure in first_part.getElementsByClass('Measure'):
                measure_count += 1
                if measure.number not in unique_measures:
                    unique_measures[measure.number] = measure
            
            # Sort measures by number
            measures = [unique_measures[num] for num in sorted(unique_measures.keys())]
            
            if not measures:
                return {'error': 'No measures found in score'}
            
            # Add debug information about measure counts
            add_debug_message(f"\nMeasure count analysis in timing:")
            add_debug_message(f"Total measures in first part: {measure_count}")
            add_debug_message(f"Unique measure numbers: {len(unique_measures)}")
            
            # If skipping duration calculation, just return measure count
            if skip_duration_calc:
                return {
                    'total_measures': len(measures),
                    'error': None
                }
            
            # Initialize tempo tracking
            tempo_changes = []
            current_tempo = None
            
            # First look for initial tempo marking
            first_measure = measures[0]
            for element in first_measure.recurse():
                if 'TempoIndication' in element.classes or 'MetronomeMark' in element.classes:
                    if hasattr(element, 'number'):
                        current_tempo = float(element.number)
                        break
                    elif hasattr(element, 'bpm'):
                        current_tempo = float(element.bpm)
                        break
            
            # If no initial tempo found, try to get it from the score
            if current_tempo is None:
                mm = self.score.metronomeMarkBoundaries()
                if mm and mm[0] and mm[0][2]:
                    current_tempo = float(mm[0][2].number)
                else:
                    # Default tempo if none found
                    current_tempo = 80.0
            
            # Add initial tempo
            tempo_changes.append({
                'measure': 1,
                'tempo': current_tempo,
                'dotted_quarter_tempo': current_tempo * 2/3
            })
            
            # Look for tempo changes in subsequent measures
            for measure in measures[1:]:
                measure_number = measure.number
                tempo_found = False
                
                for element in measure.recurse():
                    if 'TempoIndication' in element.classes or 'MetronomeMark' in element.classes:
                        tempo = None
                        if hasattr(element, 'number'):
                            tempo = float(element.number)
                        elif hasattr(element, 'bpm'):
                            tempo = float(element.bpm)
                        
                        if tempo is not None and tempo != current_tempo:
                            current_tempo = tempo
                            tempo_changes.append({
                                'measure': measure_number,
                                'tempo': current_tempo,
                                'dotted_quarter_tempo': current_tempo * 2/3
                            })
                            tempo_found = True
                            break
            
            # Create summary
            unique_tempos = set(change['tempo'] for change in tempo_changes)
            summary = {
                'total_measures': len(measures),
                'unique_tempo_changes': len(unique_tempos),
                'tempo_summary': tempo_changes
            }
            
            add_debug_message(f"Found {len(measures)} unique measures in tempo analysis")
            add_debug_message(f"Found {len(tempo_changes)} tempo changes")
            
            # Add debug information about tempo analysis
            add_debug_message("\nTempo analysis details:")
            add_debug_message(f"Initial tempo: {tempo_changes[0]['tempo']} BPM")
            add_debug_message(f"Total unique tempos: {len(unique_tempos)}")
            add_debug_message(f"Total tempo changes: {len(tempo_changes)}")
            
            return {
                'tempo_changes': tempo_changes,
                'summary': summary,
                'error': None
            }
            
        except Exception as e:
            error_msg = f"Error analyzing timing: {str(e)}"
            add_debug_message(f"Debug Error: {error_msg}")
            add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
            return {'error': error_msg}

    def analyze_key(self) -> Dict[str, Any]:
        """Analyze the key signature of the score."""
        try:
            if not self.score:
                return {'error': 'No score loaded'}
            
            # Get first part
            first_part = self.score.parts[0]
            
            # Get unique measures
            unique_measures = {}
            for measure in first_part.getElementsByClass('Measure'):
                if measure.number not in unique_measures:
                    unique_measures[measure.number] = measure
            
            # Get key signature from first measure
            first_measure = unique_measures[1]  # Measure numbers are 1-indexed
            key_sig = first_measure.keySignature
            
            if key_sig:
                key_name = str(key_sig.asKey())
                # Replace '-' with 'b' for flats
                key_name = key_name.replace('-', 'b')
                return {'final': key_name, 'error': None}
            
            return {'final': 'Unknown', 'error': 'No key signature found'}
            
        except Exception as e:
            error_msg = f"Error analyzing key signature: {str(e)}"
            add_debug_message(f"Debug Error: {error_msg}")
            add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
            return {'final': 'Unknown', 'error': error_msg}

    def analyze_time_signature(self) -> Dict[str, Any]:
        """Analyze the time signature of the score.
        
        Returns:
            Dictionary containing:
            - final: The most common time signature (for backward compatibility)
            - time_signatures: List of dicts with time signatures and their measure ranges
            - has_countdown: Whether there's a countdown measure
            - error: Error message if any
        """
        try:
            if not self.score:
                return {'error': 'No score loaded'}
            
            # Check for countdown measure
            countdown_info = self.has_countdown_measure()
            if countdown_info['has_countdown']:
                # Use the main time signature from measure 2
                return {
                    'final': countdown_info['main_time_signature'],
                    'time_signatures': [{
                        'signature': countdown_info['main_time_signature'],
                        'start_measure': 2,
                        'end_measure': None,  # Until the end
                        'ranges': [(2, None)],
                        'percentage': 100.0
                    }],
                    'has_countdown': True,
                    'error': None
                }
            
            # Get measures from first part only
            first_part = self.score.parts[0]
            time_signatures = []
            current_ts = None
            ts_start_measure = None
            
            # Get unique measures
            unique_measures = {}
            for measure in first_part.getElementsByClass('Measure'):
                if measure.number not in unique_measures:
                    unique_measures[measure.number] = measure
            
            # Sort measures by number
            sorted_measures = [unique_measures[num] for num in sorted(unique_measures.keys())]
            total_measures = len(sorted_measures)
            
            # Track time signature changes
            ts_ranges = []
            for measure in sorted_measures:
                measure_number = measure.number
                found_ts = False
                
                for ts in measure.recurse().getElementsByClass('TimeSignature'):
                    found_ts = True
                    new_ts = f"{ts.numerator}/{ts.denominator}"
                    
                    if new_ts != current_ts:
                        # Close previous range if exists
                        if current_ts and ts_start_measure:
                            ts_ranges.append({
                                'signature': current_ts,
                                'start_measure': ts_start_measure,
                                'end_measure': measure_number - 1
                            })
                        
                        # Start new range
                        current_ts = new_ts
                        ts_start_measure = measure_number
                    
                    time_signatures.append(new_ts)
                    break
            
            # Close final range
            if current_ts and ts_start_measure:
                ts_ranges.append({
                    'signature': current_ts,
                    'start_measure': ts_start_measure,
                    'end_measure': sorted_measures[-1].number
                })
            
            if not time_signatures:
                return {'error': 'No time signature found in score'}
            
            # Group ranges by time signature and calculate percentages
            ts_groups = {}
            for ts_range in ts_ranges:
                sig = ts_range['signature']
                if sig not in ts_groups:
                    ts_groups[sig] = {
                        'signature': sig,
                        'ranges': [],
                        'measure_count': 0
                    }
                
                range_tuple = (ts_range['start_measure'], ts_range['end_measure'])
                ts_groups[sig]['ranges'].append(range_tuple)
                ts_groups[sig]['measure_count'] += (ts_range['end_measure'] - ts_range['start_measure'] + 1)
            
            # Calculate percentages and format final output
            final_ts_groups = []
            for sig, group in ts_groups.items():
                percentage = (group['measure_count'] / total_measures) * 100
                final_ts_groups.append({
                    'signature': sig,
                    'ranges': group['ranges'],
                    'percentage': round(percentage, 1)
                })
            
            # Sort by first occurrence
            final_ts_groups.sort(key=lambda x: x['ranges'][0][0])
            
            # Use the most common time signature as 'final' for backward compatibility
            final_ts = max(ts_groups.items(), key=lambda x: x[1]['measure_count'])[0]
            
            add_debug_message("\nTime Signature Analysis:")
            add_debug_message(f"Found {len(final_ts_groups)} different time signatures")
            for group in final_ts_groups:
                ranges_str = ', '.join(f"{r[0]}-{r[1] or 'end'}" for r in group['ranges'])
                add_debug_message(f"- {group['signature']} ({group['percentage']}%) measures {ranges_str}")
            
            return {
                'final': final_ts,
                'time_signatures': final_ts_groups,
                'has_countdown': False,
                'error': None
            }
            
        except Exception as e:
            error_msg = f"Error analyzing time signature: {str(e)}"
            add_debug_message(f"Debug Error: {error_msg}")
            add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
            return {'error': error_msg}

    def analyze_chord_progression(self) -> Dict[str, Any]:
        """Analyze the chord progression in the score."""
        try:
            # Initialize variables
            chord_progression = []
            unique_chords = set()
            
            # Get measures from first part only
            first_part = self.score.parts[0]
            
            # Get all chord symbols from the first part
            for element in first_part.recurse():
                chord_text = None
                
                # Handle different types of chord elements
                if 'ChordSymbol' in element.classes:
                    if hasattr(element, 'figure'):
                        chord_text = element.figure
                    elif hasattr(element, 'root'):
                        # Build chord name from root and kind
                        chord_text = str(element.root().name)
                        if element.quality:
                            chord_text += element.quality
                elif 'ChordWithFretBoard' in element.classes:
                    if hasattr(element, 'chord') and hasattr(element.chord, 'commonName'):
                        chord_text = element.chord.commonName
                    elif hasattr(element, 'chord') and hasattr(element.chord, 'pitches'):
                        # Get root note of the chord
                        root = element.chord.root()
                        if root:
                            chord_text = root.name
                
                if chord_text:
                    # Clean up the chord text
                    chord_text = (chord_text
                                .replace('-', 'b')  # Replace hyphens with 'b' for flats
                                .replace('♭', 'b')  # Replace flat symbol with 'b'
                                .replace('♯', '#')  # Replace sharp symbol with '#'
                                .replace('power', '5')  # Replace "power" with "5" for power chords
                                .strip())
                    
                    # Skip if the chord text is empty or invalid
                    if not chord_text.startswith('<') and not chord_text.startswith('music21'):
                        chord_progression.append(chord_text)
                        unique_chords.add(chord_text)
            
            # Create summary
            if chord_progression:
                summary = f"Found {len(chord_progression)} chord symbols with {len(unique_chords)} unique chords."
            else:
                summary = "No chord symbols found in the score."
            
            return {
                'progression': chord_progression,
                'unique_chords': list(unique_chords),
                'summary': summary,
                'error': None
            }
            
        except Exception as e:
            error_msg = f"Error analyzing chord progression: {str(e)}"
            add_debug_message(f"Debug Error: {error_msg}")
            add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
            return {'error': error_msg}

    def analyze_snippets(self) -> Dict[str, Any]:
        """Analyze snippets marked in the score."""
        try:
            if not self.score:
                return {'error': 'No score loaded'}
            
            snippets = []
            current_snippet = None
            
            # Get measures from first part only
            first_part = self.score.parts[0]
            unique_measures = {}
            for measure in first_part.getElementsByClass('Measure'):
                if measure.number not in unique_measures:
                    unique_measures[measure.number] = measure
            
            # Sort measures by number
            measures = [unique_measures[num] for num in sorted(unique_measures.keys())]
            
            # Iterate through measures
            for measure in measures:
                measure_number = measure.number
                
                # Look for snippet markers
                for expression in measure.recurse().getElementsByClass(['TextExpression', 'RehearsalMark']):
                    text = expression.content if hasattr(expression, 'content') else str(expression)
                    
                    # Check for snippet start
                    if '/snippet' in text.lower():
                        # Parse snippet information
                        # Format: /snippet type;description;difficulty
                        parts = text.split(';')
                        if len(parts) >= 3:
                            current_snippet = {
                                'type': parts[0].replace('/snippet', '').strip(),
                                'description': parts[1].strip(),
                                'difficulty': parts[2].strip(),
                                'start_measure': measure_number
                            }
                    
                    # Check for snippet end
                    elif '/endsnippet' in text.lower() and current_snippet:
                        current_snippet['measure'] = f"{current_snippet['start_measure']}-{measure_number}"
                        snippets.append(current_snippet)
                        current_snippet = None
            
            # Handle any unclosed snippets
            if current_snippet:
                last_measure = max(m.number for m in measures)
                current_snippet['measure'] = f"{current_snippet['start_measure']}-{last_measure}"
                snippets.append(current_snippet)
            
            return {'snippets': snippets}
            
        except Exception as e:
            error_msg = f"Error analyzing snippets: {str(e)}"
            add_debug_message(f"Debug Error: {error_msg}")
            add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
            return {'error': error_msg}

    def has_countdown_measure(self) -> Dict[str, Any]:
        """Detect if score starts with a special countdown measure.
        
        Returns:
            Dictionary containing:
            - has_countdown: Whether the score has a countdown measure
            - countdown_beats: Number of countdown beats (if applicable)
            - main_time_signature: The actual time signature of the piece
            - error: Error message if any
        """
        try:
            if not self.score:
                return {
                    'has_countdown': False,
                    'error': 'No score loaded'
                }
            
            # Get measures from first part only
            first_part = self.score.parts[0]
            unique_measures = {}
            for measure in first_part.getElementsByClass('Measure'):
                if measure.number not in unique_measures:
                    unique_measures[measure.number] = measure
            
            # Sort measures by number
            measures = [unique_measures[num] for num in sorted(unique_measures.keys())]
            
            if len(measures) < 2:
                return {
                    'has_countdown': False,
                    'error': None
                }
            
            # Get time signatures of first two measures
            first_ts = None
            second_ts = None
            
            for ts in measures[0].recurse().getElementsByClass('TimeSignature'):
                first_ts = ts
                break
                
            for ts in measures[1].recurse().getElementsByClass('TimeSignature'):
                second_ts = ts
                break
            
            if not first_ts or not second_ts:
                return {
                    'has_countdown': False,
                    'error': None
                }
            
            # Check if first measure is 9/4 (or similar) and second is different
            is_countdown = (
                first_ts.numerator == 9 and 
                first_ts.denominator == 4 and
                second_ts.numerator != first_ts.numerator
            )
            
            if is_countdown:
                return {
                    'has_countdown': True,
                    'countdown_beats': 5,  # 1 beat silence + 4 beats countdown
                    'main_time_signature': f"{second_ts.numerator}/{second_ts.denominator}",
                    'error': None
                }
            
            return {
                'has_countdown': False,
                'error': None
            }
            
        except Exception as e:
            return {
                'has_countdown': False,
                'error': f"Error detecting countdown measure: {str(e)}"
            } 

    def process_score(self, score_file: str, skip_tempo_analysis: bool = False) -> Tuple[bool, Optional[str]]:
        """Process a score file for analysis.
        
        Args:
            score_file: Path to the score file
            skip_tempo_analysis: Whether to skip tempo analysis (when using tempo map)
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Load and parse score
            success, error = self._load_score(score_file)
            if not success:
                return False, error
            
            # Always analyze structure (needed for sections)
            success, error = self._analyze_structure()
            if not success:
                return False, error
            
            # Skip tempo analysis if using tempo map
            if not skip_tempo_analysis:
                success, error = self._analyze_tempo()
                if not success:
                    return False, error
                
                # Calculate duration based on tempo
                success, error = self._calculate_duration()
                if not success:
                    return False, error
            
            return True, None
            
        except Exception as e:
            error_msg = f"Error processing score: {str(e)}"
            logger.error(error_msg)
            return False, error_msg 