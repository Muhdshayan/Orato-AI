# Python Modules - ORATO-AI

This directory contains the core AI/ML modules for the ORATO-AI system. Each subdirectory handles a specific aspect of the AI pipeline.

## Directory Structure

### Preprocessor/
Splits video and audio, makes frames, and does initial preprocessing for other modules.
- Audio preprocessing and normalization
- Initial data preparation for downstream modules
Audio and video preprocessing, normalization, and data preparation.
- Audio preprocessing (noise reduction, normalization)
- Video preprocessing (stabilization, enhancement)
- Data normalization and standardization
- Format conversion utilities

### cv/ (Computer Vision)
Computer vision modules for pose detection, gesture recognition, and frame analysis.
- Pose detection and analysis
- Gesture recognition
- Frame extraction and processing
- Visual feature extraction

### nlp_asr/ (NLP/ASR)
Natural Language Processing and Automatic Speech Recognition modules.
- Speech recognition and transcription
- Filler word detection
- Language processing utilities
- Audio-to-text conversion

### content_relevance/
Content relevance analysis and LLM-assisted topic verification.
- Topic relevance scoring
- Content quality assessment
- LLM-based content analysis
- Semantic similarity analysis

### score_aggregator/
Composite scoring and feedback aggregation logic.
- Multi-modal scoring algorithms
- Score normalization and weighting
- Feedback aggregation
- Performance metrics calculation

### llm/
Large Language Model custom scripts and utilities.
- LLM integration and management
- Prompt engineering utilities
- Model fine-tuning scripts
- LLM-based analysis tools


### utils/
Shared helpers and utilities used across all modules.
- Common data structures
- Utility functions
- Configuration management
- Logging and debugging tools

## Installation

Install all dependencies using:
```bash
pip install -r requirements.txt
```

## Usage

Each module can be imported and used independently:
```python
from python_modules.cv import pose_detector
from python_modules.nlp_asr import speech_recognizer
from python_modules.score_aggregator import score_calculator
```
