from faster_whisper import WhisperModel
import threading
import queue
import os
import time
import shutil
import sqlite3
import numpy as np
import soundfile as sf
from utils.audio_utils import log_message
from config import DB_PATH, SAMPLE_RATE, CHUNK_DURATION
from services.audio_recorder import ContinuousRecorder
from services.speaker_diarization import SpeakerDiarizer
from database.db_utils import get_chunks_from_db, get_latest_session_id, get_audio_path

# Transcription model (initialized on demand)
model = None
model_size = "large-v3"

# Global session storage
active_session = None

def initialize_model():
    """Initialize the Whisper model"""
    global model
    if model is None:
        log_message(f"Loading Whisper model {model_size}...")
        model = WhisperModel(model_size, device="cuda", compute_type="float16")
        log_message("Model loaded successfully!")
    return model

class TranscriptionSession:
    def __init__(self, session_id=None):
        self.session_id = session_id if session_id else str(os.urandom(16).hex())
        self.transcription_queue = queue.Queue()
        self.is_recording = True
        self.temp_dir = f"temp_{self.session_id}"
        
        # Maintain a list of all chunks for both sources
        self.all_chunks = []
        
        # Separate chunk tracking for convenience
        self.mic_chunks = []
        self.speaker_chunks = []
        
        # Combined transcript
        self.combined_transcript = []  # List of (timestamp, speaker, text) tuples for sorting
        
        # Transcript files - now we'll have just one combined file
        self.combined_transcript_file = f"transcript_{self.session_id}.txt"
        
        # Create temp directory for this session
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Ensure model is initialized
        initialize_model()
        
        # Initialize the speaker diarizer
        self.speaker_diarizer = SpeakerDiarizer(self.session_id)
        
        # Initialize transcript file with header
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        with open(self.combined_transcript_file, "w", encoding="utf-8") as f:
            f.write(f"Transcription Session: {self.session_id}\n")
            f.write(f"Started: {timestamp}\n")
            f.write("-" * 50 + "\n\n")
        
        # Register session in database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (session_id, start_time, active) VALUES (?, ?, ?)",
            (self.session_id, timestamp, 1)
        )
        conn.commit()
        conn.close()
        
        log_message(f"Session created. Temp directory: {self.temp_dir}", self.session_id)
        log_message(f"Combined transcript file: {self.combined_transcript_file}", self.session_id)
        
        # Start continuous recorder
        self.recorder = ContinuousRecorder(self)
        
        # Start transcription thread
        self.transcription_thread = threading.Thread(target=self._transcribe_chunks)
        self.transcription_thread.daemon = True
        self.transcription_thread.start()
        
        log_message("Dual-source recording with speaker diarization started", self.session_id)
        
    def _transcribe_chunks(self):
        """Transcribes audio chunks with source identification and speaker diarization."""
        log_message("Transcription thread started", self.session_id)
        
        while self.is_recording or not self.transcription_queue.empty():
            try:
                try:
                    # Get chunk file with timeout
                    chunk_file, chunk_id, audio_level, source = self.transcription_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                log_message(f"Transcribing {source} chunk {chunk_id}", self.session_id)
                
                # Create a globally unique chunk ID
                unique_chunk_id = f"{self.session_id}_{chunk_id}"
                
                # Transcribe the chunk
                segments, info = model.transcribe(
                    chunk_file, 
                    beam_size=10,              # Better transcription quality
                    temperature=0.0,           # Deterministic output
                    no_speech_threshold=0.6,   # More sensitive speech detection
                    word_timestamps=True       # Generate timestamps for words
                )
                
                # Extract text
                segment_texts = []
                for segment in segments:
                    segment_texts.append(segment.text.strip())
                
                # Process regardless of content
                transcription_text = " ".join(segment_texts) if segment_texts else "[silence]"
                timestamp = time.strftime("%H:%M:%S")
                
                # Save the audio file permanently
                permanent_audio_path = f"audio_chunks/{self.session_id}_{chunk_id}.wav"
                shutil.copy2(chunk_file, permanent_audio_path)
                
                # Identify the speaker for this chunk if it's from speaker source
                speaker_id = None
                if source == "speaker" and transcription_text != "[silence]":
                    speaker_id = self.speaker_diarizer.identify_speaker(chunk_file, source)
                    if speaker_id:
                        log_message(f"Identified {speaker_id} for chunk {chunk_id}", self.session_id)
                
                # Check if this chunk already exists in the database
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                # Add speaker_id column if it doesn't exist
                cursor.execute("PRAGMA table_info(chunks)")
                columns = cursor.fetchall()
                speaker_id_exists = any(col[1] == 'speaker_id' for col in columns)
                
                if not speaker_id_exists:
                    cursor.execute("ALTER TABLE chunks ADD COLUMN speaker_id TEXT")
                    conn.commit()
                
                cursor.execute("SELECT chunk_id FROM chunks WHERE chunk_id = ?", (unique_chunk_id,))
                existing_chunk = cursor.fetchone()
                
                # Only insert if this chunk doesn't already exist
                if not existing_chunk:
                    # Add to database with source and speaker info
                    cursor.execute(
                        "INSERT INTO chunks (chunk_id, session_id, timestamp, text, audio_path, source, speaker_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (unique_chunk_id, self.session_id, timestamp, transcription_text, permanent_audio_path, source, speaker_id)
                    )
                    conn.commit()
                    
                    # Create a display name for the speaker
                    display_speaker = "You" if source == "mic" else (speaker_id if speaker_id else "Speaker")
                    
                    # Only add to transcripts if not silence
                    if transcription_text != "[silence]":
                        # Create chunk info for storage
                        chunk_info = {
                            "text": transcription_text,
                            "timestamp": timestamp,
                            "chunk_id": unique_chunk_id,
                            "audio_path": permanent_audio_path,
                            "source": source,
                            "speaker_id": speaker_id,
                            "display_speaker": display_speaker
                        }
                        
                        # Add to appropriate chunk lists
                        self.all_chunks.append(chunk_info)
                        
                        if source == "mic":
                            self.mic_chunks.append(chunk_info)
                        elif source == "speaker":
                            self.speaker_chunks.append(chunk_info)
                        
                        # Add to combined transcript list
                        self.combined_transcript.append((timestamp, display_speaker, transcription_text))
                        
                        # Immediately append to transcript file
                        with open(self.combined_transcript_file, "a", encoding="utf-8") as f:
                            f.write(f"[{timestamp}] {display_speaker}: {transcription_text}\n")
                        
                        log_message(f"Transcribed {source} {display_speaker}: {transcription_text}", self.session_id)
                else:
                    log_message(f"Chunk {unique_chunk_id} already exists in database, skipping", self.session_id)
                
                conn.close()
                
                # Mark as done
                self.transcription_queue.task_done()
                
                # Delete the temporary file
                os.remove(chunk_file)
                
            except Exception as e:
                log_message(f"Error in transcription: {str(e)}", self.session_id)
                if not self.transcription_queue.empty():
                    self.transcription_queue.task_done()

    def stop(self):
        """Stop the recording session"""
        log_message("Stopping recording session", self.session_id)
        self.is_recording = False
        self.recorder.stop()
        
        # Update session status in database
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessions SET end_time = ?, active = ? WHERE session_id = ?",
            (timestamp, 0, self.session_id)
        )
        conn.commit()
        conn.close()
        
        # Sort transcript by timestamp
        sorted_transcript = sorted(self.combined_transcript, key=lambda x: x[0])
        
        # Create a clean sorted transcript text
        sorted_transcript_text = "\n".join([f"[{ts}] {speaker}: {text}" for ts, speaker, text in sorted_transcript])
        
        # Finalize transcript file
        with open(self.combined_transcript_file, "a", encoding="utf-8") as f:
            f.write("\n" + "-" * 50 + "\n")
            f.write(f"Session ended: {timestamp}\n")
            f.write("\n=== COMPLETE TRANSCRIPT (CHRONOLOGICAL) ===\n\n")
            f.write(sorted_transcript_text)
            f.write("\n\n")
        
        log_message(f"Transcript finalized: {self.combined_transcript_file}", self.session_id)
        
    def cleanup(self):
        """Clean up temp files"""
        log_message("Cleaning up session", self.session_id)
        self.is_recording = False
        # Wait for queue to be processed
        self.transcription_queue.join()
        # Delete temp directory (but keep transcript files)
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        log_message(f"Removed temporary files directory: {self.temp_dir}", self.session_id)
        
    def get_new_chunks(self, last_chunk_id=None):
        """Get all new chunks since last_chunk_id, from both sources."""
        # All chunks are already combined
        all_chunks = self.all_chunks
        
        # Sort by timestamp (to keep them in chronological order)
        all_chunks.sort(key=lambda x: x["timestamp"])
        
        if last_chunk_id is None:
            return all_chunks
        
        # Find index of last chunk
        for i, chunk in enumerate(all_chunks):
            if chunk["chunk_id"] == last_chunk_id:
                return all_chunks[i+1:]
        
        # If not found, return all chunks
        return all_chunks
    
    def get_combined_transcript(self):
        """Get the complete transcript as a string."""
        return "\n".join([f"[{ts}] {speaker}: {text}" for ts, speaker, text in 
                         sorted(self.combined_transcript, key=lambda x: x[0])])
    
    def get_transcript_file_path(self):
        """Get the path to the transcript file."""
        return self.combined_transcript_file

# Global functions for API access

def start_session():
    """Start a new transcription session"""
    global active_session
    
    # Stop any existing session
    if active_session:
        stop_session()
    
    # Create a new session
    active_session = TranscriptionSession()
    return active_session.session_id

def stop_session():
    """Stop the active transcription session"""
    global active_session
    
    if active_session:
        active_session.stop()
        active_session.cleanup()
        session_id = active_session.session_id
        active_session = None
        return session_id
    
    return None

def get_session_status():
    """Get the status of the active session"""
    global active_session
    
    if active_session:
        return {
            "active": True,
            "session_id": active_session.session_id
        }
    else:
        return {
            "active": False,
            "session_id": None
        }

def get_latest_chunks(last_chunk_id=None):
    """Get the latest transcription chunks"""
    global active_session
    
    if active_session:
        return active_session.get_new_chunks(last_chunk_id)
    else:
        # If no active session, check database for most recent session
        session_id = get_latest_session_id()
        if session_id:
            return get_chunks_from_db(session_id, last_chunk_id)
        return []