import os
from dotenv import load_dotenv
from langchain.agents import AgentType
from langchain.agents import Tool, initialize_agent
from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai
from Data_Extraction_tool import extract_flight_details
from Authentication_Tool import authenticate
from Flight_Searching_Tool import search_flights
import json

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0,
    convert_system_message_to_human=True,
    google_api_key=os.getenv("GEMINI_API_KEY")
)

tools = [
    Tool(name="extract_details", func=extract_flight_details,  description="Use this tool to analyze any user message and extract flight details. Must be called first before any reasoning. Always return its output directly if it provides a message key."),
    Tool(name="auth", func=authenticate, description="Generates Bearer token for Bookme."),
    Tool(name="search", func=search_flights, description="Searches flights using token and extracted data.", return_direct=True)
]

agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

if __name__ == "__main__":


    def ask_user_to_fill_missing_fields(partial_data: dict) -> dict:
        """Interactively ask user to fill missing fields."""
        required_fields = ["source", "destination", "date"]

        for field in required_fields:
            if not partial_data.get(field):
                user_input = input(f"❓ Please provide the {field}:\n> ")

                # Only use extract_flight_details for date so it gets formatted properly
                if field == "date":
                    extracted = json.loads(extract_flight_details(user_input))
                    if "date" in extracted:
                        partial_data["date"] = extracted["date"]
                    else:
                        print("❌ Could not parse a valid date. Try again.")
                        return None
                else:
                    partial_data[field] = user_input.strip()

        return partial_data


    user_input = input("🛫 Enter your flight request:\n> ")
    response = agent.run(user_input)

    # Try parsing JSON to check for missing fields
    try:
        data = json.loads(response)

        # If it's asking for any missing info
        if "message" in data and "partial_data" in data:
            print("📩", data["message"])
            partial = data["partial_data"]

            # Ask for all missing fields (source, destination, date)
            updated = ask_user_to_fill_missing_fields(partial)

            if updated is None:
                print("❌ Failed to update missing fields.")
                exit(1)

            # Re-run the agent with complete data
            print("\n🔁 Reprocessing with all required details...\n")
            final_response = agent.run(json.dumps(updated))
            print("\nFinal Result:\n", final_response)

        else:
            # All fields were complete from the start
            print("\nFinal Result:\n", response)

    except json.JSONDecodeError:
        print("\nFinal Result:\n", response)
