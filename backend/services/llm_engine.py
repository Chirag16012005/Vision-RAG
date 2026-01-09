from backend.db.milvus_handler import search_vectors
from backend.services.ingestion import embed_query

# Placeholder for actual LLM (Using a simple logic or mock for now)
# If you have an OpenAI Key or HuggingFace Pipeline, replace 'generate_mock_response'
def generate_answer(question: str, selected_files: list = None):
    # 1. Vector Search
    query_vector = embed_query(question)
    hits = search_vectors(query_vector, file_filters=selected_files)
    
    # 2. Build Context
    context_text = "\n\n".join([hit.entity.get("text") for hit in hits])
    sources = list(set([hit.entity.get("source") for hit in hits]))

    if not context_text:
        return "I couldn't find any relevant information in the uploaded documents.", []

    # 3. Construct Prompt (If you had an LLM connected)
    prompt = f"""
    Use the following context to answer the question.
    
    Context:
    {context_text}
    
    Question: {question}
    """
    
    # --- REAL LLM CALL WOULD GO HERE ---
    # response = openai.ChatCompletion.create(...)
    # return response.choices[0].message.content, sources
    
    # For now, we return a summary + context (Simulation)
    answer = f"Based on the documents, here is the relevant info:\n\n{hits[0].entity.get('text')[:500]}...\n\n(Context derived from {len(hits)} chunks)"
    
    return answer, sources