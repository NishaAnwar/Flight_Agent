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
import warnings
import logging

warnings.filterwarnings("ignore")  # Suppress warnings
logging.getLogger().setLevel(logging.CRITICAL)  # Suppress logs globally


load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0,
    convert_system_message_to_human=True,
    google_api_key=os.getenv("GEMINI_API_KEY")
)

tools = [
    Tool(name="extract_details", func=extract_flight_details,  description="First tool for ANY user query. Extracts flight details OR returnsspecial responses for non-flight/abusive queries. ALWAYS return its output directly if it contains 'message' key."),
    Tool(name="auth", func=authenticate, description="Generates Bearer token for Bookme."),
    Tool(name="search", func=search_flights, description="Searches flights using token and extracted data.", return_direct=True)

]

agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=False
)

if __name__ == "__main__":

    def re_ask_full_prompt_if_required(data: dict) -> dict:
        """If essential info is missing, notify and exit the program."""
        missing = []
        if not data.get("source"):
            missing.append("source")
        if not data.get("destination"):
            missing.append("destination")
        if not data.get("date"):
            missing.append("date")

        if missing:
            print(f" Missing essential details: {', '.join(missing).title()}")
            print("Please re-run the program and provide the full flight request with all required details.")
            exit(1)

        return data

    user_input = input("Enter your flight request:\n> ")
    response = agent.run(user_input)

    try:
        data = json.loads(response)

        if "message" in data and "partial_data" in data:
            print("📩", data["message"])
            data = data["partial_data"]

        #  Check for missing essential details and exit if incomplete
        data = re_ask_full_prompt_if_required(data)

        # Attach token and proceed
        token = authenticate("Bookme")
        data["token"] = token

        final_response = search_flights(data)
        print("\nFinal Result:\n", final_response)

    except json.JSONDecodeError:
        print("\nFinal Result:\n", response)
