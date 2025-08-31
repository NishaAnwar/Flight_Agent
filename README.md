🛫 **Flight Booking Agent with Gemini + LangChain + FAISS**

This project implements an intelligent flight assistant that helps users search and filter flights in real-time using Google Gemini (LLM) and LangChain agents. The system integrates with Bookme APIs through authentication and combines data extraction, flight search, and conversational memory to deliver relevant flight results.

🔹 **Key Features**

Flight Details Extraction → Uses a custom extract_flight_details tool to parse user queries and identify source, destination, and travel dates.

Authentication → Secure login with Bookme’s API using a dedicated Authentication_Tool.

Flight Search → Retrieves real-time flight availability using the Flight_Searching_Tool.

Context-Aware Conversations → Maintains conversation history and applies FAISS vector search to reuse past results for follow-up queries.

Filtering with Gemini LLM → Automatically filters old flight results when users refine their search (e.g., choosing a specific airline).

Error Handling → Gracefully manages incomplete inputs (e.g., missing travel date, source, or destination).

Vector Database → Stores past queries and responses in FAISS for fast semantic retrieval and personalization.

🔹 **Workflow**

User enters a flight request in natural language.

The system checks FAISS for similar past queries.

If found → filters old results with Gemini.

If not found → extracts flight details, validates inputs, and performs a fresh search.

Flight results are shown, stored in conversation history, and saved into FAISS for future reuse.

⚠️ **Note**: Don’t forget to enter your **Bookme username and password** in the authentication_tool, and provide your **Gemini API** key in the environment before running the agent.
