class Session:
    """
    Model representing a transcription session
    """
    def __init__(self, session_id, start_time=None, end_time=None, active=False):
        self.session_id = session_id
        self.start_time = start_time
        self.end_time = end_time
        self.active = active
        self.mic_chunks = []
        self.speaker_chunks = []
    
    def to_dict(self):
        """Convert session to dictionary"""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "active": self.active,
            "mic_chunks_count": len(self.mic_chunks),
            "speaker_chunks_count": len(self.speaker_chunks)
        }

class Chunk:
    """
    Model representing a transcription chunk
    """
    def __init__(self, chunk_id, session_id, timestamp, text, audio_path, source, speaker_id=None):
        self.chunk_id = chunk_id
        self.session_id = session_id
        self.timestamp = timestamp
        self.text = text
        self.audio_path = audio_path
        self.source = source  # "mic" or "speaker"
        self.speaker_id = speaker_id
    
    def to_dict(self):
        """Convert chunk to dictionary"""
        return {
            "chunk_id": self.chunk_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "text": self.text,
            "audio_path": self.audio_path,
            "source": self.source,
            "speaker_id": self.speaker_id
        }