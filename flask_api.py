__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import streamlit as st
import chromadb
from chromadb.utils import embedding_functions
import numpy as np
from sentence_transformers import CrossEncoder
from huggingface_hub import InferenceClient
import os
from typing import List, Tuple
from datetime import datetime, timedelta

from flask import Flask, request, jsonify

# Initialize local memory for conversation history
user_sessions = {}

from load_dotenv import load_dotenv

load_dotenv()

system_prompt = """
SYSTEM PROMPT:
You are an AI assistant for Thought Co tasked with providing answers based on the given context. Your goal is to analyze the information provided and formulate a response with a reading ease of flesch reading score of 80, concise and well-structured response to the question. Sometimes the information might not be sufficient to answer the question fully, in which case you should state this clearly in your response.

context will be passed as "Context:"
user question will be passed as "Question:"

To answer the question:
1. Thoroughly analyze the context, identifying key information relevant to the question.
2. Organize your thoughts and plan your response to ensure a logical flow of information.
3. Formulate a detailed answer that directly addresses the question, using only the information provided in the context.
4. Ensure your answer is comprehensive, covering all relevant aspects found in the context.
5. If the context doesn't contain sufficient information to fully answer the question, state this clearly in your response.

Format your response as follows:
1. Use clear, concise language.
2. Organize your answer into paragraphs for readability.
3. Use bullet points or numbered lists where appropriate to break down complex information.
4. If relevant, include any headings or subheadings to structure your response.
5. Ensure proper grammar, punctuation, and spelling throughout your answer.

IMPORTANT: At the beginning, write a short sentence summarizing your answer and then go into detail about it. You don't need to use the sources but it is appreciated.
DO NOT PROVIDE MORE UNRELATED INFORMATION THAN NECESSARY.
"""

# read articles.txt to get article titles
article_titles = [article for article in open("articles.txt").read().split("\n") if article]

class VectorDBQuery:
    def __init__(self, db_path="./vector_db_new"):
        self.chroma_client = chromadb.PersistentClient(path=db_path)
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self.cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        self.collection = self.chroma_client.get_collection(
            name="thoughtco_articles",
            embedding_function=self.embedding_function
        )

    def search_similar(self, query_text: str, n_results: int = 10, n_rerank: int = 3) -> List[Tuple]:
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            include=["metadatas", "documents", "distances"]
        )

        if results['distances'][0]:
            max_distance = max(results['distances'][0])
            similarities = [100 * (1 - (dist / max_distance)) for dist in results['distances'][0]]
            print(similarities)
        else:
            similarities = []
        
        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        
        pairs = [[query_text, doc] for doc in documents]
        cross_scores = self.cross_encoder.predict(pairs)
        
        ranked_results = list(zip(cross_scores, metadatas, documents, similarities))
        ranked_results.sort(reverse=True)
        
        top_results = ranked_results[:n_rerank]
        
        return [(metadata, document, similarities) 
                for score, metadata, document, similarities in top_results]

class HuggingFaceHelper:
    def __init__(self):
        self.client = InferenceClient(api_key=os.getenv("HUGGINGFACE_API_KEY"))
        self.model = "meta-llama/Meta-Llama-3-8B-Instruct"

    def generate_response(self, question: str, context: str, system_prompt: str) -> str:
        messages = [
            {
                "role": "assistant",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": f"Context: {context}\n\nQuestion: {question}"
            }
        ]
        
        try:
            response_text = ""
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=600,
                temperature=0.7,
                stream=True
            )
            
            # Create a placeholder for streaming response
            response_placeholder = st.empty()

            response_placeholder.markdown("🤖 Answer: ")
            
            # Stream the response
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    response_text += chunk.choices[0].delta.content
                    response_placeholder.markdown(response_text + "▌")
            
            response_placeholder.markdown(response_text)

            # once finished generating remove the placeholder
            response_placeholder.empty()

            return response_text
            
        except Exception as e:
            return f"Error generating response: {str(e)}"

def format_documents(results: List[Tuple]) -> str:
    context = ""
    for metadata, document, similarity in results:
        context += f"\nTitle: {metadata['title']}\n"
        context += f"Content: {document}\n"
        context += f"Source: {metadata['url']}\n\n"
    return context

app = Flask(__name__)

def cleanup_sessions():
    """Remove sessions older than 1 hour."""
    current_time = datetime.now()
    expired_sessions = [
        session_id for session_id, session_data in user_sessions.items()
        if session_data['last_active'] < current_time - timedelta(hours=1)
    ]
    for session_id in expired_sessions:
        del user_sessions[session_id]

@app.route('/api/chat', methods=['POST'])
def chat():
    global user_sessions, system_prompt

    data = request.get_json()
    user_question = data.get('question')
    session_id = data.get('session_id')

    if not user_question:
        return jsonify({"error": "Question is required."}), 400

    if not session_id:
        # Generate a new session ID if one is not provided
        session_id = str(uuid.uuid4())
        user_sessions[session_id] = {
            "history": [],
            "last_active": datetime.now()
        }

    # Cleanup old sessions
    cleanup_sessions()

    # Update session history and timestamp
    user_sessions[session_id]["history"].append({"role": "user", "content": user_question})
    user_sessions[session_id]["last_active"] = datetime.now()

    # Search for relevant documents
    db_query = VectorDBQuery()
    results = db_query.search_similar(user_question, n_results=10, n_rerank=3)
    context = format_documents(results)

    # Generate response from LLM
    llm_helper = HuggingFaceHelper()
    llm_response = llm_helper.generate_response(
        question=user_question,
        context=context,
        system_prompt=system_prompt
    )

    # Add assistant response to conversation history
    user_sessions[session_id]["history"].append({"role": "assistant", "content": llm_response})

    # Return response with conversation history
    return jsonify({
        "session_id": session_id,
        "conversation": user_sessions[session_id]["history"],
        "sources": [{
            "title": metadata['title'],
            "url": metadata['url'],
            "similarity": similarity
        } for metadata, document, similarity in results]
    })

if __name__ == "__main__":
    app.run(debug=True)

