import chromadb
from chromadb.utils import embedding_functions
import numpy as np

class VectorDBQuery:
    def __init__(self, db_path="./vector_db_new"):
        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(path=db_path)
        
        # Initialize the embedding function (same as scraper)
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        # Get the collection
        self.collection = self.chroma_client.get_collection(
            name="thoughtco_articles",
            embedding_function=self.embedding_function
        )

    def search_similar(self, query_text, n_results=5):
        """Search for similar articles and return results with distances"""
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            include=["metadatas", "documents", "distances"]
        )
        
        # Convert distances to similarity scores (0-100%)
        # Lower distance means higher similarity
        if results['distances'][0]:
            max_distance = max(results['distances'][0])
            similarities = [100 * (1 - (dist / max_distance)) for dist in results['distances'][0]]
        else:
            similarities = []

        return zip(
            results['metadatas'][0],
            results['documents'][0],
            similarities
        )
    
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

def print_results(results, max_preview_length=200):
    """Pretty print the search results"""
    for idx, (metadata, document, similarity) in enumerate(results, 1):
        print(f"\n{'='*80}")
        print(f"Result {idx} - Similarity: {similarity:.2f}%")
        print(f"Title: {metadata['title']}")
        print(f"URL: {metadata['url']}")
        print(f"\nPreview: {document[:max_preview_length]}...")

if __name__ == "__main__":
    # Initialize the query tool
    db_query = VectorDBQuery()

    # db_query.print_titles()
    
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
        results = db_query.search_similar(query, n_results=5)
        
        # Print results
        print_results(results)