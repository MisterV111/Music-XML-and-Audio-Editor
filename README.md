# MusicXML and Audio Editor

A Streamlit-based application for editing and analyzing MusicXML scores and audio files.

## Project Structure

```
MusicXML and Audio Editor/
├── src/                    # Source code
│   ├── core/              # Core functionality (music_editor.py, score_analyzer.py)
│   ├── processors/        # Audio and data processors
│   └── ui/                # User interface (MusicEditorApp.py)
├── tests/                 # Test files
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

3. Run the application:
```bash
streamlit run src/ui/MusicEditorApp.py
```

## Features

Current Features:
- Upload and analyze MusicXML scores and audio files
- Analyze score structure (sections, snippets)
- Display tempo, key signature, and time signature
- Calculate precise timing information
- Support for compound time signatures (e.g., 6/8)
- Debug logging for troubleshooting
- Section editing and rearrangement using OpenAI APIs

Planned Features:
- Audio synchronization
- Snippet management
- Preview and playback
- Export to various formats 