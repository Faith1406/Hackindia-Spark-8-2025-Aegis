"""
Configuration settings for the transcription application
"""
import os

# Audio settings
SAMPLE_RATE = 48000  # Hz
CHUNK_DURATION = 5  # seconds per chunk
PROCESSING_INTERVAL = 5  # seconds between processing chunks

# Database settings
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transcriptions.db")

# Transcription model settings
MODEL_SIZE = "large-v3"  # Whisper model size
USE_CUDA = True  # Whether to use GPU acceleration

# Noise threshold defaults
DEFAULT_MIC_THRESHOLD = 0.005
DEFAULT_SPEAKER_THRESHOLD = 0.01

# Speaker diarization settings
SPEAKER_SIMILARITY_THRESHOLD = 0.7  # Higher values = stricter speaker matching