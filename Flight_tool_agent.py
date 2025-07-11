import os
from dotenv import load_dotenv
from langchain.agents import AgentType
from langchain.agents import Tool, initialize_agent
from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai
from Data_Extraction_tool import extract_flight_details
from Authentication_Tool import authenticate
from Flight_Searching_Tool import search_flights


load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0,
    convert_system_message_to_human=True,
    google_api_key=os.getenv("GEMINI_API_KEY")
)

tools = [
    Tool(name="extract_details", func=extract_flight_details, description="Extracts flight booking info from user query."),
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
    user_input = input("🛫 Enter your flight request:\n> ")
    response = agent.run(user_input)
    print("\n🎯 Final Result:\n", response)