# Test Data Directory

This directory contains test data for the MusicXML and Audio Editor project. The files are organized by song, with each song having its own directory containing all related files.

## Directory Structure

```
test_data/
├── songs/
│   ├── yellow/                  # Coldplay - Yellow (Simple Time)
│   │   ├── yellow_score.xml     # Score file
│   │   ├── yellow_audio.ogg     # Audio file
│   │   └── yellow_tempo.xml     # Tempo map
│   │
│   ├── hallelujah/             # Leonard Cohen - Hallelujah (Simple Time)
│   │   ├── hallelujah_score.xml
│   │   ├── hallelujah_audio.ogg
│   │   └── hallelujah_tempo.xml
│   │
│   ├── perfect/               # Ed Sheeran - Perfect (Compound Time)
│   │   ├── perfect_score.xml
│   │   ├── perfect_audio.ogg
│   │   └── perfect_tempo.xml
│   │
│   └── viva_la_vida/         # Coldplay - Viva la Vida (Mixed Time)
│       ├── viva_la_vida_score.xml
│       ├── viva_la_vida_audio.ogg
│       └── viva_la_vida_tempo.xml
└── README.md
```

## File Types

Each song directory contains:
1. Score Files (*.xml, *.musicxml)
   - MusicXML format
   - Contains musical notation, lyrics, and metadata

2. Audio Files (*.ogg, *.mp3, *.wav)
   - Audio recordings for testing
   - Various formats supported

3. Timing Files (*.xml, *.txt)
   - Tempo maps and timing information
   - Can be in MusicXML or text format

## Time Signatures

The test files cover different time signature types:
- Simple Time (4/4): Yellow, Hallelujah
- Compound Time (6/8): Perfect
- Mixed Time: Viva la Vida

## Usage

When loading files in the application:
1. Select files from the same song directory
2. Load them in this order:
   - Score file first
   - Timing file second (if needed)
   - Audio file last

## Notes

- All files within a song directory are compatible with each other
- Files have been preprocessed and validated
- Each song demonstrates different musical features and editing scenarios 