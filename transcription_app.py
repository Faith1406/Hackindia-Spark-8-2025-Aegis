from flask import Flask, render_template, jsonify, request, send_file, abort
import os
from services.transcription import start_session, stop_session, get_session_status, get_latest_chunks, active_session
from utils.audio_utils import log_message, get_available_devices
from database.db_utils import get_audio_path

app = Flask(__name__)

# Serve static audio files from audio_chunks directory
@app.route('/audio_chunks/<path:filename>')
def serve_audio(filename):
    audio_file_path = os.path.join("audio_chunks", filename)
    if os.path.exists(audio_file_path):
        return send_file(audio_file_path, mimetype="audio/wav")
    else:
        abort(404)

@app.route('/api/process_to_main', methods=['POST'])
def process_to_main():
    """Process current transcript and redirect to main app for further processing."""
    try:
        # Get the current transcript info
        if active_session:
            transcript_path = active_session.get_transcript_file_path()
            
            if not transcript_path:
                return jsonify({"success": False, "error": "No transcript file available"})
                
            # Here we could do some pre-processing if needed
            
            # Return success with the main app URL
            return jsonify({
                "success": True, 
                "redirect_url": "http://localhost:5000/",
                "transcript_path": transcript_path
            })
        else:
            # Use the fixed transcript file path
            fixed_transcript_path = "transcriptions/transcription.txt"
            if os.path.exists(fixed_transcript_path):
                return jsonify({
                    "success": True, 
                    "redirect_url": "http://localhost:5000/",
                    "transcript_path": fixed_transcript_path
                })
            
            return jsonify({"success": False, "error": "No active session or transcript file"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# Download transcript file
@app.route('/download/<path:filepath>')
def download_file(filepath):
    # Security check - only allow downloading transcript files
    if not filepath.startswith("transcript_") and not os.path.basename(filepath).startswith("transcript_") and filepath != "transcriptions/transcription.txt":
        abort(403)  # Forbidden
    
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        abort(404)

@app.route('/')
def index():
    """Render the main page"""
    return render_template('transcription.html')

@app.route('/api/devices', methods=['GET'])
def get_devices():
    """Get available audio devices"""
    devices = get_available_devices()
    return jsonify(devices)

@app.route('/api/start', methods=['POST'])
def api_start_session():
    """Start a new transcription session"""
    session_id = start_session()
    return jsonify({"success": True, "session_id": session_id})

@app.route('/api/stop', methods=['POST'])
def api_stop_session():
    """Stop the active transcription session"""
    session_id = stop_session()
    return jsonify({"success": True, "session_id": session_id})

@app.route('/api/status', methods=['GET'])
def api_get_status():
    """Get the status of the active session"""
    status = get_session_status()
    return jsonify(status)

@app.route('/api/chunks', methods=['GET'])
def api_get_chunks():
    """Get the latest transcription chunks"""
    last_chunk_id = request.args.get('last_chunk_id', None)
    chunks = get_latest_chunks(last_chunk_id)
    return jsonify({"chunks": chunks})

@app.route('/api/audio/<path:chunk_id>', methods=['GET'])
def get_audio(chunk_id):
    """Get audio for a specific chunk - now handles full chunk IDs with session prefix"""
    audio_path = get_audio_path(chunk_id)
    if audio_path and os.path.exists(audio_path):
        return send_file(audio_path, mimetype="audio/wav")
    else:
        abort(404)

@app.route('/api/set_mic_threshold', methods=['POST'])
def set_mic_threshold():
    """Set the microphone noise threshold for the active recording session"""
    if not active_session:
        return jsonify({"success": False, "error": "No active recording session"})
    
    data = request.json
    if not data or 'threshold' not in data:
        return jsonify({"success": False, "error": "Missing threshold parameter"})
    
    try:
        threshold = float(data['threshold'])
        if threshold < 0:
            return jsonify({"success": False, "error": "Threshold must be positive"})
        
        active_session.recorder.set_mic_threshold(threshold)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/set_speaker_threshold', methods=['POST'])
def set_speaker_threshold():
    """Set the speaker noise threshold for the active recording session"""
    if not active_session:
        return jsonify({"success": False, "error": "No active recording session"})
    
    data = request.json
    if not data or 'threshold' not in data:
        return jsonify({"success": False, "error": "Missing threshold parameter"})
    
    try:
        threshold = float(data['threshold'])
        if threshold < 0:
            return jsonify({"success": False, "error": "Threshold must be positive"})
        
        active_session.recorder.set_speaker_threshold(threshold)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/transcript', methods=['GET'])
def get_transcript():
    """Get the complete combined transcript"""
    fixed_transcript_path = "transcriptions/transcription.txt"
    
    if active_session:
        return jsonify({
            "transcript": active_session.get_combined_transcript(),
            "file_path": fixed_transcript_path
        })
    else:
        # Check if the fixed transcript file exists
        if os.path.exists(fixed_transcript_path):
            try:
                with open(fixed_transcript_path, 'r', encoding='utf-8') as f:
                    transcript_content = f.read()
                
                return jsonify({
                    "transcript": transcript_content,
                    "file_path": fixed_transcript_path
                })
            except Exception as e:
                log_message(f"Error reading transcript file: {e}")
        
        return jsonify({
            "transcript": "",
            "file_path": fixed_transcript_path  # Still return the path even if empty
        })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)