import threading
import numpy as np
import time
import os
import soundfile as sf
import soundcard as sc
from utils.audio_utils import log_message
from config import SAMPLE_RATE, CHUNK_DURATION

class ContinuousRecorder:
    def __init__(self, session):
        self.session = session
        self.is_recording = True
        
        # Separate buffers for mic and speaker
        self.mic_buffer = np.array([])
        self.speaker_buffer = np.array([])
        self.buffer_lock = threading.Lock()
        
        # Separate positions for processing
        self.last_mic_pos = 0
        self.last_speaker_pos = 0
        
        # Separate chunk counters
        self.mic_chunk_counter = 0
        self.speaker_chunk_counter = 0
        
        # Noise thresholds - can be adjusted independently
        self.mic_noise_threshold = 0.005
        self.speaker_noise_threshold = 0.01
        
        # Initialize audio devices
        try:
            self.default_mic = sc.default_microphone()
            self.loopback_speaker = sc.get_microphone(id=str(sc.default_speaker().name), include_loopback=True)
            log_message(f"Using mic: {self.default_mic.name} and speaker: {self.loopback_speaker.name}", self.session.session_id)
        except Exception as e:
            log_message(f"Error initializing audio devices: {e}", self.session.session_id)
            return
        
        # Start recording threads
        self.mic_thread = threading.Thread(target=self._record_microphone)
        self.mic_thread.daemon = True
        self.mic_thread.start()
        
        self.speaker_thread = threading.Thread(target=self._record_speaker)
        self.speaker_thread.daemon = True
        self.speaker_thread.start()
        
        # Start processing threads
        self.mic_processing_thread = threading.Thread(target=self._process_mic_chunks)
        self.mic_processing_thread.daemon = True
        self.mic_processing_thread.start()
        
        self.speaker_processing_thread = threading.Thread(target=self._process_speaker_chunks)
        self.speaker_processing_thread.daemon = True
        self.speaker_processing_thread.start()
    
    def _record_microphone(self):
        """Record from microphone to separate buffer."""
        log_message("Microphone recording started", self.session.session_id)
        
        # Small frames for low latency
        frames_per_step = int(SAMPLE_RATE * 0.1)
        
        try:
            with self.default_mic.recorder(samplerate=SAMPLE_RATE) as mic_recorder:
                while self.is_recording:
                    # Record microphone
                    mic_data = mic_recorder.record(numframes=frames_per_step)
                    
                    # Convert to mono
                    if mic_data.shape[1] > 0:
                        new_data = mic_data[:, 0].copy()
                    else:
                        new_data = np.zeros(frames_per_step)
                    
                    # Add to mic buffer
                    with self.buffer_lock:
                        if len(self.mic_buffer) == 0:
                            self.mic_buffer = new_data
                        else:
                            self.mic_buffer = np.concatenate((self.mic_buffer, new_data))
                    
                    # Short sleep to prevent CPU overuse
                    time.sleep(0.01)
        except Exception as e:
            log_message(f"Error in microphone recording: {e}", self.session.session_id)
    
    def _record_speaker(self):
        """Record from speaker to separate buffer."""
        log_message("Speaker recording started", self.session.session_id)
        
        # Small frames for low latency
        frames_per_step = int(SAMPLE_RATE * 0.1)
        
        try:
            with self.loopback_speaker.recorder(samplerate=SAMPLE_RATE) as speaker_recorder:
                while self.is_recording:
                    # Record speaker output
                    speaker_data = speaker_recorder.record(numframes=frames_per_step)
                    
                    # Convert to mono
                    if speaker_data.shape[1] > 0:
                        new_data = speaker_data[:, 0].copy()
                    else:
                        new_data = np.zeros(frames_per_step)
                    
                    # Add to speaker buffer
                    with self.buffer_lock:
                        if len(self.speaker_buffer) == 0:
                            self.speaker_buffer = new_data
                        else:
                            self.speaker_buffer = np.concatenate((self.speaker_buffer, new_data))
                    
                    # Short sleep to prevent CPU overuse
                    time.sleep(0.01)
        except Exception as e:
            log_message(f"Error in speaker recording: {e}", self.session.session_id)
    
    def _process_mic_chunks(self):
        """Process microphone chunks separately."""
        log_message("Microphone chunk processing started", self.session.session_id)
        log_message(f"Using mic noise threshold: {self.mic_noise_threshold}", self.session.session_id)
        
        # Wait to gather initial audio
        time.sleep(2)
        
        # Create temp directory if needed
        os.makedirs(self.session.temp_dir, exist_ok=True)
        
        chunk_size = int(CHUNK_DURATION * SAMPLE_RATE)
        
        while self.is_recording:
            try:
                current_time = time.time()
                
                with self.buffer_lock:
                    # Calculate positions
                    buffer_length = len(self.mic_buffer)
                    unprocessed_length = buffer_length - self.last_mic_pos
                    
                    # Process if we have a full chunk
                    if unprocessed_length >= chunk_size:
                        # Get chunk boundaries
                        start_pos = self.last_mic_pos
                        chunk_end_pos = start_pos + chunk_size
                        
                        # Ensure we're within buffer
                        if chunk_end_pos > buffer_length:
                            chunk_end_pos = buffer_length
                        
                        # Safety check
                        if start_pos >= buffer_length or start_pos < 0 or chunk_end_pos <= start_pos:
                            log_message("Invalid mic buffer positions - resetting", self.session.session_id)
                            self.last_mic_pos = max(0, buffer_length - chunk_size)
                            time.sleep(0.5)
                            continue
                        
                        # Extract chunk
                        chunk_data = self.mic_buffer[start_pos:chunk_end_pos].copy()
                        
                        # Verify chunk size
                        if len(chunk_data) != chunk_size:
                            log_message(f"Mic chunk size mismatch. Expected {chunk_size}, got {len(chunk_data)}. Skipping.", 
                                     self.session.session_id)
                            self.last_mic_pos += len(chunk_data)
                            continue
                        
                        # Update position
                        self.last_mic_pos = chunk_end_pos
                        
                        # Calculate audio level
                        audio_level = np.abs(chunk_data).mean()
                        
                        # Apply noise threshold
                        if audio_level < self.mic_noise_threshold:
                            # Skip this chunk - likely just background noise
                            continue
                        
                        # Increment chunk counter
                        self.mic_chunk_counter += 1
                        chunk_id = f"mic_{self.mic_chunk_counter}"
                        
                        # Save file
                        temp_file = f"{self.session.temp_dir}/{chunk_id}_{int(current_time)}.wav"
                        
                        # Check audio data validity
                        if np.isnan(chunk_data).any() or np.isinf(chunk_data).any():
                            chunk_data = np.nan_to_num(chunk_data)
                        
                        # Save with error handling
                        try:
                            sf.write(file=temp_file, data=chunk_data, samplerate=SAMPLE_RATE)
                            
                            # Verify file was created
                            if os.path.exists(temp_file) and os.path.getsize(temp_file) > 100:
                                # Add to queue with source=mic flag
                                self.session.transcription_queue.put((temp_file, chunk_id, audio_level, "mic"))
                                log_message(f"Processed mic chunk {chunk_id} (level: {audio_level:.6f})", self.session.session_id)
                            else:
                                log_message(f"Failed to save valid mic audio file", self.session.session_id)
                        except Exception as e:
                            log_message(f"Error saving mic audio: {str(e)}", self.session.session_id)
                
                # Sleep before checking again
                time.sleep(0.05)
                
            except Exception as e:
                log_message(f"Error processing mic chunk: {str(e)}", self.session.session_id)
                time.sleep(0.5)
    
    def _process_speaker_chunks(self):
        """Process speaker chunks separately."""
        log_message("Speaker chunk processing started", self.session.session_id)
        log_message(f"Using speaker noise threshold: {self.speaker_noise_threshold}", self.session.session_id)
        
        # Wait to gather initial audio
        time.sleep(2)
        
        # Create temp directory if needed
        os.makedirs(self.session.temp_dir, exist_ok=True)
        
        chunk_size = int(CHUNK_DURATION * SAMPLE_RATE)
        
        while self.is_recording:
            try:
                current_time = time.time()
                
                with self.buffer_lock:
                    # Calculate positions
                    buffer_length = len(self.speaker_buffer)
                    unprocessed_length = buffer_length - self.last_speaker_pos
                    
                    # Process if we have a full chunk
                    if unprocessed_length >= chunk_size:
                        # Get chunk boundaries
                        start_pos = self.last_speaker_pos
                        chunk_end_pos = start_pos + chunk_size
                        
                        # Ensure we're within buffer
                        if chunk_end_pos > buffer_length:
                            chunk_end_pos = buffer_length
                        
                        # Safety check
                        if start_pos >= buffer_length or start_pos < 0 or chunk_end_pos <= start_pos:
                            log_message("Invalid speaker buffer positions - resetting", self.session.session_id)
                            self.last_speaker_pos = max(0, buffer_length - chunk_size)
                            time.sleep(0.5)
                            continue
                        
                        # Extract chunk
                        chunk_data = self.speaker_buffer[start_pos:chunk_end_pos].copy()
                        
                        # Verify chunk size
                        if len(chunk_data) != chunk_size:
                            log_message(f"Speaker chunk size mismatch. Expected {chunk_size}, got {len(chunk_data)}. Skipping.", 
                                     self.session.session_id)
                            self.last_speaker_pos += len(chunk_data)
                            continue
                        
                        # Update position
                        self.last_speaker_pos = chunk_end_pos
                        
                        # Calculate audio level
                        audio_level = np.abs(chunk_data).mean()
                        
                        # Apply noise threshold
                        if audio_level < self.speaker_noise_threshold:
                            # Skip this chunk - likely just background noise
                            continue
                        
                        # Increment chunk counter
                        self.speaker_chunk_counter += 1
                        chunk_id = f"speaker_{self.speaker_chunk_counter}"
                        
                        # Save file
                        temp_file = f"{self.session.temp_dir}/{chunk_id}_{int(current_time)}.wav"
                        
                        # Check audio data validity
                        if np.isnan(chunk_data).any() or np.isinf(chunk_data).any():
                            chunk_data = np.nan_to_num(chunk_data)
                        
                        # Save with error handling
                        try:
                            sf.write(file=temp_file, data=chunk_data, samplerate=SAMPLE_RATE)
                            
                            # Verify file was created
                            if os.path.exists(temp_file) and os.path.getsize(temp_file) > 100:
                                # Add to queue with source=speaker flag
                                self.session.transcription_queue.put((temp_file, chunk_id, audio_level, "speaker"))
                                log_message(f"Processed speaker chunk {chunk_id} (level: {audio_level:.6f})", self.session.session_id)
                            else:
                                log_message(f"Failed to save valid speaker audio file", self.session.session_id)
                        except Exception as e:
                            log_message(f"Error saving speaker audio: {str(e)}", self.session.session_id)
                
                # Sleep before checking again
                time.sleep(0.05)
                
            except Exception as e:
                log_message(f"Error processing speaker chunk: {str(e)}", self.session.session_id)
                time.sleep(0.5)
    
    def set_mic_threshold(self, value):
        """Update microphone noise threshold."""
        self.mic_noise_threshold = float(value)
        log_message(f"Mic noise threshold updated to: {self.mic_noise_threshold}", self.session.session_id)
    
    def set_speaker_threshold(self, value):
        """Update speaker noise threshold."""
        self.speaker_noise_threshold = float(value)
        log_message(f"Speaker noise threshold updated to: {self.speaker_noise_threshold}", self.session.session_id)
    
    def stop(self):
        """Stop all recording."""
        self.is_recording = False
        log_message("Stopping all recording", self.session.session_id)