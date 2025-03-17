"""Module for handling the editing interface."""

import streamlit as st
import logging
import os
import tempfile
import traceback
from typing import Dict, Optional, List
import plotly.graph_objects as go
import pandas as pd
from src.processors.openai_processor import OpenAIProcessor
from src.processors.audio_processor import AudioProcessor
from src.ui.state_utils import reset_edits

# Configure logger
logger = logging.getLogger(__name__)

def format_duration(seconds):
    """Format duration in seconds to MM:SS format"""
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    return f"{minutes}:{remaining_seconds:02d}"

class EditingUI:
    def __init__(self):
        """Initialize the editing UI components."""
        if 'openai_processor' not in st.session_state:
            st.session_state.openai_processor = OpenAIProcessor()
        if 'audio_processor' not in st.session_state:
            st.session_state.audio_processor = AudioProcessor()
        if 'edit_command_value' not in st.session_state:
            st.session_state.edit_command_value = ""
        
    def render(self, analysis_data: Optional[Dict] = None):
        """Render the editing interface."""
        if analysis_data:
            # Initialize timing_info in session state
            if 'timing_info' not in st.session_state:
                st.session_state.timing_info = analysis_data.get('timing_info', {})
            
            # Create collapsible section for current song information
            with st.expander("Current Song Information", expanded=True):
                self._display_basic_info(analysis_data)
                self.render_song_structure_timeline(analysis_data)
            
            # Get available sections from timing info
            available_sections = [
                section for section in analysis_data.get('timing_info', {}).keys()
                if not any(x in section.lower() for x in ['/snippet', '/endsnippet'])
            ]
            
            # Editing Instructions Section
            st.markdown("## Editing Instructions")
            self.render_editing_section(available_sections)
        else:
            st.warning("Please process your files in the Main tab first to enable editing.")
    
    def _display_basic_info(self, analysis_data):
        """Display basic information about the score."""
        st.markdown("### Basic Information")
        
        # Display key signature
        st.markdown(f"**Key:** {analysis_data['key_info']}")
        
        # Display time signatures with percentages
        time_analysis = analysis_data.get('time_analysis')
        if time_analysis and time_analysis.get('time_signatures'):
            time_sigs = []
            for ts_info in time_analysis['time_signatures']:
                percentage = ts_info.get('percentage', 0)
                time_sigs.append(f"{ts_info['signature']} ({percentage:.1f}%)")
            st.markdown(f"**Time Signature:** {', '.join(time_sigs)}")
        else:
            st.markdown(f"**Time Signature:** {analysis_data['time_signature']}")
        
        # Display tempo and duration
        st.markdown(f"**Average Tempo:** {analysis_data['average_tempo']}")
        st.markdown(f"**Duration:** {format_duration(analysis_data['duration'])}")
        
        if analysis_data['chord_info']:
            st.markdown("**Chords Used:**")
            st.markdown(", ".join(analysis_data['chord_info']))
    
    def render_editing_section(self, available_sections: List[str]):
        """Render the editing interface section."""
        # Initialize session state variables
        if 'process_triggered' not in st.session_state:
            st.session_state.process_triggered = False
        if 'fade_in' not in st.session_state:
            st.session_state.fade_in = False
        if 'fade_out' not in st.session_state:
            st.session_state.fade_out = False
        if 'audio_preview_generated' not in st.session_state:
            st.session_state.audio_preview_generated = False
        if 'timing_info' not in st.session_state:
            st.session_state.timing_info = {}
            
        # Command input with key handler
        command = st.text_area(
            "Enter your editing instructions",
            value=st.session_state.edit_command_value,
            placeholder="Example: 'keep only the chorus and outro' or 'remove verse 2'",
            help="Type your editing instructions in natural language and press Command+Enter (Mac) or Ctrl+Enter (Windows) to process.",
            key="edit_command",
            on_change=self._handle_command_enter
        )
        
        # Update the stored command value
        st.session_state.edit_command_value = command
        
        # Show example commands right after the text area
        with st.expander("See Example Commands"):
            st.markdown(f"""
            ### Example Commands:
            
            **Multiple Instructions:**
            - "remove from Intro to Verse 2, keep from Chorus 2 to Bridge, remove the Outro"
            - "keep from Verse 2 to Bridge, remove everything else"
            
            **Range-based Instructions:**
            - "remove from Intro to Verse 2" (removes Intro, Verse 1, Chorus 1, Interlude 1, and Verse 2)
            - "keep from Verse 2 to Bridge" (keeps Verse 2, Chorus 2, Interlude 2, and Bridge)
            
            **Simple Instructions:**
            - "keep only the chorus and outro"
            - "remove verse 2 and bridge"
            
            **Important Note:**
            When using multiple instructions, "keep" commands are more powerful than "remove" commands.
            For example, in: "remove from Intro to Verse 2, keep Chorus 2"
            - Even though the remove command comes first, Chorus 2 will be kept because "keep" takes priority.
            This makes it easy to protect specific sections you want to keep!
            
            Available sections in your song: {", ".join(available_sections)}
            """)
        
        # Store available sections in session state for the handler
        st.session_state.available_sections = available_sections
        
        # Create two columns for fade controls with equal width
        col1, col2 = st.columns(2)
        with col1:
            st.checkbox("Apply fade-in (using extended bar)", key="fade_in", help="Applies a fade-in effect using the extended bar before the section")
        with col2:
            st.checkbox("Apply fade-out (using extended bar)", key="fade_out", help="Applies a fade-out effect using the extended bar after the section")
        
        # Add some vertical space
        st.write("")
        
        # Process Command button
        if st.button("Process Command"):
            st.session_state.process_triggered = True
        
        # Process the command if triggered
        if st.session_state.process_triggered and st.session_state.edit_command_value:
            result = self._process_command(st.session_state.edit_command_value, available_sections)
            if result:
                st.session_state.last_edit_result = result
            st.session_state.process_triggered = False
        
        # Show Generate Audio Preview button and other controls if command has been processed
        if hasattr(st.session_state, 'last_edit_result') and st.session_state.last_edit_result:
            # Add some space before the Generate Audio Preview button
            st.write("")
            
            # Generate Audio Preview button
            if st.button("Generate Audio Preview"):
                self._generate_audio_preview(st.session_state.last_edit_result)
            
            # Only show audio player and other controls after preview is generated
            if st.session_state.audio_preview_generated:
                # Create a container for the buttons
                button_container = st.container()
                with button_container:
                    # Create two columns for Reset and Export buttons
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        if st.button("Reset Edits"):
                            # Clear the command value
                            st.session_state.edit_command_value = ""
                            # Reset other state
                            from src.ui.state_utils import reset_edits
                            reset_edits()
                    
                    with col2:
                        if st.button("Export Files", type="primary"):
                            self._export_files(st.session_state.last_edit_result)
                
                # Create a separate container for the download section
                if 'show_downloads' not in st.session_state:
                    st.session_state.show_downloads = False
                
                if st.session_state.show_downloads:
                    st.write("")  # Add space before downloads section
                    st.markdown("## Download Your Files")
                    
                    # Create columns for download buttons
                    col1, col2 = st.columns([1, 1])
                    
                    # Audio files in first column
                    with col1:
                        if hasattr(st.session_state, 'wav_data'):
                            st.download_button(
                                label="Download WAV File",
                                data=st.session_state.wav_data,
                                file_name=st.session_state.wav_filename,
                                mime="audio/wav",
                                key="download_wav"
                            )
                        st.write("")  # Add space between buttons
                        if hasattr(st.session_state, 'ogg_data'):
                            st.download_button(
                                label="Download OGG File",
                                data=st.session_state.ogg_data,
                                file_name=st.session_state.ogg_filename,
                                mime="audio/ogg",
                                key="download_ogg"
                            )
                    
                    # Score and Tempo files in second column
                    with col2:
                        st.download_button(
                            label="Download Score File",
                            data=b"",  # Empty bytes for now
                            file_name=f"{st.session_state.wav_filename.replace('.wav', '.musicxml')}",
                            mime="application/vnd.recordare.musicxml+xml",
                            disabled=True,
                            key="download_score"
                        )
                        st.write("")  # Add space between buttons
                        st.download_button(
                            label="Download Tempo Map",
                            data=b"",  # Empty bytes for now
                            file_name=f"{st.session_state.wav_filename.replace('.wav', '_tempo.txt')}",
                            mime="text/plain",
                            disabled=True,
                            key="download_tempo"
                        )
    
    def _render_file_upload_section(self):
        """Render the file upload section of the UI."""
        # Implementation of _render_file_upload_section method
        pass
    
    def _render_editing_instructions(self):
        """Render the editing instructions input section of the UI."""
        # Implementation of _render_editing_instructions method
        pass
    
    def _generate_preview(self):
        """Generate audio preview for the edited sections."""
        # Implementation of _generate_preview method
        pass
    
    def _render_preview_player(self):
        """Render the preview player section of the UI."""
        # Implementation of _render_preview_player method
        pass
    
    def _render_export_controls(self):
        """Render the export controls section of the UI."""
        # Implementation of _render_export_controls method
        pass
    
    def _check_files_processed(self):
        """Check if files are processed."""
        # Implementation of _check_files_processed method
        pass
    
    def _check_preview_available(self):
        """Check if preview is available."""
        # Implementation of _check_preview_available method
        pass
    
    def _handle_command_enter(self):
        """Handle Command+Enter key press event."""
        if st.session_state.edit_command:  # Only trigger if there's text in the input
            st.session_state.process_triggered = True
    
    def _process_command(self, command: str, available_sections: List[str]) -> Optional[Dict]:
        """Process the editing command and display results."""
        # Process the command
        result, message = st.session_state.openai_processor.parse_edit_command(
            command, available_sections
        )
        
        # Display results
        if "error" in result:
            st.error(message)
            return None
        else:
            st.success(message)
            
            # Show preview of changes
            st.subheader("Preview of Changes")
            self._display_edit_preview(result, available_sections)
            
            return result
    
    def _display_edit_preview(self, result: Dict, available_sections: List[str]):
        """Display a preview of the editing changes."""
        action = result["action"]
        sections = result["sections"]
        
        # Create two columns for a more compact display
        col1, col2 = st.columns(2)
        
        # Determine which sections will be kept
        if action == "keep":
            kept_sections = sections
            removed_sections = [s for s in available_sections if s not in sections]
        elif action == "remove":
            kept_sections = [s for s in available_sections if s not in sections]
            removed_sections = sections
        else:  # reorder
            kept_sections = sections
            removed_sections = []
        
            with col1:
                st.markdown("**✅ Keeping:**")
                st.markdown(", ".join(kept_sections))
            with col2:
                st.markdown("**❌ Removing:**")
            st.markdown(", ".join(removed_sections))
    
    def _create_structure_timeline(self, timing_info: Dict) -> go.Figure:
        """Create a timeline visualization of the song structure."""
        # Sort sections by start time
        sorted_sections = sorted(timing_info.items(), key=lambda x: x[1]['start'])
        
        # Prepare data for visualization
        sections = []
        start_times = []
        durations = []
        
        # Modern color scheme
        color_map = {
            'verse': '#4CAF50',      # Vibrant green
            'chorus': '#2196F3',     # Bright blue
            'bridge': '#9C27B0',     # Deep purple
            'intro': '#00BCD4',      # Cyan
            'outro': '#00BCD4',      # Cyan
            'solo': '#FF9800',       # Orange
            'interlude': '#03A9F4'   # Light blue
        }
        
        # Process each section
        for section, info in sorted_sections:
            sections.append(section)
            start_times.append(info['start'])
            durations.append(info['duration'])
        
        # Create figure
        fig = go.Figure()
        
        # Calculate total duration for scaling
        total_duration = max([info['end'] for info in timing_info.values()])
        
        # Add sections as shapes
        for i, (section, start, duration) in enumerate(zip(sections, start_times, durations)):
            # Determine section type and color
            section_type = next((key for key in color_map.keys() if key in section.lower()), 'other')
            color = color_map.get(section_type, '#757575')
            
            # Add section shape
            fig.add_shape(
                type="rect",
                x0=start,
                x1=start + duration,
                y0=0,
                y1=1,
                fillcolor=color,
                line=dict(width=0),
                layer="below"
            )
            
            # Add section label
            fig.add_annotation(
                x=start + duration/2,
                y=0.5,
                text=f"{section}",
                showarrow=False,
                font=dict(
                    size=20,  # Increased font size
                    color='white',
                    family='Arial Black'
                )
            )
        
        # Update layout
        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=200,  # Significantly increased height
            margin=dict(l=10, r=10, t=20, b=10),  # Added small margins for better spacing
            xaxis=dict(
                showgrid=False,
                zeroline=False,
                showline=False,
                showticklabels=False,
                range=[-total_duration*0.01, total_duration*1.01]
            ),
            yaxis=dict(
                showgrid=False,
                zeroline=False,
                showline=False,
                showticklabels=False,
                range=[-0.1, 1.1],
                scaleanchor="x",
                scaleratio=0.2  # Adjusted for better proportions at larger size
            ),
            showlegend=False
        )
        
        return fig
    
    def _generate_audio_preview(self, edit_result):
        """Generate audio preview for the edited sections."""
        try:
            # Show progress message
            progress_msg = st.empty()
            progress_msg.info("Generating audio preview...")
            
            # Validate edit_result
            if not edit_result:
                st.error("No edit result available to generate preview.")
                return
                
            # Validate timing_info
            if 'timing_info' not in st.session_state:
                st.error("No timing information available. Please process your files first.")
                return
                
            timing_info = st.session_state.timing_info
            if not timing_info:
                st.error("Timing information is empty. Please process your files first.")
                return
                
            # Validate audio_processor
            if not hasattr(st.session_state, 'audio_processor'):
                st.error("Audio processor not initialized. Please process your files first.")
                return
                
            # Validate audio data is loaded
            if not st.session_state.audio_processor.audio_segment:
                st.error("No audio data loaded. Please upload an audio file first.")
                return
                
            # Get fade settings
            fade_in = st.session_state.get('fade_in', False)
            fade_out = st.session_state.get('fade_out', False)
                
            # Generate preview
            preview = st.session_state.audio_processor.generate_preview(
                edit_result,
                timing_info,
                fade_in=fade_in,
                fade_out=fade_out
            )
            
            if preview is None:
                st.error("Failed to generate audio preview. Please check your edit instructions.")
                return
                
            # Export preview to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                preview.export(tmp_file.name, format='wav')
                
                # Update progress message
                progress_msg.success("Audio preview generated!")
                
                # Display audio player
                st.audio(tmp_file.name)
                
                # Clean up temporary file
                try:
                    os.unlink(tmp_file.name)
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file: {e}")
                
            # Set flag for successful preview generation
            st.session_state.audio_preview_generated = True
            
        except Exception as e:
            error_msg = f"Error generating preview: {str(e)}"
            logger.error(f"Error: {error_msg}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            st.error(error_msg)
            st.session_state.audio_preview_generated = False
    
    def _export_files(self, result: Dict):
        """Export the edited files."""
        try:
            # Create a temporary directory for exports if it doesn't exist
            if 'export_dir' not in st.session_state:
                st.session_state.export_dir = tempfile.mkdtemp()
            
            export_dir = st.session_state.export_dir
            
            # Get original filename without extension
            original_filename = st.session_state.audio_processor.original_filename
            if not original_filename:
                original_filename = 'edited_audio'
            else:
                # Remove extension if present
                original_filename = os.path.splitext(original_filename)[0]
            
            # Export audio files
            if 'audio_processor' in st.session_state:
                # Export WAV file
                wav_filename = f"{original_filename} (Shortened).wav"
                wav_path = os.path.join(export_dir, wav_filename)
                success, error = st.session_state.audio_processor.export_audio(
                    wav_path, "wav"
                )
                if success:
                    with open(wav_path, 'rb') as f:
                        st.session_state.wav_data = f.read()
                else:
                    st.error(f"Failed to export WAV: {error}")
                
                # Export OGG file
                ogg_filename = f"{original_filename} (Shortened).ogg"
                ogg_path = os.path.join(export_dir, ogg_filename)
                success, error = st.session_state.audio_processor.export_audio(
                    ogg_path, "ogg"
                )
                if success:
                    with open(ogg_path, 'rb') as f:
                        st.session_state.ogg_data = f.read()
                else:
                    st.error(f"Failed to export OGG: {error}")
            
                # Store filenames in session state
                st.session_state.wav_filename = wav_filename
                st.session_state.ogg_filename = ogg_filename
                
                # Show the download section
                st.session_state.show_downloads = True
                
                # Force a rerun to show the download section
                st.rerun()
            
        except Exception as e:
            st.error(f"Error during export: {str(e)}")
    
    def render_song_structure_timeline(self, analysis_data: Dict):
        """Render the song structure timeline."""
        if 'timing_info' in analysis_data:
            st.markdown("### Song Structure Timeline")
            
            # Filter timing info to only include valid sections
            valid_timing_info = {
                section: info for section, info in analysis_data['timing_info'].items()
                if not any(x in section.lower() for x in ['/snippet', '/endsnippet'])
            }
            
            if valid_timing_info:
                # Create section timeline visualization
                sections = []
                durations = []
                colors = []
                
                # Define colors for different section types
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
                
                for section, info in valid_timing_info.items():
                    sections.append(section)
                    durations.append(info['duration'])
                    # Determine section type and assign color
                    section_type = next((st for st in section_colors.keys() 
                                    if st in section.lower()), 'other')
                    colors.append(section_colors.get(section_type, 'rgb(169, 169, 169)'))
                
                # Create timeline visualization
                fig = go.Figure()
                
                for i in range(len(sections)):
                    fig.add_trace(go.Bar(
                        name=sections[i],
                        x=[sections[i]],
                        y=[durations[i]],
                        marker=dict(color=colors[i]),
                        text=f"{format_duration(durations[i])}",
                        textposition='outside',
                        hovertemplate=f"<b>{sections[i]}</b><br>" +
                                    f"Duration: {format_duration(durations[i])}"
                    ))
                
                fig.update_layout(
                    showlegend=False,
                    height=400,
                    xaxis=dict(
                        title="",
                        tickangle=45,
                        tickmode='array',
                        ticktext=sections,
                        tickfont=dict(size=10)
                    ),
                    yaxis=dict(
                        title="Duration (seconds)",
                        range=[0, max(durations) * 1.1]
                    ),
                    margin=dict(l=50, r=20, t=30, b=150),
                    plot_bgcolor='white',
                    bargap=0.3
                )
                
                st.plotly_chart(fig, use_container_width=True) 
    
    def cleanup_preview(self):
        """Clean up temporary preview files."""
        try:
            if ('editing_state' in st.session_state and 
                'preview_audio' in st.session_state.editing_state and 
                st.session_state.editing_state['preview_audio']):
                try:
                    os.remove(st.session_state.editing_state['preview_audio'])
                except:
                    pass
                st.session_state.editing_state['preview_audio'] = None
                st.session_state.audio_preview_generated = False
        except Exception as e:
            logger.error(f"Error cleaning up preview: {str(e)}")
    
    def __del__(self):
        """Destructor to ensure cleanup of temporary files."""
        self.cleanup_preview() 