"""Module for handling audio preview functionality in the UI."""

import streamlit as st
import tempfile
import os
from typing import Dict, Optional

class PreviewUI:
    """Handles audio preview functionality in the UI."""
    
    def __init__(self):
        """Initialize the preview UI components."""
        self.temp_dir = tempfile.mkdtemp()
    
    def render_preview_controls(self, fade_controls: bool = True):
        """Render preview controls including fade options.
        
        Args:
            fade_controls: Whether to show fade in/out controls
        """
        if fade_controls:
            col1, col2 = st.columns(2)
            with col1:
                fade_in = st.checkbox("Apply fade-in (300ms)", value=False)
            with col2:
                fade_out = st.checkbox("Apply fade-out (300ms)", value=False)
            return fade_in, fade_out
        return False, False
    
    def play_preview(self, audio_segment, preview_id: str):
        """Play an audio preview.
        
        Args:
            audio_segment: The audio segment to preview
            preview_id: Unique identifier for this preview
        """
        try:
            # Create temporary file for preview
            preview_path = os.path.join(self.temp_dir, f"preview_{preview_id}.wav")
            audio_segment.export(preview_path, format="wav")
            
            # Play the preview
            st.audio(preview_path)
            
        except Exception as e:
            st.error(f"Failed to play preview: {str(e)}")
    
    def show_preview_info(self, edit_info: Dict):
        """Show information about the preview.
        
        Args:
            edit_info: Dictionary containing edit information
        """
        st.markdown("### Preview Information")
        
        # Show sections to be kept
        if "kept_sections" in edit_info:
            st.write("✅ Sections to keep:")
            for section in edit_info["kept_sections"]:
                st.write(f"  • {section}")
        
        # Show sections to be removed
        if "removed_sections" in edit_info:
            st.write("❌ Sections to remove:")
            for section in edit_info["removed_sections"]:
                st.write(f"  • {section}")
    
    def show_export_options(self):
        """Show export format options."""
        st.markdown("### Export Options")
        
        col1, col2 = st.columns(2)
        with col1:
            wav_export = st.checkbox("Export WAV", value=True)
        with col2:
            ogg_export = st.checkbox("Export OGG", value=True)
        
        return wav_export, ogg_export