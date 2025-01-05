"""Utility functions for managing Streamlit state."""

import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

import streamlit as st
import logging
import traceback
from src.core.debug_utils import add_debug_message

def reset_edits() -> bool:
    """Reset all editing-related state while preserving analysis data.
    
    Returns:
        bool: True if reset was successful, False otherwise
    """
    try:
        add_debug_message("\nDebug: Resetting edits")
        
        # Reset editing state
        if 'editing_state' in st.session_state:
            st.session_state.editing_state = {
                'current_edits': [],
                'preview_audio': None,
                'modified_sections': {},
                'edit_history': [],
                'has_changes': False,
                'preview_waveform': None,
                'active_section': None
            }
            add_debug_message("Reset editing state")
        
        # Reset UI state
        if 'last_edit_result' in st.session_state:
            del st.session_state.last_edit_result
        if 'audio_preview_generated' in st.session_state:
            st.session_state.audio_preview_generated = False
        if 'process_triggered' in st.session_state:
            st.session_state.process_triggered = False
            
        # Reset audio processor state if it exists
        if 'audio_processor' in st.session_state:
            # Get original filename before reset
            original_filename = st.session_state.audio_processor.original_filename
            # Reset the processor
            st.session_state.audio_processor.reset()
            # Restore original filename for exports
            st.session_state.audio_processor.original_filename = original_filename
            add_debug_message("Reset audio processor state")
            
            # Check analysis state
            if 'analysis_state' not in st.session_state:
                add_debug_message("No analysis state found")
                return False
                
            analysis_state = st.session_state.analysis_state
            add_debug_message(f"Analysis state keys: {list(analysis_state.keys())}")
            
            # Check audio data
            if 'audio_data' not in analysis_state:
                add_debug_message("No audio data in analysis state")
                return False
                
            audio_data = analysis_state.get('audio_data')
            add_debug_message(f"Audio data type: {type(audio_data)}")
            
            # Check duration
            if 'audio_duration' not in analysis_state:
                add_debug_message("No audio duration in analysis state")
                return False
                
            duration = analysis_state.get('audio_duration')
            add_debug_message(f"Audio duration: {duration}")
            
            # Try to restore audio data
            if audio_data is not None:
                # Try raw audio data first
                if 'raw_audio_data' in analysis_state:
                    add_debug_message("Attempting to restore from raw audio data")
                    success = st.session_state.audio_processor.restore_audio_data(
                        analysis_state['raw_audio_data'],
                        duration
                    )
                    if success:
                        add_debug_message("Restored raw audio data from analysis state")
                    else:
                        # Fallback to AudioSegment
                        add_debug_message("Failed to restore raw audio data, trying AudioSegment")
                        success = st.session_state.audio_processor.restore_audio_data(
                            audio_data,
                            duration
                        )
                        if success:
                            add_debug_message("Restored audio segment from analysis state")
                        else:
                            add_debug_message("Failed to restore audio data")
                else:
                    # Try AudioSegment only
                    add_debug_message("Attempting to restore from AudioSegment")
                    success = st.session_state.audio_processor.restore_audio_data(
                        audio_data,
                        duration
                    )
                    if success:
                        add_debug_message("Restored audio segment from analysis state")
                    else:
                        add_debug_message("Failed to restore audio data")
            else:
                add_debug_message("Audio data is None")
                return False
        
        # Force a rerun to refresh the UI
        st.rerun()
        
        add_debug_message("Reset complete")
        return True
        
    except Exception as e:
        error_msg = f"Error resetting edits: {str(e)}"
        add_debug_message(f"Debug Error: {error_msg}")
        add_debug_message(f"Debug Traceback: {traceback.format_exc()}")
        return False 