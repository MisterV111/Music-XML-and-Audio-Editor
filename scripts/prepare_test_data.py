#!/usr/bin/env python3

import os
import shutil
from pathlib import Path

def create_directories():
    """Create the test data directory structure."""
    base_dir = Path("tests/test_data")
    
    # Create song directories
    directories = [
        base_dir / "songs" / "yellow",
        base_dir / "songs" / "hallelujah",
        base_dir / "songs" / "perfect",
        base_dir / "songs" / "viva_la_vida"
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    
    print("\nCreating test data directories...")

def copy_test_files():
    """Copy selected test files to the appropriate directories."""
    print("\nCopying test files...")
    
    # Define source and target paths for each test case
    test_files = {
        'yellow': {
            'score': ("Assets/For testing/Coldplay - Yellow/Coldplay _ Yellow _ Guitar _ HRV _ 8 _ Original Rhythm _ origkey_EABGBD# _ Yousician.xml",
                     "tests/test_data/songs/yellow/yellow_score.xml"),
            'audio': ("Assets/For testing/Coldplay - Yellow/Coldplay _ Yellow _ Full mix _ HRV _ Origkey _ Yousician.ogg",
                     "tests/test_data/songs/yellow/yellow_audio.ogg"),
            'timing': ("Assets/For testing/Coldplay - Yellow/Coldplay _ Yellow _ Tempo map _ HRV.musicxml",
                      "tests/test_data/songs/yellow/yellow_tempo.xml")
        },
        'hallelujah': {
            'score': ("Assets/For testing/Leonard Cohen - Hallelujah/Leonard Cohen _ Hallelujah  Guitar _ AV4 _ 3 _ Advanced Melody _ origkey _ Yousician.xml",
                     "tests/test_data/songs/hallelujah/hallelujah_score.xml"),
            'audio': ("Assets/For testing/Leonard Cohen - Hallelujah/Leonard Cohen _ Hallelujah _ Full mix _ HRV acc _ Yousician.ogg",
                     "tests/test_data/songs/hallelujah/hallelujah_audio.ogg"),
            'timing': ("Assets/For testing/Leonard Cohen - Hallelujah/Leonard Cohen _ Hallelujah _ Tempo map _ HRV.musicxml",
                      "tests/test_data/songs/hallelujah/hallelujah_tempo.xml")
        },
        'perfect': {
            'score': ("Assets/For testing/Ed Sheeran - Perfect/Ed _ Sheeran _ Perfect_ Guitar _ HRV _ 8 _ Advanced Fingerpicking Rhythm and Lead _ origkey _ CAPO 1 _ Yousician.xml",
                     "tests/test_data/songs/perfect/perfect_score.xml"),
            'audio': ("Assets/For testing/Ed Sheeran - Perfect/Ed Sheeran _ Perfect _ Full Mix _ HRV acc _ origkey _ Yousician.ogg",
                     "tests/test_data/songs/perfect/perfect_audio.ogg"),
            'timing': ("Assets/For testing/Ed Sheeran - Perfect/Ed Sheeran _ Perfect _ Tempo map _ HRV.musicxml",
                      "tests/test_data/songs/perfect/perfect_tempo.xml")
        },
        'viva_la_vida': {
            'score': ("Assets/For testing/Coldplay - Viva La Vida/Guitar/Coldplay _ Viva La Vida _ Guitar _ 7 _ Full _ Accompaniment _ HRV acc _ Origkey _ Yousician.xml",
                     "tests/test_data/songs/viva_la_vida/viva_la_vida_score.xml"),
            'audio': ("Assets/For testing/Coldplay - Viva La Vida/bm-Coldplay - Viva La Vida YSRemix nbv-bv-ld.ogg",
                     "tests/test_data/songs/viva_la_vida/viva_la_vida_audio.ogg"),
            'timing': ("Assets/For testing/Coldplay - Viva La Vida/Viva La Vida_click.txt",
                      "tests/test_data/songs/viva_la_vida/viva_la_vida_timing.txt")
        }
    }
    
    # Copy files
    for song_name, song_files in test_files.items():
        for file_type, (src, dst) in song_files.items():
            try:
                if os.path.exists(src):
                    shutil.copy2(src, dst)
                    print(f"Copied {song_name} {file_type}: {dst}")
                else:
                    print(f"Warning: Source file not found: {src}")
            except Exception as e:
                print(f"Error copying {src}: {str(e)}")

def main():
    """Main function to prepare test data."""
    create_directories()
    copy_test_files()
    print("\nTest data preparation complete!")

if __name__ == "__main__":
    main() 