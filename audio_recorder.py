import soundcard as sc
                # Default to coordinator team
import soundfile as sf

OUTPUT_FILE_NAME = "out.wav"   
SAMPLE_RATE = 48000             
RECORD_SEC = 5                  

with sc.get_microphone(id=str(sc.default_speaker().name), include_loopback=True).recorder(samplerate=SAMPLE_RATE) as mic:
    data = mic.record(numframes=SAMPLE_RATE*RECORD_SEC)
    
    sf.write(file=OUTPUT_FILE_NAME, data=data[:, 0], samplerate=SAMPLE_RATE)
