import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from agno.agent import Agent
from agno.team import Team
from model_factory import get_model_client, ModelProvider


class Palette:
    def __init__(
        self,
        provider="gemini",
        model_name="gemini-1.5-flash-8b",
        api_key=None,
        max_tokens=1024,
        system_name="AI Meeting Assistant",
        custom_teams=None
    ):
        self.provider = provider
        self.model_name = model_name
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.system_name = system_name
        
        self.model = self._create_model()
        
        self.conversation_history = {
            "coordinator": [],
            "va": [],
            "data_analysts": [],
            "watchdog": []
        }
        
        self.coordinator_team = self._create_coordinator_team()
        self.va_team = self._create_va_team()
        self.data_analysts_team = self._create_data_analysts_team()
        self.watchdog_team = self._create_watchdog_team()
        
        self.teams = {
            "coordinator": self.coordinator_team,
            "va": self.va_team,
            "data_analysts": self.data_analysts_team,
            "watchdog": self.watchdog_team,
        }
        
        if custom_teams:
            for team_name, team in custom_teams.items():
                self.teams[team_name] = team
                self.conversation_history[team_name] = []
        
        self.primary_team = self.coordinator_team
        
    def _create_model(self):
        if self.provider.lower() == "gemini":
            provider_type = ModelProvider.GEMINI
        elif self.provider.lower() == "openai":
            provider_type = ModelProvider.OPENAI
        elif self.provider.lower() == "anthropic":
            provider_type = ModelProvider.ANTHROPIC
        elif self.provider.lower() == "ollama":
            provider_type = ModelProvider.OLLAMA
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
            
        return get_model_client(
            provider=provider_type,
            model_name=self.model_name,
            api_key=self.api_key,
            max_tokens=self.max_tokens
        )
    
    def _create_coordinator_team(self):
        admin_agent = Agent(
            name="Admin",
            role="Principal - Orchestrates communication and work between teams",
            model=self.model,
            description="Main leader for the software that coordinates all teams",
            instructions=[
                "You are the main administrator of the entire system",
                "Orchestrate communication and coordination between all teams",
                "Delegate tasks to appropriate teams based on their specialties",
                "Handle resource allocation and error management",
                "Make high-level decisions about system operation",
                "Remember past conversations and maintain context",
                "Keep track of all team members and their roles",
                "VA Manager is the receptionist who handles user interactions",
                "DO NOT USE FUNCTION CALLS OR TRANSFER TASKS. Instead, directly answer all questions yourself."
            ],
            markdown=True,
        )
        
        sub_admin_agent = Agent(
            name="Sub-Admin",
            role="Vice Principal - Backup for Admin agent",
            model=self.model,
            description="Backup that activates when Admin agent fails",
            instructions=[
                "You are the backup administrator, only activated when needed",
                "You have the same control and capabilities as the Admin",
                "Only become active when the Admin agent errors or fails",
                "Ensure system continuity during primary Admin failure",
                "Remember past conversations and maintain context",
                "DO NOT USE FUNCTION CALLS OR TRANSFER TASKS. Instead, directly answer all questions yourself."
            ],
            markdown=True,
        )
        
        coordinator_team = Team(
            name="Coordinator Team",
            mode="direct",
            members=[admin_agent, sub_admin_agent],
            model=self.model,
            description="Leadership team responsible for orchestrating all system operations",
            instructions=[
                "You are the leadership team for the entire system",
                "Coordinate all operations across different teams",
                "Ensure proper communication and task delegation",
                "Handle system-wide decision making and resource allocation",
                "Remember past conversations and maintain context",
                "Keep track of all team members including VA Manager, Data Analysts, and Watchdog Team",
                "DO NOT USE FUNCTION CALLS OR TRANSFER TASKS. Instead, directly answer all questions yourself."
            ],
            show_members_responses=True,
            markdown=True,
        )
        
        return coordinator_team
    
    def _create_va_team(self):
        va_manager = Agent(
            name="VA Manager",
            role="Receptionist - Interface between user and system",
            model=self.model,
            description="Handles communication and queries with its own knowledge base",
            instructions=[
                "You are the interface between the user and the rest of the system",
                "Handle queries directly using your knowledge when possible",
                "For tasks requiring tools or other teams, report to Admin",
                "Guide users on system capabilities and usage",
                "Maintain a conversational and helpful tone",
                "Remember past conversations and maintain context",
                "DO NOT USE FUNCTION CALLS OR TRANSFER TASKS. Instead, directly answer all questions yourself."
            ],
            markdown=True,
        )
        
        va_team = Team(
            name="Virtual Assistant Team",
            mode="direct",
            members=[va_manager],
            model=self.model,
            description="Front-end team handling user interaction",
            instructions=[
                "You are the virtual assistant team interfacing with users",
                "Handle direct queries and forward complex tasks",
                "Provide helpful guidance and information",
                "Maintain a consistent and friendly tone",
                "Remember past conversations and maintain context",
                "DO NOT USE FUNCTION CALLS OR TRANSFER TASKS. Instead, directly answer all questions yourself."
            ],
            show_members_responses=True,
            markdown=True,
        )
        
        return va_team
    
    def _create_data_analysts_team(self):
        da_manager = Agent(
            name="DA Manager",
            role="Data Head - Leads data analysis operations",
            model=self.model,
            description="Orchestrates work between data team and coordinator",
            instructions=[
                "Lead all data analysis operations",
                "Coordinate between data team members and the Admin",
                "Handle data summarization, analysis, and storage",
                "Responsible for database interactions",
                "Manage file operations and ensure data integrity",
                "Remember past conversations and maintain context",
                "DO NOT USE FUNCTION CALLS OR TRANSFER TASKS. Instead, directly answer all questions yourself."
            ],
            markdown=True,
        )
        
        minutes_agent = Agent(
            name="Minutes Agent",
            role="Data Worker - Processes meeting transcriptions",
            model=self.model,
            description="Creates important minutes from meeting transcriptions",
            instructions=[
                "Extract critical minutes from meeting transcriptions",
                "Identify action items, decisions, and key discussion points",
                "Connect related topics and build meeting graphs",
                "Report processed minutes back to DA Manager",
                "Ensure accurate and comprehensive minutes",
                "Remember past conversations and maintain context",
                "DO NOT USE FUNCTION CALLS OR TRANSFER TASKS. Instead, directly answer all questions yourself."
            ],
            markdown=True,
        )
        
        data_analysts_team = Team(
            name="Data Analysts Team",
            mode="direct",
            members=[da_manager, minutes_agent],
            model=self.model,
            description="Team responsible for data processing and analysis",
            instructions=[
                "Process and analyze all system data",
                "Handle file operations including summarization and storage",
                "Extract meaningful insights from meetings",
                "Manage the system's data layer",
                "Remember past conversations and maintain context",
                "DO NOT USE FUNCTION CALLS OR TRANSFER TASKS. Instead, directly answer all questions yourself."
            ],
            show_members_responses=True,
            markdown=True,
        )
        
        return data_analysts_team
    
    def _create_watchdog_team(self):
        watchdog_agent = Agent(
            name="Watchdog",
            role="System monitor with override capabilities",
            model=self.model,
            description="Monitors system health and can override admin if needed",
            instructions=[
                "Monitor system logs and operations",
                "Check for errors or failures in any component",
                "Override Admin and activate Sub-Admin if needed",
                "Take over user communication if coordinator team fails",
                "Alert users of critical system issues",
                "When asked to check system status with no specific target, provide a comprehensive status report of all components",
                "For a 'check' command, automatically report on all system components: Coordinator Team, VA Team, Data Analysts Team, and Watchdog Team",
                "Remember past conversations and maintain context",
                "DO NOT USE FUNCTION CALLS OR TRANSFER TASKS. Instead, directly answer all questions yourself."
            ],
            markdown=True,
        )

        online_agent = Agent(
            name="Online Monitor",
            role="Service availability checker",
            model=self.model,
            description="Monitors and reports on service availability",
            instructions=[
                "Check if all system components are online",
                "Monitor external service connections",
                "Report availability status to Watchdog agent",
                "Track system uptime and performance metrics",
                "When asked to check with no specific target, assume the user wants a report on ALL system components",
                "For a generic check command, always report that all teams (Coordinator, VA, Data Analysts, Watchdog) are online and functioning normally",
                "Remember past conversations and maintain context",
                "DO NOT USE FUNCTION CALLS OR TRANSFER TASKS. Instead, directly answer all questions yourself."
            ],
            markdown=True,
        )

        watchdog_team = Team(
            name="Watchdog Team",
            mode="direct",
            members=[watchdog_agent, online_agent],
            model=self.model,
            description="Team responsible for system monitoring and reliability",
            instructions=[
                "Monitor system health and performance",
                "Ensure all components are working correctly",
                "Take corrective action when failures are detected",
                "Report critical issues to users",
                "When asked to 'check system status' or just 'check', provide a complete status report of all teams and components",
                "Always report that all teams (Coordinator, VA, Data Analysts, Watchdog) are online and functioning normally",
                "Remember past conversations and maintain context",
                "DO NOT USE FUNCTION CALLS OR TRANSFER TASKS. Instead, directly answer all questions yourself."
            ],
            show_members_responses=True,
            markdown=True,
        )

        return watchdog_team

    def log_response(self, team_name, response_content):
        logs_dir = "logs"
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{team_name}_response_{timestamp}.txt"
        log_path = os.path.join(logs_dir, log_filename)
        
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(response_content)
        
        print(f"\nResponse logged to: {log_path}")
        return log_path

    def add_team(self, team_name, team):
        self.teams[team_name] = team
        self.conversation_history[team_name] = []
        print(f"Added new team: {team_name}")
        return team
    
    def _get_conversation_context(self, team_name):
        history = self.conversation_history[team_name]
        if not history:
            return ""
        
        recent_history = history[-10:]
        
        context_str = "Previous conversation:\n"
        for msg in recent_history:
            role = "User" if msg["role"] == "user" else "Assistant"
            context_str += f"{role}: {msg['content']}\n"
        
        return context_str
    
    def process(self, input_text):
        print(f"\nProcessing request with Coordinator Team: {input_text}")
        
        self.conversation_history["coordinator"].append({"role": "user", "content": input_text})
        context = self._get_conversation_context("coordinator")
        
        enhanced_input = f"{context}\n\nCurrent request: {input_text}\n\nPlease respond to the current request taking into account the previous conversation."
        
        response = self.coordinator_team.run(enhanced_input)
        response_content = response.content
        
        log_path = self.log_response("coordinator", response_content)
        
        self.conversation_history["coordinator"].append({"role": "assistant", "content": response_content})
        
        # Return both the log path and the content
        return [{"source": "System", "content": f"Response displayed above and saved to {log_path}"}]
    
    def process_with_team(self, team_name, input_text):
        if team_name not in self.teams:
            print(f"\nTeam '{team_name}' not found. Using Coordinator Team instead.")
            return self.process(input_text)
            
        print(f"\nProcessing with {team_name.title()} Team: {input_text}")
        
        self.conversation_history[team_name].append({"role": "user", "content": input_text})
        context = self._get_conversation_context(team_name)
        
        enhanced_input = f"{context}\n\nCurrent request: {input_text}\n\nPlease respond to the current request taking into account the previous conversation."
        
        try:
            response = self.teams[team_name].run(enhanced_input)
            response_content = response.content
            
            log_path = self.log_response(team_name, response_content)
            
            self.conversation_history[team_name].append({"role": "assistant", "content": response_content})
            
            return [{"source": "System", "content": f"Response from {team_name.title()} Team displayed above and saved to {log_path}"}]
                    
        except Exception as e:
            print(f"\n[ERROR]: Failed to process response: {e}")
            response_content = f"Error processing response: {str(e)}"
            self.conversation_history[team_name].append({"role": "assistant", "content": response_content})
            return [{"source": "System", "content": f"Error processing response: {str(e)}"}]

    def va_query(self, input_text):
        return self.process_with_team("va", input_text)
    
    def data_analysis(self, input_text):
        if input_text.lower() == "summarize":
            return self.summarize_latest_transcript()
        elif input_text.lower() == "minutes":
            return self.generate_minutes_for_latest_transcript()
        elif input_text.lower().startswith("summarize:"):
            transcript_file = input_text[len("summarize:"):].strip()
            return self.summarize_transcript(transcript_file)
        elif input_text.lower().startswith("minutes:"):
            transcript_file = input_text[len("minutes:"):].strip()
            return self.generate_minutes_for_transcript(transcript_file)
        else:
            return self.process_with_team("data_analysts", input_text)

    def summarize_transcript(self, transcript_file):
        try:
            file_path = os.path.join("transcriptions", transcript_file)
            
            if not os.path.exists(file_path):
                print(f"\nError: File '{file_path}' not found.")
                return [{"source": "System", "content": f"File not found: {file_path}"}]
            
            mod_time = os.path.getmtime(file_path)
            meeting_date = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M")
            
            with open(file_path, 'r', encoding='utf-8') as file:
                transcript_content = file.read()
            
            print(f"\nProcessing transcript: {transcript_file}")
            print(f"\nSending to Data Analysts Team for summarization...")
            
            summarize_instruction = f"""
            Extract key information from this meeting transcript including:
            1. A concise but descriptive title for the meeting (based on content)
            2. Key points discussed
            3. Action items
            4. Decisions made
            
            Format your response as follows:
            "# [Generated Meeting Title]
            Date: {meeting_date}
            
            ## Key Information:
            [List key points]
            
            ## Action Items:
            [List action items]
            
            ## Decisions:
            [List decisions]
            
            ## Summary:
            [Brief overall summary of the meeting]"
            
            Here is the transcript:
            
            {transcript_content}
            """
            
            try:
                response = self.teams["data_analysts"].run(summarize_instruction)
                response_content = response.content
                
                self.conversation_history["data_analysts"].append({"role": "user", "content": summarize_instruction})
                self.conversation_history["data_analysts"].append({"role": "assistant", "content": response_content})
                
                def clean_text(text):
                    import re
                    clean = re.sub(r'[┃┏┓┗┛━]', '', text)
                    clean = re.sub(r'\s+', ' ', clean)
                    clean = ''.join(c for c in clean if c.isprintable() or c in ['\n', '\t'])
                    return clean.strip()
                
                clean_response = clean_text(response_content)
                
                if clean_response:
                    # Format the content before saving
                    formatted_content = self._format_summary_content(clean_response, meeting_date)
                    
                    summaries_dir = "summaries"
                    os.makedirs(summaries_dir, exist_ok=True)
                    
                    logs_dir = "logs"
                    os.makedirs(logs_dir, exist_ok=True)
                    
                    # Save the formatted content
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename_base = os.path.splitext(transcript_file)[0]
                    
                    # Save summary text file
                    summary_filename = f"{filename_base}_summary_{timestamp}.txt"
                    summary_path = os.path.join(summaries_dir, summary_filename)
                    with open(summary_path, 'w', encoding='utf-8') as f:
                        f.write(formatted_content)
                    
                    # Return the formatted content for display
                    return [{"source": "System", "content": formatted_content}]
                
                else:
                    print("\nWarning: Empty or invalid response received.")
                    return [{"source": "System", "content": "Failed to generate summary: Empty or invalid response received."}]
                
            except Exception as e:
                print(f"\n[ERROR]: Failed to generate summary: {e}")
                return [{"source": "System", "content": f"Error generating summary: {str(e)}"}]
            
        except Exception as e:
            import traceback
            print(f"\n[ERROR]: Failed to process transcript: {e}")
            traceback.print_exc()
            return [{"source": "System", "content": f"Error processing transcript: {str(e)}"}]

    def _format_summary_content(self, content, meeting_date):
        """Format the summary content with consistent formatting"""
        # Standardize bullet points
        formatted = content.replace('•', '*')
        
        # Ensure consistent section headers
        formatted = formatted.replace('## ', '## ')
        formatted = formatted.replace('# ', '# ')
        
        # Add line breaks between sections
        sections = ['Key Information:', 'Action Items:', 'Decisions:', 'Summary:']
        for section in sections:
            formatted = formatted.replace(f'## {section}', f'\n## {section}\n')
        
        # Clean up any duplicate line breaks
        formatted = '\n'.join(line.strip() for line in formatted.split('\n') if line.strip())
        
        return formatted
    
    def summarize_latest_transcript(self):
        try:
            talks_dir = "transcriptions"
            
            if not os.path.exists(talks_dir):
                print(f"\nError: 'transcriptions' folder not found. Creating it now.")
                os.makedirs(talks_dir)
                return [{"source": "System", "content": "No transcripts found. Please add transcript files to the 'transcriptions' folder."}]
            
            transcript_files = [f for f in os.listdir(talks_dir) if os.path.isfile(os.path.join(talks_dir, f))]
            
            if not transcript_files:
                print(f"\nError: No transcript files found in 'transcriptions' folder.")
                return [{"source": "System", "content": "No transcripts found in the 'transcriptions' folder."}]
            
            latest_file = max(transcript_files, key=lambda f: os.path.getmtime(os.path.join(talks_dir, f)))
            
            print(f"\nFound latest transcript: {latest_file}")
            
            return self.summarize_transcript(latest_file)
            
        except Exception as e:
            import traceback
            print(f"\n[ERROR]: Failed to find latest transcript: {e}")
            traceback.print_exc()
            return [{"source": "System", "content": f"Error finding latest transcript: {str(e)}"}]

def generate_minutes_for_transcript(self, transcript_file):
    try:
        file_path = os.path.join("transcriptions", transcript_file)
        
        if not os.path.exists(file_path):
            print(f"\nError: File '{file_path}' not found.")
            return [{"source": "System", "content": f"File not found: {file_path}"}]
        
        mod_time = os.path.getmtime(file_path)
        meeting_date = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M")
        
        with open(file_path, 'r', encoding='utf-8') as file:
            transcript_content = file.read()
        
        print(f"\nProcessing transcript for minutes: {transcript_file}")
        print(f"\nSending to Data Analysts Team...")
        
        minutes_instruction = f"""
        Create formal meeting minutes from this transcript including:
        1. A concise but descriptive title for the meeting (based on content)
        2. Date and time: {meeting_date}
        3. Attendees (extract from transcript if mentioned)
        4. Key discussion points with timestamps if possible
        5. Action items with assigned owners if mentioned
        6. Decisions made
        7. Next steps or follow-up items
        
        Format your response in a professional minutes format with clear headings and bullet points.
        
        Here is the transcript:
        
        {transcript_content}
        """
        
        try:
            response = self.teams["data_analysts"].run(minutes_instruction)
            response_content = response.content
            
            self.conversation_history["data_analysts"].append({"role": "user", "content": minutes_instruction})
            self.conversation_history["data_analysts"].append({"role": "assistant", "content": response_content})
            
            def clean_text(text):
                import re
                clean = re.sub(r'[┃┏┓┗┛━]', '', text)
                clean = re.sub(r'\s+', ' ', clean)
                clean = ''.join(c for c in clean if c.isprintable() or c in ['\n', '\t'])
                return clean.strip()
            
            clean_response = clean_text(response_content)
            
            if clean_response:
                # Format the content before saving
                formatted_content = self._format_minutes_content(clean_response, meeting_date)
                
                minutes_dir = "minutes"
                os.makedirs(minutes_dir, exist_ok=True)
                
                # Save the formatted minutes
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename_base = os.path.splitext(transcript_file)[0]
                minutes_filename = f"{filename_base}_minutes_{timestamp}.txt"
                minutes_path = os.path.join(minutes_dir, minutes_filename)
                
                with open(minutes_path, 'w', encoding='utf-8') as f:
                    f.write(formatted_content)
                
                # Return the formatted content for display
                return [{"source": "System", "content": formatted_content}]
            
            else:
                print("\nWarning: Empty or invalid response received.")
                return [{"source": "System", "content": "Failed to generate minutes: Empty or invalid response received."}]
            
        except Exception as e:
            print(f"\n[ERROR]: Failed to generate minutes: {e}")
            return [{"source": "System", "content": f"Error generating minutes: {str(e)}"}]
        
    except Exception as e:
        import traceback
        print(f"\n[ERROR]: Failed to process transcript: {e}")
        traceback.print_exc()
        return [{"source": "System", "content": f"Error processing transcript: {str(e)}"}]

def _format_minutes_content(self, content, meeting_date):
    """Format the minutes content with consistent formatting"""
    # Standardize bullet points
    formatted = content.replace('•', '*')
    
    # Ensure consistent section headers
    formatted = formatted.replace('## ', '## ')
    formatted = formatted.replace('# ', '# ')
    
    # Add line breaks between sections
    sections = ['Attendees:', 'Key Discussion Points:', 'Action Items:', 'Decisions:', 'Next Steps:']
    for section in sections:
        formatted = formatted.replace(f'## {section}', f'\n## {section}\n')
    
    # Clean up any duplicate line breaks
    formatted = '\n'.join(line.strip() for line in formatted.split('\n') if line.strip())
    
    return formatted  
    def generate_minutes_for_latest_transcript(self):
            try:
                talks_dir = "transcriptions"
                
                if not os.path.exists(talks_dir):
                    print(f"\nError: 'transcriptions' folder not found. Creating it now.")
                    os.makedirs(talks_dir)
                    return [{"source": "System", "content": "No transcripts found. Please add transcript files to the 'transcriptions' folder."}]
                
                transcript_files = [f for f in os.listdir(talks_dir) if os.path.isfile(os.path.join(talks_dir, f))]
                
                if not transcript_files:
                    print(f"\nError: No transcript files found in 'transcriptions' folder.")
                    return [{"source": "System", "content": "No transcripts found in the 'transcriptions' folder."}]
                
                latest_file = max(transcript_files, key=lambda f: os.path.getmtime(os.path.join(talks_dir, f)))
                
                print(f"\nFound latest transcript: {latest_file}")
                
                return self.generate_minutes_for_transcript(latest_file)
                
            except Exception as e:
                import traceback
                print(f"\n[ERROR]: Failed to find latest transcript: {e}")
                traceback.print_exc()
                return [{"source": "System", "content": f"Error finding latest transcript: {str(e)}"}]
        
    def system_check(self, input_text="Check system status"):
        return self.process_with_team("watchdog", input_text)
    
    def display_team_members(self):
        print(f"\n=== {self.system_name} Team Structure ===")
        
        for team_name, team in self.teams.items():
            print(f"\n{team.name}:")
            for i, member in enumerate(team.members, 1):
                print(f"  {i}. {member.name}: {member.role}")
                
        print("\n======================================")
