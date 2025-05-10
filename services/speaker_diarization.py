# speaker_diarization.py
import numpy as np
import librosa
from scipy.spatial.distance import cosine
import pickle
import os
import time
from collections import defaultdict

class SpeakerDiarizer:
    def __init__(self, session_id):
        self.session_id = session_id
        self.speaker_embeddings = {}  # Maps speaker_id to their voice embedding
        self.speaker_counter = 0      # Counter for new speakers
        self.similarity_threshold = 0.7  # Threshold for matching speakers (higher = stricter)
        
        # Create embeddings directory if it doesn't exist
        os.makedirs("speaker_embeddings", exist_ok=True)
        
        # Session-specific storage for speaker identification
        self.embedding_file = f"speaker_embeddings/session_{session_id}.pkl"
        
        # Load embeddings if file exists (for resuming a session)
        if os.path.exists(self.embedding_file):
            try:
                with open(self.embedding_file, 'rb') as f:
                    data = pickle.load(f)
                    self.speaker_embeddings = data.get('embeddings', {})
                    self.speaker_counter = data.get('counter', 0)
                    print(f"Loaded {len(self.speaker_embeddings)} speaker profiles")
            except Exception as e:
                print(f"Error loading speaker embeddings: {e}")
                self.speaker_embeddings = {}
                self.speaker_counter = 0
    
    def extract_embedding(self, audio_path):
        """Extract voice embedding from audio file"""
        try:
            # Load audio file
            y, sr = librosa.load(audio_path, sr=None)
            
            # Normalize audio
            y = librosa.util.normalize(y)
            
            # Extract MFCC features (good for speaker identification)
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
            
            # Compute mean across time
            mfcc_mean = np.mean(mfccs, axis=1)
            
            # Normalize the embedding
            embedding = mfcc_mean / np.linalg.norm(mfcc_mean)
            
            return embedding
            
        except Exception as e:
            print(f"Error extracting embedding: {e}")
            return None
    
    def identify_speaker(self, audio_path, source):
        """Identify the speaker from an audio chunk"""
        # Only process speaker source audio (not microphone)
        if source != "speaker":
            return None
            
        # Extract voice embedding from the audio chunk
        embedding = self.extract_embedding(audio_path)
        
        if embedding is None:
            print("Failed to extract embedding")
            return None
            
        # If no speakers yet, create the first one
        if len(self.speaker_embeddings) == 0:
            speaker_id = f"Speaker 1"
            self.speaker_counter = 1
            self.speaker_embeddings[speaker_id] = embedding
            self._save_embeddings()
            return speaker_id
            
        # Compare with known speakers
        best_match = None
        highest_similarity = -1
        
        for speaker_id, known_embedding in self.speaker_embeddings.items():
            # Calculate cosine similarity (higher = more similar)
            similarity = 1 - cosine(embedding, known_embedding)
            
            if similarity > highest_similarity:
                highest_similarity = similarity
                best_match = speaker_id
        
        # If the similarity is high enough, it's the same speaker
        if highest_similarity >= self.similarity_threshold:
            # Update the embedding with a weighted average to adapt over time
            self.speaker_embeddings[best_match] = (
                0.7 * self.speaker_embeddings[best_match] + 0.3 * embedding
            )
            return best_match
        else:
            # New speaker
            self.speaker_counter += 1
            new_speaker_id = f"Speaker {self.speaker_counter}"
            self.speaker_embeddings[new_speaker_id] = embedding
            self._save_embeddings()
            return new_speaker_id
    
    def _save_embeddings(self):
        """Save speaker embeddings to disk"""
        try:
            with open(self.embedding_file, 'wb') as f:
                data = {
                    'embeddings': self.speaker_embeddings,
                    'counter': self.speaker_counter,
                }
                pickle.dump(data, f)
        except Exception as e:
            print(f"Error saving speaker embeddings: {e}")