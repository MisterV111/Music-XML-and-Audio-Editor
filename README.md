# MusicXML and Audio Editor

A powerful Streamlit-based application designed to edit and analyze MusicXML scores and audio files used during the production of song-based exercises for the Yousican App. This tool enables users to edit audio files using natural language commands—leveraging OpenAI APIs—to request that specific sections of a song be removed or retained, based on the score and tempo information. Users can preview and download the edited audio in both WAV and OGG formats. Future updates will introduce additional features, including tempo slowdown, pitch and key signature adjustments for both audio and score files, and automatic tempo map generation to ensure seamless synchronization in the Yousician App.

## Features

Current Features:
- Upload and analyze MusicXML scores and audio files
- Analyze score structure (sections, snippets)
- Display tempo, key signature, and time signature information
- Calculate precise timing information
- Support for all time signatures (simple, compound, and mixed)
- Section editing and rearrangement using OpenAI APIs with natural language commands
- Audio preview functionality for edits
- Fade in/out effects for audio sections
- Multiple edit versions from a single upload using reset functionality
- Debug logging for troubleshooting

Planned Features:
- Tempo modification (slow down/speed up)
- Key signature and pitch transposition
- Automatic tempo map generation (both MusicXML and text formats)
- Audio synchronization
- Snippet management
- Export to various formats

## Project Structure

```
MusicXML and Audio Editor/
├── src/                    # Source code
│   ├── core/              # Core functionality
│   │   ├── music_editor.py     # Main editing logic
│   │   ├── score_analyzer.py   # Score analysis
│   │   └── debug_utils.py      # Debugging utilities
│   ├── processors/        # Data processors
│   │   ├── audio_processor.py      # Audio processing
│   │   ├── score_processor.py      # Score processing
│   │   ├── section_processor.py    # Section handling
│   │   ├── tempo_map_processor.py  # Tempo processing
│   │   ├── openai_processor.py     # AI integration
│   │   └── ...
│   └── ui/                # User interface
│       ├── MusicEditorApp.py   # Main application
│       ├── editing_ui.py       # Editing interface
│       └── analysis_ui.py      # Analysis interface
├── tests/                 # Test files and sample data
└── Assets/                # Asset files and resources
```

## Setup

1. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure OpenAI API:
   - Create a `.env` file in the root directory
   - Add your OpenAI API key following the format in `.env.example`

4. Run the application:
```bash
streamlit run src/ui/MusicEditorApp.py
```

## File Format Support

- Score Files: MusicXML (.xml, .musicxml)
- Tempo Maps: 
  - MusicXML format (Score Tempo)
  - Text file format (Click Track)
- Audio Files: WAV or OGG formats

## Usage Guide

### Basic Workflow
1. Upload your score file (MusicXML)
2. Upload a tempo map (optional)
3. Upload the corresponding audio file
4. Analyze the files
5. Use natural language commands to edit sections
6. Preview the changes
7. Download the edited version or reset to try different edits

### Section Editing Commands

The application supports natural language commands for section editing. Here are some examples:

#### Multiple Instructions
```
"remove from Intro to Verse 2, keep from Chorus 2 to Bridge, remove the Outro"
"keep from Verse 2 to Bridge, remove everything else"
```

#### Range-based Instructions
```
"remove from Intro to Verse 2"  # Removes Intro, Verse 1, Chorus 1, Interlude 1, and Verse 2
"keep from Verse 2 to Bridge"   # Keeps Verse 2, Chorus 2, Interlude 2, and Bridge
```

#### Simple Instructions
```
"keep only the chorus and outro"
"remove verse 2 and bridge"
```

**Note:** "Keep" commands take priority over "remove" commands. For example, in the command "remove from Intro to Verse 2, keep Chorus 2", Chorus 2 will be preserved regardless of the remove command.

### Sample Files

The project includes test data organized by song, demonstrating different time signatures and editing scenarios:
- Simple Time (4/4): Yellow, Hallelujah
- Compound Time (6/8): Perfect
- Mixed Time: Viva la Vida

Each song includes compatible score files, audio files, and timing information. See the `tests/test_data/README.md` for detailed information about sample files.

## Development

### Dependencies
- Core: pydub, music21, numpy, soundfile
- UI: streamlit, plotly
- AI Integration: openai
- Environment: python-dotenv
- Testing: pytest, pytest-cov, psutil, coverage
- Development: black, flake8, mypy, isort

### Testing
Sample files for testing are provided in the `tests/test_data` directory, organized by song and including various time signatures and editing scenarios.

## Troubleshooting

If you encounter issues:
1. Check the Debug tab in the application for detailed logs
2. Verify file format compatibility
3. Ensure all required files are uploaded in the correct order
4. Confirm OpenAI API key is properly configured

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

[Your Contributing Guidelines Here] 