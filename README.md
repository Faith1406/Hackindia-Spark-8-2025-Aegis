AI Meeting Assistant
Automatically summarize meeting transcripts, generate minutes, and publish structured notes to Notion using Gemini, Ollama, and Slack integration.

Overview
The AI Meeting Assistant is a Flask-based web application that streamlines post-meeting workflows by:

Fetching transcripts from a transcription service

Analyzing them via local LLM (Ollama)

Posting to Notion and Slack

Generating minutes and summaries via multi-agent coordination (powered by the Palette framework)

It supports real-time transcript ingestion, structured knowledge extraction, and automated publishing of meeting artifacts.

Key Features
✅ Real-time transcript ingestion from HTTP-based sources

🧠 Transcript analysis using Ollama (LLaMA3)

🗂 Structured Notion pages with action items, summaries, and minutes

📤 Slack integration for transcription sharing

👥 Modular agent teams (Coordinator, Virtual Assistant, Data Analysts, Watchdog)

🛠 Built with extensibility in mind using Palette (multi-agent orchestration)

Installation
Clone the repository

bash
Copy
Edit
git clone https://github.com/your-username/ai-meeting-assistant.git
cd ai-meeting-assistant
Install dependencies

bash
Copy
Edit
pip install -r requirements.txt
Set environment variables
Create a .env file in the project root:

env
Copy
Edit
GEMINI_API_KEY=your_gemini_key
SLACK_BOT_TOKEN=your_slack_token
SLACK_CHANNEL_ID=your_channel_id
NOTION_API_KEY=your_notion_key
NOTION_DATABASE_ID=your_database_id
TRANSCRIPTION_DIRECTORIES=transcriptions
OLLAMA_MODEL=llama3
Run the server

bash
Copy
Edit
python app.py
Usage
Visit http://localhost:5000 in your browser.

Paste your command in the form. Examples:

va: Hello, what can you do?

data: summarize

data: minutes

check (system health)

API Endpoint
You can also POST to /process_live_transcript to trigger full processing of a new transcript:

bash
Copy
Edit
curl -X POST http://localhost:5000/process_live_transcript
Output Artifacts
📝 transcriptions/ — Raw transcripts

📄 summaries/ — AI-generated summaries

🗒 minutes/ — Structured minutes of meetings

📋 logs/ — Raw logs for debugging

Architecture
arduino
Copy
Edit
                 ┌────────────┐
                 │Transcript  │
                 │ Source API │
                 └────┬───────┘
                      │
                      ▼
          ┌────────────────────┐
          │ Flask Web Server   │
          └────┬──────┬────────┘
               │      │
        ┌──────▼──┐ ┌─▼─────────┐
        │Palette  │ │Notion API │
        │Framework│ └───────────┘
        └──┬──────┘
           │
  ┌────────▼─────────┐
  │Agent Teams       │
  │- Coordinator     │
  │- Virtual Assistant│
  │- Data Analysts   │
  │- Watchdog        │
  └──────────────────┘
Contributing
Fork the repository.

Make your changes in a branch.

Ensure code follows the style of the rest of the project.

Submit a pull request with a clear description of your change.

License
This project is licensed under the MIT License.
