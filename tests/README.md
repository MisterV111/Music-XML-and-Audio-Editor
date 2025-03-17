# Testing Guide

This directory contains the test suite for the MusicXML and Audio Editor project. The tests are organized to cover different aspects of the application, from unit tests to integration and performance tests.

## Test Structure

```
tests/
├── test_data/               # Test data directory
│   ├── songs/              # Song-specific test files
│   │   ├── yellow/         # Coldplay - Yellow (4/4)
│   │   ├── hallelujah/     # Leonard Cohen - Hallelujah (4/4)
│   │   ├── perfect/        # Ed Sheeran - Perfect (6/8)
│   │   └── viva_la_vida/   # Coldplay - Viva la Vida (Mixed)
│   └── README.md           # Test data documentation
├── test_audio_processing.py # Unit tests for audio processing
├── test_integration.py     # Integration tests
└── test_performance.py     # Performance tests
```

## Prerequisites

1. Install test dependencies:
```bash
pip install -r requirements.txt
pip install pytest pytest-cov psutil
```

2. Ensure test data is available:
- The test data is included in the repository under `tests/test_data/songs/`
- Each song directory contains all necessary files (score, audio, timing)
- Run `scripts/prepare_test_data.py` if test data is missing

## Running Tests

### Running All Tests
```bash
pytest tests/
```

### Running Specific Test Categories
1. Unit Tests:
```bash
pytest tests/test_audio_processing.py
```

2. Integration Tests:
```bash
pytest tests/test_integration.py
```

3. Performance Tests:
```bash
pytest tests/test_performance.py
```

### Running with Coverage Report
```bash
pytest --cov=src tests/
```

## Test Categories

### 1. Audio Processing Tests (`test_audio_processing.py`)
- Tests basic audio processing functionality
- Covers different time signatures:
  - Simple time (4/4): Yellow, Hallelujah
  - Compound time (6/8): Perfect
  - Mixed time: Viva la Vida
- Verifies audio file loading and properties
- Tests score processing and time signature detection

### 2. Integration Tests (`test_integration.py`)
- Tests complete workflow from file loading to synchronization
- Covers different scenarios:
  - Simple time signatures (4/4)
  - Compound time signatures (6/8)
  - Mixed time signatures
- Verifies proper interaction between components

### 3. Performance Tests (`test_performance.py`)
- Tests memory usage and processing time
- Verifies performance thresholds:
  - Memory usage < 500MB
  - Processing time < 5s
  - Audio loading time < 2s

## Test Data Organization

Each song in the `test_data/songs/` directory contains:
1. Score file (e.g., `song_score.xml`)
   - MusicXML format
   - Contains musical notation and metadata
2. Audio file (e.g., `song_audio.ogg`)
   - OGG format
   - High-quality audio recording
3. Timing file (e.g., `song_tempo.xml` or `song_timing.txt`)
   - Contains tempo and timing information
   - Format varies by song

For more details about the test data organization and file formats, see `tests/test_data/README.md`.

## Adding New Tests

When adding new tests:

1. Follow the existing test structure
2. Add test data to appropriate directories
3. Update test files with new test cases
4. Ensure performance thresholds are appropriate
5. Document new test cases in this README

## Troubleshooting

1. Missing Test Data:
```bash
python scripts/prepare_test_data.py
```

2. Memory Issues:
- Increase `MAX_MEMORY_USAGE` in `test_performance.py`
- Run garbage collection manually
- Monitor memory usage with `psutil`

3. Timing Issues:
- Adjust `MAX_PROCESSING_TIME` and `MAX_AUDIO_LOAD_TIME`
- Consider system performance variations
- Use appropriate timing thresholds for CI/CD

## Contributing

When contributing new tests:

1. Follow the existing test structure
2. Add appropriate test data
3. Update this README with new test cases
4. Ensure all tests pass locally
5. Verify performance metrics 