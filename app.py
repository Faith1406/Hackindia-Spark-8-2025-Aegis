from flask import Flask, render_template, request, jsonify
from palette import Palette
import os
from dotenv import load_dotenv
from bridge import send_latest_transcription_to_slack  # Import the function from bridge.py
from notion_maker import load_txt_transcript, create_notion_page, analyze_transcript_with_ollama  # Import the necessary functions from notion_maker.py
import glob
from datetime import datetime
import requests

load_dotenv()

app = Flask(__name__)

# Initialize the system
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("API_KEY")
system = Palette(
    provider="gemini",
    model_name="gemini-1.5-flash-8b",
    api_key=api_key,
    max_tokens=1024,
    system_name="AI Meeting Assistant"
)

def fetch_latest_transcript_from_transcription_app():
    """Fetch the latest transcript from the transcription app."""
    try:
        transcription_app_url = "http://localhost:3000/api/transcript"
        response = requests.get(transcription_app_url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            transcript_content = data.get("transcript", "")
            transcript_file_path = data.get("file_path", None)
            
            if transcript_content and transcript_file_path:
                print(f"Fetched transcript from transcription app: {transcript_file_path}")
                return transcript_content, transcript_file_path
            else:
                print("No transcript content or file path returned")
                return None, None
        else:
            print(f"Error fetching transcript: {response.status_code}")
            return None, None
    except Exception as e:
        print(f"Exception while fetching transcript: {str(e)}")
        return None, None

def get_latest_transcript_file():
    """Get the latest transcript file from the transcriptions directory."""
    transcript_dir = os.getenv("TRANSCRIPTION_DIRECTORIES", "transcriptions")
    # If comma-separated, use the first directory
    if "," in transcript_dir:
        transcript_dir = transcript_dir.split(",")[0].strip()
    
    files = glob.glob(os.path.join(transcript_dir, "*.txt"))
    
    if not files:
        print("No transcription files found.")
        return None
    
    # Sort by modification time (newest first)
    latest_file = max(files, key=os.path.getmtime)
    print(f"Found latest transcript: {os.path.basename(latest_file)}")
    return latest_file

@app.route('/process_live_transcript', methods=['POST'])
def process_live_transcript():
    """Process the latest transcript from the transcription app."""
    try:
        # Fetch the latest transcript from the transcription app
        transcript_content, transcript_file_path = fetch_latest_transcript_from_transcription_app()
        
        if not transcript_content or not transcript_file_path:
            return jsonify({'error': 'No transcript available from transcription app'})
        
        # Save the transcript to the transcriptions directory
        transcription_dir = os.getenv("TRANSCRIPTION_DIRECTORIES", "transcriptions")
        if "," in transcription_dir:
            transcription_dir = transcription_dir.split(",")[0].strip()
        
        # Create the directory if it doesn't exist
        os.makedirs(transcription_dir, exist_ok=True)
        
        # Use the original filename or generate a new one
        target_filename = os.path.basename(transcript_file_path)
        if not target_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_filename = f"transcript_{timestamp}.txt"
        
        target_path = os.path.join(transcription_dir, target_filename)
        
        # Save the transcript
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(transcript_content)
        
        print(f"Saved transcript to {target_path}")
        
        # Send to Slack
        send_latest_transcription_to_slack()
        
        # Process transcript and create Notion page
        notion_result = process_transcript_to_notion()
        
        # Generate summary and minutes
        summary_response = system.summarize_latest_transcript()
        minutes_response = system.generate_minutes_for_latest_transcript()
        
        # Combine results
        summary_content = summary_response[0]['content'] if isinstance(summary_response, list) and len(summary_response) > 0 else str(summary_response)
        minutes_content = minutes_response[0]['content'] if isinstance(minutes_response, list) and len(minutes_response) > 0 else str(minutes_response)
        
        response_content = f"""
        Transcript processed successfully!
        
        {notion_result}
        
        SUMMARY:
        {summary_content}
        
        MINUTES:
        {minutes_content}
        """
        
        # Convert newlines to HTML line breaks before sending
        response_content = response_content.replace('\n', '<br>')
        
        return jsonify({'response': response_content})
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error processing live transcript: {str(e)}\n{error_details}")
        return jsonify({'error': f"Failed to process live transcript: {str(e)}"})

def process_transcript_to_notion():
    """Process the latest transcript and create a Notion page."""
    try:
        # Get the latest transcript file
        transcript_file = get_latest_transcript_file()
        if not transcript_file:
            return "No transcript file found."
        
        # Load and analyze transcript
        transcript = load_txt_transcript(transcript_file)
        if not transcript:
            return "Failed to load transcript."
        
        # Analyze transcript
        analysis = analyze_transcript_with_ollama(transcript)
        
        # Extract just the filename without extension
        base_filename = os.path.splitext(os.path.basename(transcript_file))[0]
        
        # Define the directories for summaries and minutes
        minutes_dir = "minutes"
        summaries_dir = "summaries"
        
        # Create Notion page with directory information
        page_url = create_notion_page(
            analysis, 
            transcript_file, 
            transcript, 
            minutes_dir, 
            summaries_dir
        )
        
        # Now load the actual content of the minutes and summary to display
        try:
            # Find the appropriate minutes file
            minutes_files = glob.glob(os.path.join(minutes_dir, f"{base_filename}*.txt"))
            if not minutes_files:
                minutes_files = glob.glob(os.path.join(minutes_dir, "*.txt"))
            
            minutes_content = ""
            if minutes_files:
                latest_minutes = max(minutes_files, key=os.path.getmtime)
                with open(latest_minutes, 'r', encoding='utf-8') as f:
                    minutes_content = f.read()
            
            # Find the appropriate summary file
            summary_files = glob.glob(os.path.join(summaries_dir, f"{base_filename}*.txt"))
            if not summary_files:
                summary_files = glob.glob(os.path.join(summaries_dir, "*.txt"))
            
            summary_content = ""
            if summary_files:
                latest_summary = max(summary_files, key=os.path.getmtime)
                with open(latest_summary, 'r', encoding='utf-8') as f:
                    summary_content = f.read()
            
            # Create a response that includes both the Notion status and the file contents
            response = "Transcript processing results:\n\n"
            
            if page_url:
                response += f"✅ Notion page created successfully: {page_url}\n\n"
            else:
                response += "❌ Failed to create Notion page.\n\n"
            
            if summary_content:
                response += "SUMMARY:\n" + summary_content + "\n\n"
            
            if minutes_content:
                response += "MINUTES:\n" + minutes_content
            
            return response
            
        except Exception as e:
            if page_url:
                return f"Notion page created successfully: {page_url}\nBut failed to load file contents: {str(e)}"
            else:
                return f"Failed to create Notion page and load file contents: {str(e)}"
    except Exception as e:
        return f"Error processing transcript: {str(e)}"

@app.route('/')
def index():
    soul_machines_api_key = os.getenv("SOUL_MACHINES_API_KEY", "")
    return render_template('index.html', soul_machines_api_key=soul_machines_api_key)

def read_log_file(log_path):
    """Read and return the content of a log file."""
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading log file: {str(e)}"

@app.route('/process', methods=['POST'])
def process():
    user_input = request.form['user_input']
    
    if not user_input.strip():
        return jsonify({'error': 'Please enter a request'})
    
    try:
        if user_input.lower().startswith("va:"):
            content = user_input[len("va:"):].strip()
            response = system.va_query(content)
        elif user_input.lower() == "data: summarize":
            # Send latest transcription to Slack before summarizing
            send_latest_transcription_to_slack()
            # Create Notion page for the latest transcript
            notion_result = process_transcript_to_notion()
            # Then continue with the summarization
            response = system.summarize_latest_transcript()
            # Add Notion page creation result to response
            if isinstance(response, list) and len(response) > 0:
                response[0]['content'] += f"\n\n{notion_result}"
            else:
                response = [{'content': f"{response}\n\n{notion_result}"}]
        elif user_input.lower() == "data: minutes":
            # Send latest transcription to Slack before generating minutes
            send_latest_transcription_to_slack()
            # Create Notion page for the latest transcript
            notion_result = process_transcript_to_notion()
            # Then continue with minutes generation
            response = system.generate_minutes_for_latest_transcript()
            # Add Notion page creation result to response
            if isinstance(response, list) and len(response) > 0:
                response[0]['content'] += f"\n\n{notion_result}"
            else:
                response = [{'content': f"{response}\n\n{notion_result}"}]
        elif user_input.lower().startswith("data: summarize:"):
            file_name = user_input[len("data: summarize:"):].strip()
            response = system.summarize_transcript(file_name)
        elif user_input.lower().startswith("data: minutes:"):
            file_name = user_input[len("data: minutes:"):].strip()
            response = system.generate_minutes_for_transcript(file_name)
        elif user_input.lower().startswith("data:"):
            content = user_input[len("data:"):].strip()
            response = system.data_analysis(content)
        elif user_input.lower() == "check":
            response = system.system_check()
        else:
            # Process with the coordinator team and get the log path
            response_obj = system.process(user_input)
            log_path = response_obj[0]['content'].split("and saved to ")[1]
            
            # Read the log file content
            log_content = read_log_file(log_path)
            
            # Return both the original response and the log content
            return jsonify({'response': log_content})
            
        # Convert newlines to HTML line breaks before sending
        if isinstance(response, list) and len(response) > 0:
            response_content = response[0].get('content', 'No response content')
            # Convert newlines to <br> tags for proper HTML display
            response_content = response_content.replace('\n', '<br>')
        else:
            response_content = str(response)
            response_content = response_content.replace('\n', '<br>')
            
        return jsonify({'response': response_content})
        
    except Exception as e:
        return jsonify({'error': f"Failed to process request: {str(e)}"})

if __name__ == '__main__':
    # Create necessary folders if they don't exist
    for folder in ["transcriptions", "summaries", "minutes"]:
        if not os.path.exists(folder):
            os.makedirs(folder)
    
    app.run(debug=True)
