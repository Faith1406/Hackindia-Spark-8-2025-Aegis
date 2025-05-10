import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
import glob
import re
from datetime import datetime

load_dotenv()

def extract_datetime_from_file(file_path):
    """
    Extracts the date and time from the content of a file.
    Assumes the date and time are in the first line of the file in a standard format.
    Example format: "Date: 2025-05-09 14:30:00"
    """
    try:
        with open(file_path, "r") as file:
            first_line = file.readline().strip()
            
            # Adjust this regex pattern to match your date format in the file
            date_time_match = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', first_line)
            
            if date_time_match:
                return datetime.strptime(date_time_match.group(), "%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
    
    # If we can't extract a date, use the file modification time as a fallback
    try:
        mtime = os.path.getmtime(file_path)
        return datetime.fromtimestamp(mtime)
    except:
        return None

def get_latest_transcription(directories):
    latest_file = None
    latest_datetime = None
    latest_content = ""

    # Debug: Print the directories we're searching
    print(f"Searching for transcriptions in: {directories}")

    # Loop through each directory specified in the .env file
    for directory in directories:
        directory = directory.strip()  # Remove any whitespace
        search_pattern = os.path.join(directory, "*.txt")
        files = glob.glob(search_pattern)  # Search for text files only
        
        # Debug: Print the files found in each directory
        print(f"Files found in {directory}: {len(files)}")
        
        if not files:
            continue

        for file in files:
            file_datetime = extract_datetime_from_file(file)
            if file_datetime and (latest_datetime is None or file_datetime > latest_datetime):
                latest_datetime = file_datetime
                latest_file = file
                with open(file, "r") as f:
                    latest_content = f.read()
    
    return latest_file, latest_content

def send_latest_transcription_to_slack():
    token = os.getenv("SLACK_BOT_TOKEN")
    channel_id = os.getenv("SLACK_CHANNEL_ID")
    # CHANGED: Use TRANSCRIPTION_DIRECTORIES (plural) instead of TRANSCRIPTION_DIRECTORY (singular)
    transcription_directories = os.getenv("TRANSCRIPTION_DIRECTORIES")
    
    # Debug: Print the environment variables
    print(f"SLACK_BOT_TOKEN exists: {token is not None}")
    print(f"SLACK_CHANNEL_ID exists: {channel_id is not None}")
    print(f"TRANSCRIPTION_DIRECTORIES value: {transcription_directories}")

    # CHANGED: Updated error message to match the variable name
    if not token or not channel_id or not transcription_directories:
        print("Error: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, or TRANSCRIPTION_DIRECTORIES is not set in the .env file.")
        return

    # Split the directories from comma-separated values
    directories = transcription_directories.split(",")
    latest_file, content = get_latest_transcription(directories)
    
    if not latest_file:
        print("No transcription files with valid date and time found.")
        return

    print(f"Found latest file for Slack: {latest_file}")
    
    client = WebClient(token=token)

    try:
        # Post the latest transcription as a message to the specified Slack channel
        response = client.chat_postMessage(
            channel=channel_id,
            text=f"*Latest Transcription ({os.path.basename(latest_file)}):*\n```{content}```"
        )
        print("Latest transcription posted successfully.")
    except SlackApiError as e:
        print(f"Error posting transcription: {e.response['error']}")

if __name__ == "__main__":
    send_latest_transcription_to_slack()
