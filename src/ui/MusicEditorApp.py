"""Main application module for the Music Editor."""

import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

import streamlit as st
import logging
import os
import tempfile
import traceback
from typing import Dict, Optional, List
from pydub import AudioSegment
import streamlit.components.v1 as components
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from src.core.music_editor import MusicEditor
from src.core.debug_utils import add_debug_message, clear_debug_messages, display_debug_messages, initialize_debug
from src.ui.editing_ui import EditingUI
from src.ui.analysis_ui import AnalysisUI
from src.ui.state_utils import reset_edits
from src.processors.audio_processor import AudioProcessor

# Initialize persistent analysis state
if 'analysis_state' not in st.session_state:
    st.session_state.analysis_state = {
        'score_data': None,          # Original score analysis
        'tempo_data': None,          # Original tempo information
        'audio_data': None,          # Original audio analysis
        'sections': None,            # Section information
        'measure_times': None,       # Original timing calculations
        'editor': None,              # MusicEditor instance
        'timing_info': None,         # Section timing information
        'audio_duration': None,      # Original audio duration
        'is_analyzed': False         # Flag to track if analysis is complete
    }

# Initialize editing session state
if 'editing_state' not in st.session_state:
    st.session_state.editing_state = {
        'current_edits': [],         # List of applied edits
        'preview_audio': None,       # Current audio preview
        'modified_sections': {},     # Sections being edited
        'edit_history': [],          # History of edit operations
        'has_changes': False,        # Flag to track if there are unsaved changes
        'preview_waveform': None,    # Current waveform visualization
        'active_section': None       # Currently selected section for editing
    }

# Initialize debug state
if 'debug_messages' not in st.session_state:
    st.session_state.debug_messages = []

def format_duration(seconds):
    """Format duration in seconds to MM:SS format"""
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    return f"{minutes}:{remaining_seconds:02d}"

def create_tempo_graph(tempo_changes):
    """Create an interactive tempo graph using Plotly"""
    df = pd.DataFrame(tempo_changes)
    fig = px.line(df, x='measure', y='tempo', 
                  title='Tempo Changes Throughout the Score',
                  labels={'measure': 'Measure Number', 'tempo': 'Tempo (BPM)'},
                  markers=True)
    fig.update_layout(showlegend=False, height=400)
    return fig

def create_section_timeline(timing_info):
    """Create a visual timeline of sections using Plotly"""
    sections = []
    colors = []
    starts = []
    ends = []
    durations = []
    measures = []
    
    # Define consistent colors for section types
    section_colors = {
        'verse': 'rgb(100, 149, 237)',      # Cornflower blue
        'pre-chorus': 'rgb(255, 165, 0)',   # Orange
        'chorus': 'rgb(255, 127, 80)',      # Coral
        'bridge': 'rgb(144, 238, 144)',     # Light green
        'solo': 'rgb(218, 112, 214)',       # Orchid
        'interlude': 'rgb(169, 169, 169)',  # Gray
        'intro': 'rgb(135, 206, 235)',      # Sky blue
        'outro': 'rgb(192, 192, 192)',      # Silver
    }
    
    for section, info in timing_info.items():
        # Create section label with measure numbers
        section_label = f"{section}<br>(Measures {info['start_measure']}-{info['end_measure']})"
        sections.append(section_label)
        starts.append(info['start'])
        ends.append(info['end'])
        durations.append(info['duration'])
        measures.append(f"Measures {info['start_measure']} - {info['end_measure']}")
        
        # Determine section type and assign color
        section_type = next((st for st in section_colors.keys() 
                           if st in section.lower()), 'other')
        colors.append(section_colors.get(section_type, 'rgb(169, 169, 169)'))
    
    fig = go.Figure()
    
    for i in range(len(sections)):
        fig.add_trace(go.Bar(
            name=sections[i],
            x=[sections[i]],  # Section names on x-axis
            y=[durations[i]],  # Duration determines bar height
            marker=dict(color=colors[i]),
            text=f"{format_duration(durations[i])}",
            textposition='outside',
            hovertemplate=f"<b>{sections[i]}</b><br>" +
                         f"Duration: {format_duration(durations[i])}<br>" +
                         f"Start: {format_duration(starts[i])}<br>" +
                         f"End: {format_duration(ends[i])}"
        ))
    
    fig.update_layout(
        title="Song Structure Timeline",
        showlegend=False,
        height=500,
        xaxis=dict(
            title="",
            tickangle=45,  # Angle the section names for better readability
            tickmode='array',
            ticktext=sections,
            tickfont=dict(size=10)  # Adjust font size if needed
        ),
        yaxis=dict(
            title="Duration (seconds)",
            range=[0, max(durations) * 1.1]  # Add 10% padding at the top
        ),
        uniformtext=dict(mode='hide', minsize=8),
        margin=dict(l=50, r=20, t=30, b=150),  # Increased bottom margin for longer labels
        plot_bgcolor='white',
        bargap=0.3
    )
    
    return fig

def save_uploaded_file(uploaded_file):
    """Save uploaded file to a temporary location and return the path"""
    try:
        if not uploaded_file:
            add_debug_message("Error: No file provided to save_uploaded_file")
            return None
            
        add_debug_message(f"\nSaving uploaded file: {uploaded_file.name}")
        
        # Create a temporary file with the same suffix as the uploaded file
        suffix = Path(uploaded_file.name).suffix
        
        # Create temp file and write contents
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            # Get file content as bytes
            file_content = uploaded_file.getvalue()
            if not file_content:
                add_debug_message("Error: Empty file content")
                return None
                
            # Write the content
            tmp_file.write(file_content)
            tmp_file.flush()  # Ensure all data is written
            
            add_debug_message(f"File saved successfully to: {tmp_file.name}")
            add_debug_message(f"File size: {len(file_content)} bytes")
            
            return tmp_file.name
            
    except Exception as e:
        add_debug_message(f"Error saving uploaded file: {str(e)}")
        add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
        return None

def validate_reset_state():
    """Validate that all required states and data are present for reset."""
    try:
        add_debug_message("\nDebug: Starting Reset State Validation")
        
        validation_results = {
            'can_reset': False,
            'has_changes': False,
            'has_editor': False,
            'has_analysis': False,
            'has_timing_source': False,
            'error': None
        }

        # Check if we have an editing state
        add_debug_message("Checking editing state...")
        if 'editing_state' not in st.session_state:
            validation_results['error'] = "No editing state found"
            add_debug_message("Error: No editing state found")
            return validation_results

        # Check if we have changes to reset
        validation_results['has_changes'] = st.session_state.editing_state['has_changes']
        add_debug_message(f"Has changes to reset: {validation_results['has_changes']}")

        # Check if we have an analysis state
        add_debug_message("Checking analysis state...")
        if 'analysis_state' not in st.session_state:
            validation_results['error'] = "No analysis state found"
            add_debug_message("Error: No analysis state found")
            return validation_results

        # Check if we have an editor instance
        add_debug_message("Checking editor instance...")
        validation_results['has_editor'] = (st.session_state.analysis_state['editor'] is not None)
        add_debug_message(f"Has editor instance: {validation_results['has_editor']}")
        if not validation_results['has_editor']:
            validation_results['error'] = "No editor instance found"
            add_debug_message("Error: No editor instance found")
            return validation_results

        # Check timing source consistency
        add_debug_message("Checking timing source...")
        analysis_state = st.session_state.analysis_state
        timing_source = analysis_state.get('timing_source')
        
        if timing_source not in ['text_tempo_map', 'score_tempo']:
            validation_results['error'] = "Invalid timing source"
            add_debug_message(f"Error: Invalid timing source: {timing_source}")
            return validation_results
        
        # Verify timing data matches the source
        if timing_source == 'text_tempo_map':
            if not analysis_state.get('tempo_data'):
                validation_results['error'] = "Missing tempo map data"
                add_debug_message("Error: Missing tempo map data")
                return validation_results
        else:  # score_tempo
            editor = analysis_state['editor']
            if not editor.score_processor.tempo_changes:
                validation_results['error'] = "Missing score tempo data"
                add_debug_message("Error: Missing score tempo data")
                return validation_results
        
        validation_results['has_timing_source'] = True
        add_debug_message(f"Timing source validated: {timing_source}")

        # Check if we have valid analysis data
        add_debug_message("Checking analysis data...")
        validation_results['has_analysis'] = all([
            analysis_state['score_data'] is not None,
            analysis_state['timing_info'] is not None,
            analysis_state['is_analyzed'],
            validation_results['has_timing_source']
        ])
        add_debug_message(f"Has valid analysis data: {validation_results['has_analysis']}")
        
        if not validation_results['has_analysis']:
            validation_results['error'] = "Incomplete analysis data"
            add_debug_message("Error: Incomplete analysis data")
            return validation_results

        # If we reach here, we can reset
        validation_results['can_reset'] = True
        add_debug_message("Validation successful: All checks passed")
        add_debug_message(f"Using timing source: {timing_source}")
        return validation_results

    except Exception as e:
        validation_results['error'] = f"Validation error: {str(e)}"
        add_debug_message(f"Error during validation: {str(e)}")
        add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
        return validation_results

def process_files(score_file, audio_file, tempo_file=None):
    """Process uploaded files and update application state."""
    try:
        # Clear existing analysis state
        st.session_state.analysis_state = {
            'score_data': None,
            'tempo_data': None,
            'audio_data': None,
            'sections': None,
            'measure_times': None,
            'editor': None,
            'timing_info': None,
            'audio_duration': None,
            'is_analyzed': False,
            'timing_source': None
        }
        
        # Clear editing state
        st.session_state.editing_state = {
            'current_edits': [],
            'preview_audio': None,
            'modified_sections': {},
            'edit_history': [],
            'has_changes': False,
            'preview_waveform': None,
            'active_section': None
        }
        
        # Create editor instance
        editor = MusicEditor()
        temp_paths = []
        
        # Save uploaded files
        score_path = save_uploaded_file(score_file)
        if not score_path:
            return False, "Failed to save score file"
        temp_paths.append(score_path)
        add_debug_message(f"Saved score file to: {score_path}")
        
        tempo_path = None
        if tempo_file:
            tempo_path = save_uploaded_file(tempo_file)
            if not tempo_path:
                return False, "Failed to save tempo file"
            temp_paths.append(tempo_path)
            add_debug_message(f"Saved tempo file to: {tempo_path}")
        
        # Process files
        success, error = editor.process_files(score_path, tempo_path)
        if not success:
            return False, error
        
        # Get and validate data
        score_data = editor.get_score_data()
        if not score_data:
            return False, "Failed to get score data"
            
        sections = editor.get_sections()
        if not sections:
            return False, "Failed to get section data"
            
        timing_info = editor.get_timing_info()
        if not timing_info:
            return False, "Failed to get timing information"
            
        measure_times = editor.get_measure_times()
        if not measure_times:
            return False, "Failed to get measure times"
            
        # Get tempo data based on source
        tempo_data = editor.get_tempo_data()
        if not tempo_data:
            return False, "Failed to get tempo data"
        
        # Store analysis data
        st.session_state.analysis_state.update({
            'score_data': score_data,
            'sections': sections,
            'measure_times': measure_times,
            'timing_info': timing_info,
            'tempo_data': tempo_data,
            'timing_source': tempo_data['source'],
            'editor': editor,
            'is_analyzed': True
        })
        
        # Process audio if provided
        if audio_file:
            audio_path = save_uploaded_file(audio_file)
            if not audio_path:
                return False, "Failed to save audio file"
            temp_paths.append(audio_path)
            add_debug_message(f"Saved audio file to: {audio_path}")
            
            # Initialize audio processor in session state
            st.session_state.audio_processor = AudioProcessor()
            success, error = st.session_state.audio_processor.process_audio(
                audio_path,
                original_filename=audio_file.name
            )
            if not success:
                return False, error
                
            audio_data = st.session_state.audio_processor.audio_data
            audio_duration = st.session_state.audio_processor.duration
            
            if audio_data is not None and audio_duration is not None:
                st.session_state.analysis_state.update({
                    'audio_data': audio_data,
                    'audio_duration': audio_duration
                })
            else:
                add_debug_message("Warning: No audio data or duration available")
        else:
            # Clear audio processor if no audio file provided
            if 'audio_processor' in st.session_state:
                del st.session_state.audio_processor
        
        # Clean up temporary files
        for path in temp_paths:
            try:
                os.remove(path)
            except Exception as e:
                add_debug_message(f"Warning: Failed to remove temporary file {path}: {str(e)}")
        
        # Verify analysis state is complete
        required_fields = ['score_data', 'sections', 'measure_times', 'timing_info', 'tempo_data', 'timing_source']
        missing_fields = [field for field in required_fields if st.session_state.analysis_state[field] is None]
        
        if missing_fields:
            add_debug_message(f"Error: Missing required analysis data: {', '.join(missing_fields)}")
            st.session_state.analysis_state['is_analyzed'] = False
            return False, f"Missing required analysis data: {', '.join(missing_fields)}"
        
        # Log the state for debugging
        add_debug_message("\nFinal analysis state:")
        add_debug_message(f"Timing source: {st.session_state.analysis_state['timing_source']}")
        add_debug_message(f"Has score data: {st.session_state.analysis_state['score_data'] is not None}")
        add_debug_message(f"Has sections: {len(st.session_state.analysis_state['sections'])}")
        add_debug_message(f"Has timing info: {len(st.session_state.analysis_state['timing_info'])}")
        add_debug_message(f"Has measure times: {len(st.session_state.analysis_state['measure_times'])}")
        add_debug_message(f"Has tempo data: {st.session_state.analysis_state['tempo_data'] is not None}")
        add_debug_message(f"Analysis complete: {st.session_state.analysis_state['is_analyzed']}")
        
        return True, None
        
    except Exception as e:
        error_msg = f"Error processing files: {str(e)}"
        add_debug_message(f"Debug Error: {error_msg}")
        add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
        st.session_state.analysis_state['is_analyzed'] = False
        return False, error_msg

def main():
    """Main application function"""
    st.title("Music XML and Audio Editor")
    
    # Custom CSS to modify file uploader appearance
    st.markdown("""
        <style>
        .uploadedFile {
            display: none;
        }
        .stFileUploader > div > small {
            display: none;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state if needed
    if 'analysis_state' not in st.session_state:
        st.session_state.analysis_state = {
            'score_data': None,
            'tempo_data': None,
            'audio_data': None,
            'sections': None,
            'measure_times': None,
            'editor': None,
            'timing_info': None,
            'audio_duration': None,
            'is_analyzed': False
        }
    
    if 'editing_state' not in st.session_state:
        st.session_state.editing_state = {
            'current_edits': [],
            'preview_audio': None,
            'modified_sections': {},
            'edit_history': [],
            'has_changes': False,
            'preview_waveform': None,
            'active_section': None
        }
    
    if 'debug_messages' not in st.session_state:
        st.session_state.debug_messages = []
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Main", "Analysis", "Editing", "Debug"])
    
    with tab1:
        # Main content
        st.header("Upload Files")
        
        # Score file upload
        st.markdown("### Score File")
        score_file = st.file_uploader(
            "Upload Score File (MusicXML)",
            type=['xml', 'musicxml'],
            help="Upload your MusicXML score file"
        )

        # Tempo map uploads with clear headers and descriptions
        st.markdown("### Tempo Information")
        st.markdown("Choose one or both tempo sources:")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Option 1: Score Tempo")
            st.markdown("Upload a MusicXML file containing tempo markings from the score.")
            tempo_map_file = st.file_uploader(
                "XML, MUSICXML",
                type=['xml', 'musicxml'],
                key="tempo_map_upload"
            )
            
        with col2:
            st.markdown("#### Option 2: Click Track Tempo")
            st.markdown("Upload a text file containing beat-by-beat timing information.")
            text_tempo_file = st.file_uploader(
                "TXT, TEXT",
                type=['txt', 'text'],
                key="text_tempo_upload"
            )
        
        # Audio file upload
        st.markdown("### Audio File")
        audio_file = st.file_uploader(
            "Upload Audio File",
            type=['mp3', 'wav', 'ogg'],
            help="Upload your audio file"
        )
        
        # Process button
        if st.button("Process Files"):
            if score_file is None:
                st.error("Please upload a score file.")
            else:
                # Clear debug messages
                clear_debug_messages()
                
                # Process files
                success, error = process_files(
                    score_file=score_file,
                    audio_file=audio_file,
                    tempo_file=text_tempo_file or tempo_map_file
                )
                
                if success:
                    st.success("Files processed successfully! For more detailed analysis, go to the Analysis tab.")
                else:
                    st.error(f"Error processing files: {error}")
        
        # Display analysis results if available
        if st.session_state.analysis_state['is_analyzed']:
            st.markdown("---")
            st.markdown("### Analysis Results")
            
            editor = st.session_state.analysis_state['editor']
            if not editor:
                st.error("No editor instance found in session state")
                return
            
            col1, col2 = st.columns(2)
            with col1:
                # Display tempo information based on timing source
                timing_source = st.session_state.analysis_state['timing_source']
                tempo_data = st.session_state.analysis_state['tempo_data']
                
                if timing_source == 'text_tempo_map' and tempo_data:
                    # Display tempo information from text tempo file
                    tempo_changes = tempo_data.get('tempo_changes', [])
                    if tempo_changes:
                        tempos = [change['tempo'] for change in tempo_changes]
                        avg_tempo = sum(tempos) / len(tempos)
                        min_tempo = min(tempos)
                        max_tempo = max(tempos)
                        st.markdown(f"""
                        **Tempo (from Click Track):**
                        - Initial: {tempos[0]:.1f} BPM
                        - Average: {avg_tempo:.1f} BPM
                        - Range: {min_tempo:.1f} - {max_tempo:.1f} BPM
                        """)
                else:
                    # Display tempo information from score processor
                 tempo_changes = editor.score_processor.tempo_changes
                if tempo_changes:
                    tempos = [change['tempo'] for change in tempo_changes]
                    avg_tempo = sum(tempos) / len(tempos)
                    min_tempo = min(tempos)
                    max_tempo = max(tempos)
                    st.markdown(f"""
                        **Tempo (from Score):**
                    - Initial: {tempos[0]:.1f} BPM
                    - Average: {avg_tempo:.1f} BPM
                    - Range: {min_tempo:.1f} - {max_tempo:.1f} BPM
                    """)
                
                # Display time signature
                time_analysis = editor.score_processor.analyzer.analyze_time_signature()
                if time_analysis and not time_analysis.get('error'):
                    if time_analysis.get('time_signatures'):
                        st.markdown("**Time Signatures:**")
                        for ts_info in time_analysis['time_signatures']:
                            # Handle both old and new format
                            if 'ranges' in ts_info:
                                ranges_str = ', '.join(f"{r[0]}-{r[1] or 'end'}" for r in ts_info['ranges'])
                            else:
                                end_measure = ts_info['end_measure'] or 'end'
                                ranges_str = f"{ts_info['start_measure']}-{end_measure}"
                            
                            percentage = ts_info.get('percentage', '')
                            percentage_str = f" ({percentage}%)" if percentage else ''
                            
                            st.markdown(f"- {ts_info['signature']}{percentage_str} Measures {ranges_str}")
                    else:
                        st.markdown(f"**Time Signature:** {time_analysis['final']}")
                
                # Display durations
                if st.session_state.analysis_state['timing_info']:
                    total_duration = max(info['end'] for info in st.session_state.analysis_state['timing_info'].values())
                    st.markdown(f"**Exercise Version Duration:** {format_duration(total_duration)}")
                
                if st.session_state.analysis_state['audio_duration']:
                    st.markdown(f"**Audio Track Duration:** {format_duration(st.session_state.analysis_state['audio_duration'])}")
            
            with col2:
                # Display key signature first
                key_analysis = editor.score_processor.analyzer.analyze_key()
                if key_analysis and key_analysis['final'] != 'Unknown':
                    st.markdown(f"**Key Signature:** {key_analysis['final']}")
                
                # Then display chord analysis
                chord_analysis = editor.score_processor.analyzer.analyze_chord_progression()
                if chord_analysis['unique_chords']:
                    st.markdown("**Chords Used in Exercise:**")
                    unique_chords_list = sorted(list(chord_analysis['unique_chords']))
                    st.markdown(", ".join(unique_chords_list))
                else:
                    st.info("No chord annotations found in this exercise.")

            # Add song structure timeline
            st.markdown("### Song Structure")
            if st.session_state.analysis_state['timing_info']:
                # Filter timing info to only include valid sections
                valid_timing_info = {
                    section: info for section, info in st.session_state.analysis_state['timing_info'].items()
                    if not any(x in section.lower() for x in ['/snippet', '/endsnippet'])
                }
                if valid_timing_info:
                    fig = create_section_timeline(valid_timing_info)
                    st.plotly_chart(fig, use_container_width=True, key="structure_timeline")
            else:
                st.info("Please process your files in the Main tab first to see the analysis.")
    
    with tab2:
        # Analysis tab
        if st.session_state.analysis_state['is_analyzed']:
            editor = st.session_state.analysis_state['editor']
            if not editor:
                st.error("No editor instance found in session state")
                return
            
            # Create two columns for analysis display
            col1, col2 = st.columns(2)
            
            with col1:
                # Audio Analysis
                with st.expander("Audio Analysis", expanded=True):
                    if st.session_state.analysis_state['audio_duration']:
                        audio_duration = st.session_state.analysis_state['audio_duration']
                        score_duration = max(info['end'] for info in st.session_state.analysis_state['timing_info'].values())
                        
                        st.markdown("**Audio Information:**")
                        st.markdown(f"- Audio Duration: {format_duration(audio_duration)}")
                        st.markdown(f"- Score Duration: {format_duration(score_duration)}")
                        
                        # Calculate timing difference
                        diff = abs(audio_duration - score_duration)
                        diff_percentage = (diff / score_duration) * 100
                        
                        st.markdown("**Timing Analysis:**")
                        st.markdown(f"- Difference: {format_duration(diff)} ({diff_percentage:.1f}%)")
                        
                        # Add timing comparison visualization
                        fig = go.Figure()
                        
                        # Add bars for audio and score duration
                        fig.add_trace(go.Bar(
                            name='Audio',
                            x=['Duration'],
                            y=[audio_duration],
                            marker_color='rgb(55, 83, 109)',
                            text=f"{format_duration(audio_duration)}",
                            textposition='auto',
                        ))
                        fig.add_trace(go.Bar(
                            name='Score',
                            x=['Duration'],
                            y=[score_duration],
                            marker_color='rgb(26, 118, 255)',
                            text=f"{format_duration(score_duration)}",
                            textposition='auto',
                        ))
                        
                        fig.update_layout(
                            title="Audio vs Score Duration Comparison",
                            showlegend=True,
                            height=300,
                            bargap=0.15,
                            margin=dict(l=50, r=20, t=50, b=50),
                            yaxis=dict(
                                title="Duration (seconds)",
                                range=[0, max(audio_duration, score_duration) * 1.1]
                            ),
                            plot_bgcolor='white'
                        )
                        
                        st.plotly_chart(fig, use_container_width=True, key="audio_duration_comparison")
                    else:
                        st.info("Please upload an audio file to see the analysis.")
                
                # Tempo Analysis
                with st.expander("Tempo Analysis", expanded=True):
                    timing_source = st.session_state.analysis_state['timing_source']
                    tempo_data = st.session_state.analysis_state['tempo_data']
                    
                    if timing_source == 'text_tempo_map' and tempo_data:
                        tempo_changes = tempo_data.get('tempo_changes', [])
                    else:
                        # Display tempo information from score processor
                        tempo_changes = editor.score_processor.tempo_changes
                        
                    if tempo_changes:
                        # Create DataFrame for tempo changes
                        tempo_df = pd.DataFrame([
                            {'measure': change['measure'], 'tempo': change['tempo']}
                            for change in tempo_changes
                        ])
                        
                        # Display tempo statistics
                        col1_tempo, col2_tempo, col3_tempo = st.columns(3)
                        with col1_tempo:
                            st.metric(
                                label="Initial Tempo",
                                value=f"{tempo_df['tempo'].iloc[0]:.1f} BPM"
                            )
                        with col2_tempo:
                            st.metric(
                                label="Average Tempo",
                                value=f"{tempo_df['tempo'].mean():.1f} BPM"
                            )
                        with col3_tempo:
                            st.metric(
                                label="Tempo Range",
                                value=f"{tempo_df['tempo'].min():.1f} - {tempo_df['tempo'].max():.1f} BPM"
                            )
                        
                        # Create tempo graph
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=tempo_df['measure'],
                            y=tempo_df['tempo'],
                            mode='lines+markers',
                            name='Tempo',
                            line=dict(
                                color='#1f77b4',
                                width=2
                            ),
                            marker=dict(
                                size=6,
                                symbol='circle',
                                color='#1f77b4',
                                line=dict(color='white', width=1)
                            )
                        ))
                        
                        # Calculate y-axis range with padding
                        min_tempo = tempo_df['tempo'].min()
                        max_tempo = tempo_df['tempo'].max()
                        tempo_range = max_tempo - min_tempo
                        padding = max(tempo_range * 0.1, 2)  # At least 2 BPM padding
                        y_min = max(0, min_tempo - padding)
                        y_max = max_tempo + padding
                        
                        fig.update_layout(
                            title=dict(
                                text='Tempo Changes Throughout the Score',
                                x=0.5,
                                y=0.95
                            ),
                            xaxis=dict(
                                title='Measure Number',
                                gridcolor='lightgray',
                                gridwidth=1,
                                showgrid=True,
                                dtick=max(1, round(len(tempo_df)/10))  # Dynamic grid spacing
                            ),
                            yaxis=dict(
                                title='Tempo (BPM)',
                                gridcolor='lightgray',
                                gridwidth=1,
                                showgrid=True,
                                range=[y_min, y_max]
                            ),
                            plot_bgcolor='white',
                            showlegend=False,
                            height=400,
                            margin=dict(l=50, r=20, t=50, b=50)
                        )
                        
                        st.plotly_chart(fig, use_container_width=True, key="tempo_analysis_main")
                    else:
                        st.info("No tempo changes detected in the score.")
                
                # Snippet Analysis
                with st.expander("Snippet Analysis", expanded=True):
                    snippet_analysis = editor.score_processor.analyzer.analyze_snippets()
                    if snippet_analysis['snippets']:
                        # Count snippets by type
                        type_counts = {}
                        total_difficulty = 0
                        for s in snippet_analysis['snippets']:
                            type_counts[s['type']] = type_counts.get(s['type'], 0) + 1
                            total_difficulty += float(s['difficulty'])
                        
                        avg_difficulty = total_difficulty / len(snippet_analysis['snippets'])
                        
                        col1_snip, col2_snip = st.columns(2)
                        with col1_snip:
                            st.markdown(f"**Total Snippets:** {len(snippet_analysis['snippets'])}")
                            st.markdown(f"**Average Difficulty:** {avg_difficulty:.1f}/10")
                        
                        with col2_snip:
                            st.markdown("**Types:**")
                        for snippet_type, count in type_counts.items():
                                st.markdown(f"- {count} {snippet_type}")
                        
                        # Show snippet details
                        show_details = st.checkbox("View Snippet Details", key="snippet_details")
                        if show_details:
                            for snippet in snippet_analysis['snippets']:
                                st.markdown("---")
                                st.markdown(f"""
                                **Type:** {snippet['type']}  
                                **Description:** {snippet['description']}  
                                **Difficulty:** {snippet['difficulty']}  
                                **Measures:** {str(snippet['measure'])}
                                """)
                    else:
                        st.info("No snippets found in the score")
            
            with col2:
                # Structure Analysis
                with st.expander("Structure Analysis", expanded=True):
                    structure_analysis = editor.score_processor.analyzer.analyze_structure()
                    if structure_analysis['sections']:
                        st.markdown("**Sections:**")
                        for section_name, (start, end) in sorted(structure_analysis['sections'].items(), key=lambda x: x[1][0]):
                            st.markdown(f"- **{section_name}:** Measures {start}-{end}")
                    else:
                        st.info("No formal sections identified in the score.")
                
                # Timing Analysis
                with st.expander("Timing Analysis", expanded=True):
                    if st.session_state.analysis_state['timing_info']:
                        # Filter timing info to only include valid sections
                        valid_timing_info = {
                            section: info for section, info in st.session_state.analysis_state['timing_info'].items()
                            if not any(x in section.lower() for x in ['/snippet', '/endsnippet'])
                        }
                        
                        if valid_timing_info:
                            total_duration = max(info['end'] for info in valid_timing_info.values())
                            st.markdown(f"**Total Duration:** {format_duration(total_duration)}")
                            
                            st.markdown("**Section Durations:**")
                            for section, info in sorted(valid_timing_info.items(), key=lambda x: x[1]['start']):
                                duration = info['duration']
                                st.markdown(f"- **{section}:** {format_duration(duration)} (mm. {info['start_measure']}-{info['end_measure']})")

                # Time Signature Information
                with st.expander("Time Signature Information", expanded=True):
                    # Display time signature
                    time_analysis = editor.score_processor.analyzer.analyze_time_signature()
                    if time_analysis and not time_analysis.get('error'):
                        if time_analysis.get('time_signatures'):
                            st.markdown("**Time Signatures:**")
                            for ts_info in time_analysis['time_signatures']:
                                # Handle both old and new format
                                if 'ranges' in ts_info:
                                    ranges_str = ', '.join(f"{r[0]}-{r[1] or 'end'}" for r in ts_info['ranges'])
                                else:
                                    end_measure = ts_info['end_measure'] or 'end'
                                    ranges_str = f"{ts_info['start_measure']}-{end_measure}"
                                
                                percentage = ts_info.get('percentage', '')
                                percentage_str = f" ({percentage}%)" if percentage else ''
                                
                                st.markdown(f"- {ts_info['signature']}{percentage_str} Measures {ranges_str}")
                        else:
                            st.markdown(f"**Time Signature:** {time_analysis['final']}")
                        
                        # Add explanation of time signatures if needed
                        if time_analysis.get('time_signatures'):
                            compound_sigs = [ts for ts in time_analysis['time_signatures'] if ts['signature'].endswith('/8')]
                            if compound_sigs:
                                st.markdown("\n**Note about Compound Time Signatures:**")
                                st.markdown("In compound time signatures (like 6/8, 9/8, 12/8):")
                                st.markdown("- Each dotted quarter note gets one beat")
                                st.markdown("- The top number divided by 3 gives the number of beats per measure")
        else:
            st.info("Please process your files in the Main tab first to see the analysis.")
    
    with tab3:
        # Editing tab
        if st.session_state.analysis_state['is_analyzed']:
            editing_ui = EditingUI()
            # Prepare analysis data
            chord_analysis = st.session_state.analysis_state['editor'].score_processor.analyzer.analyze_chord_progression()
            time_analysis = st.session_state.analysis_state['editor'].score_processor.analyzer.analyze_time_signature()
            
            # Get tempo information based on timing source
            timing_source = st.session_state.analysis_state['timing_source']
            tempo_data = st.session_state.analysis_state['tempo_data']
            
            # Calculate average tempo
            avg_tempo = None
            if timing_source == 'text_tempo_map' and tempo_data:
                tempo_changes = tempo_data.get('tempo_changes', [])
                if tempo_changes:
                    tempos = [change['tempo'] for change in tempo_changes]
                    avg_tempo = sum(tempos) / len(tempos)
            else:
                tempo_changes = st.session_state.analysis_state['editor'].score_processor.tempo_changes
                if tempo_changes:
                    tempos = [change['tempo'] for change in tempo_changes]
                    avg_tempo = sum(tempos) / len(tempos)
            
            analysis_data = {
                'timing_info': st.session_state.analysis_state['timing_info'],
                'tempo_info': st.session_state.analysis_state['editor'].score_processor.time_signature,
                'key_info': st.session_state.analysis_state['editor'].score_processor.analyzer.analyze_key()['final'],
                'time_signature': st.session_state.analysis_state['editor'].score_processor.time_signature,
                'time_analysis': time_analysis,
                'duration': max(info['end'] for info in st.session_state.analysis_state['timing_info'].values()),
                'chord_info': sorted(list(chord_analysis['unique_chords'])) if chord_analysis['unique_chords'] else [],
                'average_tempo': f"{avg_tempo:.1f} BPM" if avg_tempo is not None else "N/A"
            }
            editing_ui.render(analysis_data)
        else:
            st.warning("Please process your files in the Main tab first to enable editing.")
            
    with tab4:
        # Debug tab
        st.markdown("### Debug Messages")
        if st.session_state.debug_messages:
            # Join all messages with newlines and display in a text area
            debug_text = "\n".join(st.session_state.debug_messages)
            st.text_area("Debug Output", value=debug_text, height=400)
            
            # Add a button to clear the debug messages
            if st.button("Clear Debug Messages"):
                clear_debug_messages()
        else:
            st.info("No debug messages available.")

if __name__ == "__main__":
    main() 