import os
import re
import argparse
import requests
from datetime import datetime
from dotenv import load_dotenv
import json
import glob

# Load environment variables
load_dotenv()

# Notion API configuration
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# Ollama API configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")  # Default to llama3 if not specified

def load_txt_transcript(file_path):
    """Load transcript from TXT file format."""
    try:
        with open(file_path, 'r') as file:
            content = file.read()
            
        # Parse the transcript metadata and content
        transcript = {}
        
        # Extract session ID from header
        session_match = re.search(r'Transcript Session: ([a-f0-9-]+)', content)
        if session_match:
            transcript['session_id'] = session_match.group(1)
        
        # Extract start date and time
        start_match = re.search(r'Started: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', content)
        if start_match:
            transcript['start_time'] = start_match.group(1)
        
        # Extract end date and time
        end_match = re.search(r'Session ended: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', content)
        if end_match:
            transcript['end_time'] = end_match.group(1)
        
        # Extract lines with timestamps
        transcript_content = []
        timestamp_pattern = r'\[(\d{2}:\d{2}:\d{2})\]\s+(.*)'
        
        for line in content.split('\n'):
            timestamp_match = re.search(timestamp_pattern, line)
            if timestamp_match:
                time = timestamp_match.group(1)
                text = timestamp_match.group(2).strip()
                transcript_content.append({
                    'timestamp': time,
                    'content': text
                })
        
        transcript['content'] = transcript_content
        
        return transcript
    except Exception as e:
        print(f"Error loading transcript: {e}")
        return None

def process_transcript_to_notion():
    """Process the latest transcript and create a Notion page."""
    try:
        # Get the latest transcript file
        print("Getting latest transcript file...")
        transcript_file = get_latest_transcript_file()
        if not transcript_file:
            return "No transcript file found."
        
        print(f"Found transcript file: {transcript_file}")
        
        # Load and analyze transcript
        print("Loading transcript...")
        transcript = load_txt_transcript(transcript_file)
        if not transcript:
            return "Failed to load transcript."
        
        print("Transcript loaded successfully")
        
        # Analyze transcript
        print("Analyzing transcript with Ollama...")
        analysis = analyze_transcript_with_ollama(transcript)
        print("Analysis complete")
        
        # Extract just the filename without extension
        base_filename = os.path.splitext(os.path.basename(transcript_file))[0]
        print(f"Base filename: {base_filename}")
        
        # Define directories
        minutes_dir = "minutes"
        summaries_dir = "summaries"
        print(f"Using minutes directory: {minutes_dir}")
        print(f"Using summaries directory: {summaries_dir}")
        
        # Create Notion page
        print("Creating Notion page...")
        page_url = create_notion_page(
            analysis, 
            transcript_file, 
            transcript, 
            minutes_dir=minutes_dir, 
            summaries_dir=summaries_dir
        )
        
        if page_url:
            return f"Notion page created successfully: {page_url}"
        else:
            return "Failed to create Notion page."
    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        print(f"Error creating Notion page: {str(e)}")
        print(f"Traceback: {traceback_str}")
        return f"Error creating Notion page: {str(e)}"


def load_minutes(transcript_file, minutes_dir="minutes"):
    """Load minutes from a corresponding file in minutes directory."""
    try:
        # Extract base filename without extension
        base_name = os.path.basename(transcript_file)
        base_name = os.path.splitext(base_name)[0]
        print(f"Looking for minutes file for base_name: {base_name} in {minutes_dir}")
        
        # Look for a matching minutes file
        minutes_path = os.path.join(minutes_dir, f"{base_name}.txt")
        print(f"Checking for minutes at: {minutes_path}")
        
        # If direct match not found, try a different name pattern
        if not os.path.exists(minutes_path):
            minutes_path = os.path.join(minutes_dir, f"{base_name}_minutes.txt")
            print(f"Not found, checking: {minutes_path}")
        
        # If still not found, get the latest minutes file
        if not os.path.exists(minutes_path):
            print(f"Exact match not found, looking for any .txt file in {minutes_dir}")
            search_pattern = os.path.join(minutes_dir, "*.txt")
            minutes_files = glob.glob(search_pattern)
            print(f"Found minutes files: {minutes_files}")
            
            if minutes_files:
                latest_file = max(minutes_files, key=os.path.getmtime)
                minutes_path = latest_file
                print(f"Using latest minutes file: {latest_file}")
            else:
                print("No minutes files found")
                return None
        
        # Load the minutes content
        print(f"Loading minutes from: {minutes_path}")
        with open(minutes_path, 'r', encoding='utf-8') as file:
            content = file.read().strip()
            print(f"Minutes loaded, length: {len(content)}")
            return content
    except Exception as e:
        print(f"Warning: Could not load minutes: {e}")
        return None

def analyze_transcript_with_ollama(transcript):
    """
    Use Ollama to analyze the transcript and extract key information.
    
    Returns:
        dict: Analysis results containing meeting title, action items, etc.
    """
    # Convert transcript to a readable format for the model
    transcript_text = ""
    if 'start_time' in transcript:
        transcript_text += f"Meeting started: {transcript['start_time']}\n\n"
    
    for entry in transcript.get('content', []):
        transcript_text += f"[{entry['timestamp']}] {entry['content']}\n"
    
    # Prepare prompt for Ollama
    prompt = f"""
    You are an AI assistant tasked with analyzing meeting transcripts and extracting structured information.
    
    Below is a transcript of a meeting. Please analyze it and return a JSON with the following structure:
    {{
        "title": "Brief descriptive title for the meeting",
        "key_points": ["List of 3-5 key points discussed"],
        "action_items": [
            {{
                "task": "Description of task",
                "assignee": "Name of person assigned (if available)",
                "due_date": "Due date (if available)"
            }}
        ],
        "minutes": ["Chronological list of important discussion points or decisions made during the meeting"],
        "participants": ["List of participant names"],
        "tags": ["Relevant tags/categories for this meeting"]
    }}
    
    The transcript is as follows:
    {transcript_text}
    
    Please format your response as valid JSON without any additional text or explanation.
    """
    
    # Send request to Ollama
    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=60  # Add timeout to prevent hanging
        )
        
        if response.status_code != 200:
            print(f"Error from Ollama API: {response.status_code} - {response.text}")
            return None
        
        # Extract and parse the response
        try:
            result = response.json()
            if "response" in result:
                # Try to find JSON in the response
                response_text = result["response"]
                print(f"Received response from Ollama. Parsing JSON...")
                
                # Find JSON content (sometimes the model might wrap the JSON in backticks)
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_text = response_text[json_start:json_end]
                    try:
                        parsed_json = json.loads(json_text)
                        print("Successfully parsed JSON response")
                        return parsed_json
                    except json.JSONDecodeError as e:
                        print(f"JSON parse error: {e}")
                        print(f"Problematic JSON text: {json_text[:100]}...")
                        # Fallback: Create a minimal valid JSON
                        return {
                            "title": "Meeting Notes",
                            "key_points": ["Discussion of project details"],
                            "action_items": [],
                            "minutes": [],
                            "participants": ["Meeting participants"],
                            "tags": ["meeting"]
                        }
                else:
                    print("Could not find JSON object in Ollama response")
            else:
                print("Response from Ollama did not contain expected 'response' field")
            
            # Fallback with minimal content
            return {
                "title": "Meeting Notes",
                "key_points": ["Discussion of project details"],
                "action_items": [],
                "minutes": [],
                "participants": ["Meeting participants"],
                "tags": ["meeting"]
            }
            
        except Exception as e:
            print(f"Error processing Ollama response: {e}")
            # Return a minimal valid structure as fallback
            return {
                "title": "Meeting Notes",
                "key_points": ["Discussion of project details"],
                "action_items": [],
                "minutes": [],
                "participants": ["Meeting participants"],
                "tags": ["meeting"]
            }
            
    except requests.exceptions.RequestException as e:
        print(f"Error making request to Ollama: {e}")
        # Return a minimal valid structure as fallback
        return {
            "title": "Meeting Notes",
            "key_points": ["Discussion of project details"],
            "action_items": [],
            "minutes": [],
            "participants": ["Meeting participants"],
            "tags": ["meeting"]
        }

def create_notion_page(analysis, transcript_file, transcript, minutes_dir="minutes", summaries_dir="summaries"):
    """Create a Notion page with the meeting information."""
    if not analysis:
        print("No analysis available to create Notion page.")
        return
    
    # Load summary and minutes from their respective directories
    print(f"Loading summary from directory: {summaries_dir}")
    summary = load_summary(transcript_file, summaries_dir)
    print(f"Loading minutes from directory: {minutes_dir}")
    minutes_content = load_minutes(transcript_file, minutes_dir)
    # Use meeting date if available, otherwise current date
    meeting_date = None
    if 'start_time' in transcript:
        try:
            meeting_date = transcript['start_time'].split()[0]  # Extract just the date part
        except:
            pass
    
    if not meeting_date:
        meeting_date = datetime.now().strftime("%Y-%m-%d")
    
    # Create page content
    page_content = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Title": {
               "rich_text": [{"type": "text", "text": {"content": analysis.get("title", "Meeting Notes")}}]
            },
            "Date": {
                "date": {"start": meeting_date}
            },
            "Tags": {
                "multi_select": [{"name": tag} for tag in analysis.get("tags", [])]
            }
        },
        "children": [
            # Summary section
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Summary"}}]
                }
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": summary}}]  # Using the loaded summary
                }
            },
            
            # Participants section
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Participants"}}]
                }
            },
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": ", ".join(analysis.get("participants", ["Unknown"]))}}]
                }
            },
            
            # Key Points section
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Key Points"}}]
                }
            }
        ]
    }
    
    # Add key points as bullet points
    for point in analysis.get("key_points", []):
        page_content["children"].append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": {"content": point}}]
            }
        })
    
    # Add Minutes section from minutes.txt file
    page_content["children"].append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "Meeting Minutes"}}]
        }
    })
    
    if minutes_content:
        # Parse and add structured minutes content
        lines = minutes_content.split('\n')
        i = 0
        
        # Skip empty lines at the beginning
        while i < len(lines) and (not lines[i] or lines[i].isspace()):
            i += 1
            
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                i += 1
                continue
                
            # Handle headings with ** markers
            if line.startswith('**') and '**' in line[2:]:
                # Extract the heading text without ** markers
                heading_text = line.strip('*').strip()
                
                # Add main heading as h3
                page_content["children"].append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": heading_text}}]
                    }
                })
            
            # Handle bullet points
            elif line.startswith('*') and not line.startswith('**'):
                # Get the bullet point text
                bullet_text = line[1:].strip()
                
                # Handle nested bullet content that may span multiple lines
                j = i + 1
                while j < len(lines) and lines[j] and not lines[j].startswith('*') and not lines[j].startswith('**'):
                    bullet_text += " " + lines[j].strip()
                    j += 1
                i = j - 1  # Will be incremented at the end of the loop
                
                # Add as bulleted list item
                page_content["children"].append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": bullet_text}}]
                    }
                })
            
            # Handle labeled content like "Date and Time: 2025-05-09..."
            elif ':' in line and not line.startswith('*'):
                parts = line.split(':', 1)
                if len(parts) == 2:
                    label, content = parts[0].strip(), parts[1].strip()
                    
                    # Check if this is a label with content
                    if content:
                        page_content["children"].append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [
                                    {"type": "text", "text": {"content": label + ": "}, "annotations": {"bold": True}},
                                    {"type": "text", "text": {"content": content}}
                                ]
                            }
                        })
                    else:
                        # This is a subheading without **
                        page_content["children"].append({
                            "object": "block",
                            "type": "heading_3",
                            "heading_3": {
                                "rich_text": [{"type": "text", "text": {"content": label}}]
                            }
                        })
            
            # Handle regular text
            else:
                # Check if this is a continuation of previous text
                page_content["children"].append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": line}}]
                    }
                })
            
            i += 1
    else:
        # Fallback to using LLM-generated minutes if minutes.txt isn't available
        page_content["children"].append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": "No formatted minutes available. See key points and transcript below."}}]
            }
        })
        
        # Add minutes from Ollama analysis as numbered list items (as fallback)
        for i, minute in enumerate(analysis.get("minutes", []), 1):
            page_content["children"].append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": minute}}]
                }
            })
    
    # Add Action Items section
    page_content["children"].append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "Action Items"}}]
        }
    })
    
    # Add action items as to-do items
    for item in analysis.get("action_items", []):
        task_text = item.get("task", "")
        if "assignee" in item and item["assignee"]:
            task_text += f" (Assigned to: {item['assignee']})"
        if "due_date" in item and item["due_date"]:
            task_text += f" (Due: {item['due_date']})"
            
        page_content["children"].append({
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"type": "text", "text": {"content": task_text}}],
                "checked": False
            }
        })
    
    # Add transcript section
    page_content["children"].append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "Full Transcript"}}]
        }
    })
    
    page_content["children"].append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": f"Source file: {os.path.basename(transcript_file)}"}}]
        }
    })
    
    # Add the full transcript as a series of paragraphs with timestamps
    for entry in transcript.get('content', []):
        page_content["children"].append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {"type": "text", "text": {"content": f"[{entry['timestamp']}] "}, "annotations": {"bold": True}},
                    {"type": "text", "text": {"content": entry['content']}}
                ]
            }
        })
    
    # Create page in Notion
    response = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json=page_content
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"Notion page created successfully: {result.get('url')}")
        return result.get('url')
    else:
        print(f"Error creating Notion page: {response.status_code} - {response.text}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Process meeting transcript and create Notion page")
    parser.add_argument("transcript_file", help="Path to the transcript TXT file")
    parser.add_argument("--minutes-dir", help="Directory containing minutes files", default="minutes")
    parser.add_argument("--summaries-dir", help="Directory containing summary files", default="summaries")
    parser.add_argument("--skip-analysis", action="store_true", help="Skip Ollama analysis and use only minutes.txt")
    args = parser.parse_args()    

    # Check for required environment variables
    if not NOTION_API_KEY:
        print("Error: NOTION_API_KEY environment variable is not set")
        return
    
    if not NOTION_DATABASE_ID:
        print("Error: NOTION_DATABASE_ID environment variable is not set")
        return
    
    # Load and process transcript
    print(f"Loading transcript from {args.transcript_file}...")
    transcript = load_txt_transcript(args.transcript_file)
    if not transcript:
        return
    
    # Initialize analysis with default values
    analysis = {
        "title": "Meeting Notes",
        "key_points": ["Discussion of project details"],
        "action_items": [],
        "minutes": [],
        "participants": ["Meeting participants"],
        "tags": ["meeting"]
    }
    
    # Only run Ollama analysis if not skipped
    if not args.skip_analysis:
        print(f"Analyzing transcript with Ollama ({OLLAMA_MODEL})...")
        try:
            ollama_analysis = analyze_transcript_with_ollama(transcript)
            if ollama_analysis:
                analysis = ollama_analysis
            else:
                print("Warning: Automated analysis failed. Using default values.")
        except Exception as e:
            print(f"Error during transcript analysis: {e}")
            print("Using default values instead.")
    else:
        print("Skipping Ollama analysis as requested.")
    
    # Create Notion page
    print("Creating Notion page...")
    
    # Pass the minutes file path to create_notion_page
    page_url = create_notion_page(analysis, args.transcript_file, transcript, args.minutes)
    
    if page_url:
        print(f"Success! Notion page created: {page_url}")
    else:
        print("Failed to create Notion page.")

if __name__ == "__main__":
    main()
