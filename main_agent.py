import os
import json
import warnings
import logging
from dotenv import load_dotenv
from langchain.agents import AgentType, Tool, initialize_agent
from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai
from Data_Extraction_tool import extract_flight_details
from Authentication_Tool import authenticate
from Flight_Searching_Tool import search_flights
import os
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.schema import Document


# Suppress warnings and logs
warnings.filterwarnings("ignore")
logging.getLogger().setLevel(logging.CRITICAL)

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Setup LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0,
    convert_system_message_to_human=True,
    google_api_key=os.getenv("GEMINI_API_KEY")
)


# Gemini Embeddings
embedding_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=os.getenv("GEMINI_API_KEY"))

# Load or create FAISS vector store
# Required for creating a dummy document

VECTOR_STORE_DIR = "flight_cache"
VECTOR_STORE_PATH = os.path.join(VECTOR_STORE_DIR, "index.faiss")

if os.path.exists(VECTOR_STORE_PATH):
    vector_store = FAISS.load_local(VECTOR_STORE_DIR, embedding_model, allow_dangerous_deserialization=True)

else:
    # You can replace this dummy document later with real data
    sample_doc = Document(page_content="Initial dummy flight data for FAISS index.")
    vector_store = FAISS.from_documents([sample_doc], embedding_model)
    vector_store.save_local(VECTOR_STORE_DIR)



# Tools
tools = [
    Tool(name="extract_details", func=extract_flight_details, description="First tool for ANY user query. Extracts flight details OR returns special responses for non-flight/abusive queries. ALWAYS return its output directly if it contains 'message' key."),
    Tool(name="auth", func=authenticate, description="Generates Bearer token for Bookme."),
    Tool(name="search", func=search_flights, description="Searches flights using token and extracted data.", return_direct=True)
]

# Initialize agent
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=False
)




# Check if required details are present
def validate_required_fields(data: dict) -> bool:
    required = ["source", "destination", "date"]
    missing = [
        field for field in required
        if not (data.get(field) or "").strip()
    ]
    if missing:
        print(f"Missing required details: {', '.join(missing).title()}")
        print("Please re-enter your request with complete information.\n")
        return False
    return True




def build_conversation_context(history, user_query):
    history_text = "\n".join(
        f"User: {item['query']}\nAssistant: {item['response']}"
        for item in history[-3:]
    )
    return f"{history_text}\nUser: {user_query}\nAssistant:"


# Main program
if __name__ == "__main__":

    conversation_history = []  # Global list to store past turns
    MAX_TURNS = 5  # Customize this if needed

    while True:
        user_input = input("\n🛫 Enter your flight request (or type 'exit' to quit):\n> ").strip()
        if user_input.lower() == "exit":
            break

        # STEP 1: Search for similar past result
        results = vector_store.similarity_search(user_input, k=3)
        found_followup = False

        for doc in results:
            old_query = doc.metadata.get("query")
            try:
                parsed_doc = json.loads(doc.page_content)
                old_response = parsed_doc.get("response", "")
            except:
                old_response = doc.page_content

            # STEP 2: Ask Gemini to filter old result based on this follow-up
            context_prompt = f"""
You're a flight assistant. The user previously received this result:
PAST RESULT (JSON):{old_response}
User now asks:"{user_input}"

            Instructions:
            - Filter and return ONLY relevant flights.
            - Use this airline mapping:
              - "Fly Jinnah" = Oneapi
              - "PIA" = Amadeus
              - "Airblue" = Airblue
            - If no match found or not a follow-up, say "NEW_QUERY".
            """

            filtered = llm.invoke(context_prompt)
            filtered_text = filtered.content if hasattr(filtered, "content") else str(filtered)

            if "NEW_QUERY" not in filtered_text:
                print("🧠 Using filtered previous result:\n", filtered_text)
                # Save to memory
                conversation_history.append({
                    "query": user_input,
                    "response": filtered_text
                })

                found_followup = True
                break

        # STEP 3: If it's a new query
        if not found_followup or vector_store.index.ntotal==0:
            # Extract flight details
            flight_data_raw = extract_flight_details(user_input)
            try:
                flight_data = json.loads(flight_data_raw)

            except json.JSONDecodeError:
                print("Couldn't understand your request. Please try again.\n")
                continue

            if "partial_data" in flight_data:
                data_to_validate = flight_data["partial_data"]
            else:
                data_to_validate = flight_data
########### Here we are tackling the situation where if any of the details are missing in user prompt, a message is appended,and other data is in partial_data  and if all details are present a simple dicti is returned

            if "message" in flight_data and "respectful" in flight_data["message"].lower():
                print(flight_data["message"])
                continue
            elif "message" in flight_data:
                print(flight_data["message"])



            # Step 2: Validate required fields
            if not validate_required_fields(data_to_validate):
                continue

            # Provide full conversation context
            prompt_with_history = build_conversation_context(conversation_history, user_input)

            agent_response = agent.run(prompt_with_history)
            print("Gemini Agent Response:\n", agent_response)

            # Save result into memory
            conversation_history.append({
                "query": user_input,
                "response": agent_response
            })

            # Also store into FAISS for future reference
            structured_faiss_data = {
                "query": user_input,
                "response": agent_response,
                "airline_map": {
                    "Oneapi": "Fly Jinnah",
                    "Amadeus": "PIA",
                    "Airblue": "Airblue"
                }
            }
            vector_store.add_texts(
                texts=[json.dumps(structured_faiss_data)],
                metadatas=[{"query": user_input}]
            )

