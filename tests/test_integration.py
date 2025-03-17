"""Integration tests for the complete workflow."""

import unittest
from pathlib import Path
import os

from src.core.music_editor import MusicEditor
from src.processors.audio_processor import AudioProcessor
from src.processors.score_processor import ScoreProcessor

class TestCompleteWorkflow(unittest.TestCase):
    """Test cases for complete workflow integration."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data paths."""
        cls.test_data_dir = Path("tests/test_data")
        cls.songs_dir = cls.test_data_dir / "songs"

    def setUp(self):
        """Set up each test."""
        self.editor = MusicEditor()

    def test_complete_workflow_simple_time(self):
        """Test complete workflow with simple time signature song."""
        # Test with Yellow by Coldplay
        song_dir = self.songs_dir / "yellow"
        audio_path = song_dir / "yellow_audio.ogg"
        score_path = song_dir / "yellow_score.xml"
        
        # Step 1: Process files
        success, error = self.editor.process_files(str(score_path))
        self.assertTrue(success, f"Failed to process files: {error}")
        
        # Step 2: Analyze score
        score_data = self.editor.get_score_data()
        self.assertIsNotNone(score_data)
        
        # Step 3: Get sections
        sections = self.editor.get_sections()
        self.assertIsNotNone(sections)
        self.assertGreater(len(sections), 0)
        
        # Step 4: Get timing information
        timing_info = self.editor.get_timing_info()
        self.assertIsNotNone(timing_info)
        self.assertGreater(len(timing_info), 0)
        
        # Step 5: Process audio
        audio_processor = AudioProcessor()
        success, error = audio_processor.process_audio(str(audio_path))
        self.assertTrue(success, f"Failed to process audio: {error}")
        
        # Step 6: Verify synchronization points
        measure_times = self.editor.get_measure_times()
        self.assertIsNotNone(measure_times)
        self.assertGreater(len(measure_times), 0)

    def test_complete_workflow_compound_time(self):
        """Test complete workflow with compound time signature song."""
        # Test with Perfect by Ed Sheeran
        song_dir = self.songs_dir / "perfect"
        audio_path = song_dir / "perfect_audio.ogg"
        score_path = song_dir / "perfect_score.xml"
        timing_path = song_dir / "perfect_tempo.xml"
        
        # Step 1: Process files with tempo map
        success, error = self.editor.process_files(str(score_path), str(timing_path))
        self.assertTrue(success, f"Failed to process files: {error}")
        
        # Step 2: Verify tempo data
        tempo_data = self.editor.get_tempo_data()
        self.assertIsNotNone(tempo_data)
        self.assertEqual(tempo_data['source'], 'score_tempo')
        
        # Step 3: Process audio
        audio_processor = AudioProcessor()
        success, error = audio_processor.process_audio(str(audio_path))
        self.assertTrue(success, f"Failed to process audio: {error}")
        
        # Step 4: Verify complete workflow data
        self.assertIsNotNone(self.editor.get_score_data())
        self.assertIsNotNone(self.editor.get_sections())
        self.assertIsNotNone(self.editor.get_timing_info())
        self.assertIsNotNone(self.editor.get_measure_times())

    def test_complete_workflow_mixed_time(self):
        """Test complete workflow with mixed time signatures."""
        # Test with Viva La Vida by Coldplay
        song_dir = self.songs_dir / "viva_la_vida"
        audio_path = song_dir / "viva_la_vida_audio.ogg"
        score_path = song_dir / "viva_la_vida_score.xml"
        timing_path = song_dir / "viva_la_vida_timing.txt"
        
        # Step 1: Process files with text tempo map
        success, error = self.editor.process_files(str(score_path), str(timing_path))
        self.assertTrue(success, f"Failed to process files: {error}")
        
        # Step 2: Verify tempo data source
        tempo_data = self.editor.get_tempo_data()
        self.assertIsNotNone(tempo_data)
        self.assertEqual(tempo_data['source'], 'text_tempo_map')
        
        # Step 3: Process audio
        audio_processor = AudioProcessor()
        success, error = audio_processor.process_audio(str(audio_path))
        self.assertTrue(success, f"Failed to process audio: {error}")
        
        # Step 4: Verify timing information
        timing_info = self.editor.get_timing_info()
        self.assertIsNotNone(timing_info)
        
        # Step 5: Verify measure times
        measure_times = self.editor.get_measure_times()
        self.assertIsNotNone(measure_times)
        self.assertGreater(len(measure_times), 0)

if __name__ == '__main__':
    unittest.main() 