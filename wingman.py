import os
from dotenv import load_dotenv
from palette import Palette
from agno.agent import Agent
from agno.team import Team

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    api_key = os.getenv("API_KEY")  

system = Palette(
    provider="gemini",  
    model_name="gemini-1.5-flash-8b",
    api_key=api_key,
    max_tokens=1024,
    system_name="AI Meeting Assistant"
)

"""
# Create custom agents
custom_agent1 = Agent(
    name="Custom Agent 1",
    role="Special role description",
    model=system.model,
    description="Custom agent description",
    instructions=["Instruction 1", "Instruction 2"],
    markdown=True,
)

custom_agent2 = Agent(
    name="Custom Agent 2",
    role="Another special role",
    model=system.model,
    description="Another custom agent description",
    instructions=["Instruction 1", "Instruction 2"],
    markdown=True,
)
import os
from dotenv import load_dotenv
from palette import Palette
from agno.agent import Agent
from agno.team import Team

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    api_key = os.getenv("API_KEY")  

system = Palette(
    provider="gemini",  
    model_name="gemini-1.5-flash-8b",
    api_key=api_key,
    max_tokens=1024,
    system_name="AI Meeting Assistant"
)

"""
# Create custom agents
custom_agent1 = Agent(
    name="Custom Agent 1",
    role="Special role description",
    model=system.model,
    description="Custom agent description",
    instructions=["Instruction 1", "Instruction 2"],
    markdown=True,
)

custom_agent2 = Agent(
    name="Custom Agent 2",
    role="Another special role",
    model=system.model,
    description="Another custom agent description",
    instructions=["Instruction 1", "Instruction 2"],
    markdown=True,
)

# Create custom team
custom_team = Team(
    name="Custom Team",
    mode="coordinate",
    members=[custom_agent1, custom_agent2],
    model=system.model,
    description="A custom team for special purposes",
    instructions=["Team instruction 1", "Team instruction 2"],
    show_members_responses=True,
    markdown=True,
)

# Add custom team to the system
system.add_team("custom", custom_team)
"""

def main():
    system.display_team_members()
    
    print(f"\n=== {system.system_name} Initialized ===")
    print("Type 'exit' to quit the application.")
    print("Use these commands to interact with specific teams:")
    print("  'va: [text]' - Interact with Virtual Assistant Team")
    print("  'data: summarize' - Generate a meeting summary for the most recent transcript")
    print("  'data: minutes' - Generate court-style minutes for the most recent transcript")
    print("  'data: summarize:[filename]' - Summarize a specific transcript file")
    print("  'data: minutes:[filename]' - Generate court-style minutes for a specific transcript")
    print("  'data: [text]' - Use Data Analysts Team for other data tasks")
    print("  'check' - Run a system check with Watchdog Team")
    print("  Any other input goes to the Coordinator Team\n") 

    for folder in ["transcriptions", "summaries", "minutes"]:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"Created '{folder}' folder.")    

    while True:
        user_input = input("Enter your request: ")
        
        if user_input.lower() in ['exit', 'quit', 'bye']:
            print("\nShutting down system. Goodbye!")
            break
        
        try:
            if user_input.lower().startswith("va:"):
                content = user_input[len("va:"):].strip()
                system.va_query(content)
            elif user_input.lower() == "data: summarize":
                system.summarize_latest_transcript()
            elif user_input.lower() == "data: minutes":
                system.generate_minutes_for_latest_transcript()
            elif user_input.lower().startswith("data: summarize:"):
                file_name = user_input[len("data: summarize:"):].strip()
                system.summarize_transcript(file_name)
            elif user_input.lower().startswith("data: minutes:"):
                file_name = user_input[len("data: minutes:"):].strip()
                system.generate_minutes_for_transcript(file_name)
            elif user_input.lower().startswith("data:"):
                content = user_input[len("data:"):].strip()
                system.data_analysis(content)
            elif user_input.lower() == "check":
                system.system_check()
            else:
                system.process(user_input)
                
        except Exception as e:
            print(f"\n[ERROR]: Failed to process request: {e}")

if __name__ == "__main__":
    main()

# Create custom team
custom_team = Team(
    name="Custom Team",
    mode="coordinate",
    members=[custom_agent1, custom_agent2],
    model=system.model,
    description="A custom team for special purposes",
    instructions=["Team instruction 1", "Team instruction 2"],
    show_members_responses=True,
    markdown=True,
)

# Add custom team to the system
system.add_team("custom", custom_team)
"""

def main():
    system.display_team_members()
    
    print(f"\n=== {system.system_name} Initialized ===")
    print("Type 'exit' to quit the application.")
    print("Use these commands to interact with specific teams:")
    print("  'va: [text]' - Interact with Virtual Assistant Team")
    print("  'data: summarize' - Generate a meeting summary for the most recent transcript")
    print("  'data: minutes' - Generate court-style minutes for the most recent transcript")
    print("  'data: summarize:[filename]' - Summarize a specific transcript file")
    print("  'data: minutes:[filename]' - Generate court-style minutes for a specific transcript")
    print("  'data: [text]' - Use Data Analysts Team for other data tasks")
    print("  'check' - Run a system check with Watchdog Team")
    print("  Any other input goes to the Coordinator Team\n") 

    for folder in ["transcriptions", "summaries", "minutes"]:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"Created '{folder}' folder.")    

    while True:
        user_input = input("Enter your request: ")
        
        if user_input.lower() in ['exit', 'quit', 'bye']:
            print("\nShutting down system. Goodbye!")
            break
        
        try:
            if user_input.lower().startswith("va:"):
                content = user_input[len("va:"):].strip()
                system.va_query(content)
            elif user_input.lower() == "data: summarize":
                system.summarize_latest_transcript()
            elif user_input.lower() == "data: minutes":
                system.generate_minutes_for_latest_transcript()
            elif user_input.lower().startswith("data: summarize:"):
                file_name = user_input[len("data: summarize:"):].strip()
                system.summarize_transcript(file_name)
            elif user_input.lower().startswith("data: minutes:"):
                file_name = user_input[len("data: minutes:"):].strip()
                system.generate_minutes_for_transcript(file_name)
            elif user_input.lower().startswith("data:"):
                content = user_input[len("data:"):].strip()
                system.data_analysis(content)
            elif user_input.lower() == "check":
                system.system_check()
            else:
                system.process(user_input)
                
        except Exception as e:
            print(f"\n[ERROR]: Failed to process request: {e}")

if __name__ == "__main__":
    main()
