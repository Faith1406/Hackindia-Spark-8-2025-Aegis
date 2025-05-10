import soundcard as sc
import soundfile as sf
import numpy as np
import datetime
import os
import warnings

# Filter out warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message="data discontinuity in recording")

def log_message(message, session_id=None):
    """Log a message with timestamp and optional session ID"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if session_id:
        print(f"[{timestamp}] [{session_id[:8]}] {message}")
    else:
        print(f"[{timestamp}] {message}")
    
    # Also log to file
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = f"{log_dir}/transcription_{datetime.datetime.now().strftime('%Y-%m-%d')}.log"
    
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            if session_id:
                f.write(f"[{timestamp}] [{session_id[:8]}] {message}\n")
            else:
                f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        print(f"Error writing to log file: {e}")

def get_available_devices():
    """Get a list of available audio devices"""
    devices = {
        "microphones": [],
        "speakers": [],
        "default_mic": "",
        "default_speaker": ""
    }
    
    try:
        for mic in sc.all_microphones():
            devices["microphones"].append({"name": mic.name, "id": mic.id})
        
        for speaker in sc.all_speakers():
            devices["speakers"].append({"name": speaker.name, "id": speaker.id})
        
        default_mic = sc.default_microphone()
        default_speaker = sc.default_speaker()
        
        if default_mic:
            devices["default_mic"] = default_mic.name
        
        if default_speaker:
            devices["default_speaker"] = default_speaker.name
    except Exception as e:
        log_message(f"Error getting audio devices: {e}")
    
    return devices

def analyze_audio_quality(audio_data, sample_rate=48000):
    """
    Analyze audio quality metrics
    Returns a dict with volume, noise level, and clipping percentage
    """
    try:
        # Ensure audio is in the right format
        if len(audio_data) == 0:
            return {
                "volume": 0,
                "noise_level": 0,
                "clipping": 0,
                "is_silent": True
            }
            
        # Convert to mono if needed
        if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
            audio = np.mean(audio_data, axis=1)
        else:
            audio = audio_data.copy()
            
        # Calculate volume (RMS)
        rms = np.sqrt(np.mean(np.square(audio)))
        volume_db = 20 * np.log10(max(rms, 1e-10))
        
        # Calculate noise level (using spectral flatness as a proxy)
        # Higher values indicate more noise
        from scipy import signal
        frequencies, times, spectrogram = signal.spectrogram(audio, fs=sample_rate)
        log_spec = np.log(spectrogram + 1e-10)
        spectral_flatness = np.exp(np.mean(log_spec, axis=0)) / np.mean(np.exp(log_spec), axis=0)
        noise_level = np.mean(spectral_flatness)
        
        # Calculate clipping (percentage of samples near max/min)
        threshold = 0.98  # 98% of max value
        clipping_samples = np.sum((np.abs(audio) > threshold))
        clipping_percentage = (clipping_samples / len(audio)) * 100
        
        # Determine if the audio is silent
        is_silent = volume_db < -50  # -50 dB threshold for silence
        
        return {
            "volume": volume_db,
            "noise_level": noise_level,
            "clipping": clipping_percentage,
            "is_silent": is_silent
        }
        
    except Exception as e:
        log_message(f"Error analyzing audio quality: {e}")
        return {
            "volume": 0,
            "noise_level": 0,
            "clipping": 0,
            "is_silent": True,
            "error": str(e)
        }