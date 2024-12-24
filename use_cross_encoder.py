import chromadb
from chromadb.utils import embedding_functions
import numpy as np
from sentence_transformers import CrossEncoder

system_prompt = """
You are an AI assistant tasked with providing detailed answers based solely on the given context. Your goal is to analyze the information provided and formulate a comprehensive, well-structured response to the question.

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

Important: Base your entire response solely on the information provided in the context. Do not include any external knowledge or assumptions not present in the given text.
"""

class VectorDBQuery:
    def __init__(self, db_path="./vector_db_new"):
        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(path=db_path)
        
        # Initialize the embedding function (same as scraper)
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        # Initialize cross encoder for re-ranking
        self.cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        
        # Get the collection
        self.collection = self.chroma_client.get_collection(
            name="thoughtco_articles",
            embedding_function=self.embedding_function
        )

    def search_similar(self, query_text, n_results=10, n_rerank=3):
        """
        Search for similar articles, then re-rank top results using cross encoder
        
        Args:
            query_text: The search query
            n_results: Number of initial results to retrieve
            n_rerank: Number of results to return after re-ranking
        """
        # First stage: Get initial results using embedding similarity
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            include=["metadatas", "documents", "distances"]
        )
        
        # Prepare for re-ranking
        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        if results['distances'][0]:
            max_distance = max(results['distances'][0])
            similarities = [100 * (1 - (dist / max_distance)) for dist in results['distances'][0]]
        else:
            similarities = []

        print_results(zip(metadatas, documents, similarities))
        
        # Create pairs for cross encoder
        pairs = [[query_text, doc] for doc in documents]
        
        # Get cross encoder scores
        cross_scores = self.cross_encoder.predict(pairs)
        
        # make sure nothing is negative
        num = min(cross_scores)
        if num < 0:
            cross_scores = [score - num for score in cross_scores]

        # Create tuples of (score, metadata, document) and sort by score
        ranked_results = list(zip(cross_scores, metadatas, documents))
        ranked_results.sort(reverse=True)  # Sort by cross encoder score (higher is better)
        
        # Take top n_rerank results
        top_results = ranked_results[:n_rerank]
        
        # Convert scores to percentages (0-100%)
        max_score = max(cross_scores)
        return [(metadata, document, (score/max_score) * 100) 
                for score, metadata, document in top_results]
    
    def print_titles(self):
        """Print titles of all articles in the collection"""
        results = self.collection.query(
            query_texts=[""],
            n_results=self.collection.count(),
            include=["metadatas"]
        )

        for metadata in results['metadatas'][0]:
            print(metadata['title'])

    def get_collection_stats(self):
        """Get basic stats about the collection"""
        count = self.collection.count()
        return {
            "total_articles": count
        }

def print_results(results, max_preview_length=200, close=False):
    """Pretty print the search results"""
    for idx, (metadata, document, similarity) in enumerate(results, 1):
        print(f"\n{'='*80}")
        print(f"Result {idx} - {'Closest ' if close else ''}Similarity: {similarity:.2f}%")
        print(f"Title: {metadata['title']}")
        print(f"URL: {metadata['url']}")
        print(f"\nPreview: {document[:max_preview_length]}...")

if __name__ == "__main__":
    # Initialize the query tool
    db_query = VectorDBQuery()
    
    # Print collection stats
    stats = db_query.get_collection_stats()
    print(f"Database contains {stats['total_articles']} articles\n")
    
    # Interactive query loop
    while True:
        # Get query from user
        query = input("\nEnter your search query (or 'quit' to exit): ").strip()
        
        if query.lower() == 'quit':
            break
            
        # Search for similar articles
        results = db_query.search_similar(query, n_results=10, n_rerank=3)
        
        # Print results
        print_results(results, close=True)