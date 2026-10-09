# AI FAQ Agent Guide

The Weather Assistant API includes an AI-powered FAQ Agent that can answer questions about the application's architecture, subscriptions, pricing, SLAs, and commercial usage. This capability uses an embedded FAISS vector database to perform similarity searches over our custom knowledge base.

## How It Works

1. **Knowledge Base**: The source of truth for the FAQ agent is the `data/faq/weather.txt` document. It contains detailed answers to common questions about using `wttr.in`, caching strategies, application vs. API pricing, and production readiness.
2. **Vector Database**: A script reads this text file, splits it into chunks, and generates OpenAI embeddings (`text-embedding-3-small`) for each chunk, saving them into a FAISS index.
3. **Agent Orchestration**: When a user queries the API, the orchestrator determines if the query requires FAQ knowledge. If so, it queries the FAISS index for relevant context and uses an LLM to synthesize an accurate answer.

## Setup Instructions

To enable the AI Agent's FAQ capability, you must build the FAISS vector database index locally. 

### Prerequisites

Ensure you have your OpenAI API key configured in your `.env` file, as it is required to generate the embeddings:
```env
OPENAI_API_KEY=your-openai-api-key
```

### Building the Index

Run the indexing script from the project root directory:

```powershell
python script/build_faiss_index.py
```

**What this script does:**
- Reads the knowledge base from `data/faq/weather.txt`.
- Splits the text into manageable chunks.
- Calls OpenAI to create embeddings for each chunk.
- Saves the resulting FAISS index to the `data/faiss_index` directory.

Once built, the API application will load this index automatically at startup.

## Testing the FAQ Agent

You can test the FAQ Agent by asking questions through the API's endpoints (e.g., via the Swagger UI at `http://127.0.0.1:8000/docs`).

**Example Questions:**
- *"Does the Weather Demo provide an SLA?"*
- *"Is the Weather Demo really zero-cost?"*
- *"What is the difference between API pricing and application pricing?"*
- *"Can this become production-ready?"*

## Updating the Knowledge Base

If you need to add new questions or update existing answers:

1. Edit the `data/faq/weather.txt` file with your new content.
2. Save the file.
3. Re-run the `python script/build_faiss_index.py` script to regenerate the embeddings and update the FAISS index.
4. Restart the API server so it loads the updated index into memory.
