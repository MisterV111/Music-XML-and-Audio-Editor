"""Performance tests for the MusicXML and Audio Editor."""

import unittest
import time
import psutil
import os
from pathlib import Path
import gc

from src.core.music_editor import MusicEditor
from src.processors.audio_processor import AudioProcessor

class TestPerformance(unittest.TestCase):
    """Test cases for performance metrics."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data paths."""
        cls.test_data_dir = Path("tests/test_data")
        cls.songs_dir = cls.test_data_dir / "songs"
        
        # Performance thresholds
        cls.MAX_MEMORY_USAGE = 500 * 1024 * 1024  # 500MB
        cls.MAX_PROCESSING_TIME = 5.0  # 5 seconds
        cls.MAX_AUDIO_LOAD_TIME = 2.0  # 2 seconds

    def setUp(self):
        """Set up each test."""
        self.editor = MusicEditor()
        self.audio_processor = AudioProcessor()
        
        # Clear memory before each test
        gc.collect()
        self.initial_memory = self._get_memory_usage()

    def _get_memory_usage(self):
        """Get current memory usage."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss

    def _measure_memory_increase(self):
        """Measure memory increase from initial state."""
        gc.collect()
        current_memory = self._get_memory_usage()
        return current_memory - self.initial_memory

    def test_audio_loading_performance(self):
        """Test performance of audio loading."""
        test_files = [
            self.songs_dir / "yellow" / "yellow.ogg",
            self.songs_dir / "perfect" / "perfect.ogg",
            self.songs_dir / "viva_la_vida" / "viva_la_vida.ogg"
        ]
        
        for audio_file in test_files:
            # Measure loading time
            start_time = time.time()
            success, error = self.audio_processor.process_audio(str(audio_file))
            load_time = time.time() - start_time
            
            # Assert success and performance
            self.assertTrue(success, f"Failed to load {audio_file}: {error}")
            self.assertLess(load_time, self.MAX_AUDIO_LOAD_TIME,
                          f"Audio loading took too long: {load_time:.2f}s")
            
            # Check memory usage
            memory_increase = self._measure_memory_increase()
            self.assertLess(memory_increase, self.MAX_MEMORY_USAGE,
                          f"Memory usage too high: {memory_increase / 1024 / 1024:.2f}MB")

    def test_score_processing_performance(self):
        """Test performance of score processing."""
        test_files = [
            (self.songs_dir / "yellow" / "yellow_score.xml", None),
            (self.songs_dir / "perfect" / "perfect_score.xml",
             self.songs_dir / "perfect" / "perfect_tempo.xml"),
            (self.songs_dir / "viva_la_vida" / "viva_la_vida_score.xml",
             self.songs_dir / "viva_la_vida" / "viva_la_vida_timing.txt")
        ]
        
        for score_file, timing_file in test_files:
            # Measure processing time
            start_time = time.time()
            if timing_file:
                success, error = self.editor.process_files(str(score_file), str(timing_file))
            else:
                success, error = self.editor.process_files(str(score_file))
            process_time = time.time() - start_time
            
            # Assert success and performance
            self.assertTrue(success, f"Failed to process {score_file}: {error}")
            self.assertLess(process_time, self.MAX_PROCESSING_TIME,
                          f"Score processing took too long: {process_time:.2f}s")
            
            # Check memory usage
            memory_increase = self._measure_memory_increase()
            self.assertLess(memory_increase, self.MAX_MEMORY_USAGE,
                          f"Memory usage too high: {memory_increase / 1024 / 1024:.2f}MB")

    def test_complete_workflow_performance(self):
        """Test performance of complete workflow."""
        # Test with Viva La Vida (most complex case)
        audio_path = self.songs_dir / "viva_la_vida" / "viva_la_vida.ogg"
        score_path = self.songs_dir / "viva_la_vida" / "viva_la_vida_score.xml"
        timing_path = self.songs_dir / "viva_la_vida" / "viva_la_vida_timing.txt"
        
        # Measure total processing time
        start_time = time.time()
        
        # Step 1: Process files
        success, error = self.editor.process_files(str(score_path), str(timing_path))
        self.assertTrue(success, f"Failed to process files: {error}")
        
        # Step 2: Process audio
        success, error = self.audio_processor.process_audio(str(audio_path))
        self.assertTrue(success, f"Failed to process audio: {error}")
        
        # Step 3: Get all necessary data
        self.editor.get_score_data()
        self.editor.get_sections()
        self.editor.get_timing_info()
        self.editor.get_measure_times()
        
        total_time = time.time() - start_time
        
        # Assert performance
        self.assertLess(total_time, self.MAX_PROCESSING_TIME * 2,
                       f"Complete workflow took too long: {total_time:.2f}s")
        
        # Check final memory usage
        memory_increase = self._measure_memory_increase()
        self.assertLess(memory_increase, self.MAX_MEMORY_USAGE * 1.5,
                       f"Total memory usage too high: {memory_increase / 1024 / 1024:.2f}MB")

if __name__ == '__main__':
    unittest.main() 