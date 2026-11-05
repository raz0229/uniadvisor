# UniAdvisor – Intelligent University Academic Advisor (Scenario 1)
Python agent + Gemini LLM, short/long-term memory, RAG (ChromaDB), MCP server/client, Streamlit GUI.

## Run
```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
# edit .env  ->  GEMINI_API_KEY=...
python rag.py                # ingest the 5 knowledge documents (or use the GUI button)
streamlit run app.py         # open http://localhost:8501
pytest -q                    # offline tests (no API key needed)
```
## Demo script
1. Pick **S1002 Bilal** -> "Can I take Machine Learning?"  (MCP prerequisite check + RAG rule, cited)
2. "What about Deep Learning?" (short-term memory follow-up)
3. "I'm interested in NLP and want a 12-credit load." (saved to long-term memory)
4. Click **New session**, ask "Plan my next semester." (memory recalled in a new session)
Expand the 🔧 tool panels under each answer to see RAG/MCP evidence. Data is synthetic.
