"""Unit tests for audio processing functionality."""

import unittest
from pathlib import Path
import os

from src.processors.audio_processor import AudioProcessor
from src.core.music_editor import MusicEditor

class TestAudioProcessing(unittest.TestCase):
    """Test cases for audio processing functionality."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data paths."""
        cls.test_data_dir = Path("tests/test_data")
        cls.songs_dir = cls.test_data_dir / "songs"

    def setUp(self):
        """Set up each test."""
        self.audio_processor = AudioProcessor()
        self.editor = MusicEditor()

    def test_simple_time_signature_processing(self):
        """Test processing audio with simple time signature (4/4)."""
        # Test with Yellow by Coldplay
        song_dir = self.songs_dir / "yellow"
        audio_path = song_dir / "yellow_audio.ogg"
        score_path = song_dir / "yellow_score.xml"
        
        # Test audio loading
        success, error = self.audio_processor.process_audio(str(audio_path))
        self.assertTrue(success, f"Failed to process audio: {error}")
        self.assertIsNotNone(self.audio_processor.audio_data)
        
        # Test audio properties
        self.assertGreater(self.audio_processor.duration, 0)
        self.assertEqual(self.audio_processor.channels, 2)  # Stereo audio
        
        # Test score processing
        success, error = self.editor.process_files(str(score_path))
        self.assertTrue(success, f"Failed to process score: {error}")
        
        # Verify time signature
        time_sig = self.editor.score_processor.time_signature
        self.assertEqual(time_sig, "4/4", "Expected 4/4 time signature")

    def test_compound_time_signature_processing(self):
        """Test processing audio with compound time signature (6/8)."""
        # Test with Perfect by Ed Sheeran
        song_dir = self.songs_dir / "perfect"
        audio_path = song_dir / "perfect_audio.ogg"
        score_path = song_dir / "perfect_score.xml"
        timing_path = song_dir / "perfect_tempo.xml"
        
        # Test audio loading
        success, error = self.audio_processor.process_audio(str(audio_path))
        self.assertTrue(success, f"Failed to process audio: {error}")
        
        # Test score and timing processing
        success, error = self.editor.process_files(str(score_path), str(timing_path))
        self.assertTrue(success, f"Failed to process files: {error}")
        
        # Verify time signature
        time_sig = self.editor.score_processor.time_signature
        self.assertEqual(time_sig, "6/8", "Expected 6/8 time signature")
        
        # Verify tempo map
        tempo_data = self.editor.get_tempo_data()
        self.assertIsNotNone(tempo_data)
        self.assertEqual(tempo_data['source'], 'score_tempo')

    def test_mixed_time_signature_processing(self):
        """Test processing audio with mixed time signatures."""
        # Test with Viva La Vida by Coldplay
        song_dir = self.songs_dir / "viva_la_vida"
        audio_path = song_dir / "viva_la_vida_audio.ogg"
        score_path = song_dir / "viva_la_vida_score.xml"
        timing_path = song_dir / "viva_la_vida_timing.txt"
        
        # Test audio loading
        success, error = self.audio_processor.process_audio(str(audio_path))
        self.assertTrue(success, f"Failed to process audio: {error}")
        
        # Test score and timing processing
        success, error = self.editor.process_files(str(score_path), str(timing_path))
        self.assertTrue(success, f"Failed to process files: {error}")
        
        # Verify timing data
        timing_info = self.editor.get_timing_info()
        self.assertIsNotNone(timing_info)
        
        # Verify tempo data from text file
        tempo_data = self.editor.get_tempo_data()
        self.assertIsNotNone(tempo_data)
        self.assertEqual(tempo_data['source'], 'text_tempo_map')

if __name__ == '__main__':
    unittest.main() 