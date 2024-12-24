import requests
from bs4 import BeautifulSoup
import chromadb
from chromadb.utils import embedding_functions
import time
import random
from urllib.parse import urljoin
import re, os

class ThoughtCoScraper:
    def __init__(self, db_path="./vector_db_new"):
        # Create directory for database if it doesn't exist
        os.makedirs(db_path, exist_ok=True)
        
        # Initialize ChromaDB with persistent storage
        self.chroma_client = chromadb.PersistentClient(path=db_path)
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        # Create or get collection
        self.collection = self.chroma_client.create_collection(
            name="thoughtco_articles",
            embedding_function=self.embedding_function
        )
        
        # Set for storing visited URLs
        self.visited_urls = set()
        
        # Headers to mimic a browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def is_valid_thoughtco_url(self, url):
        """Check if URL is a valid ThoughtCo article URL"""
        pattern = r'https?://www\.thoughtco\.com/.*-\d+$'
        return bool(re.match(pattern, url))

    def extract_article_content(self, soup):
        """Extract title and content from the article page"""
        title = ""
        content = ""
        
        # Extract title
        title_element = soup.find('h1', class_='article-heading type--lion')
        if title_element:
            title = title_element.get_text().strip()
            
        # Extract content
        content_element = soup.find('div', class_='loc article-content')
        if content_element:
            # Remove script and style elements
            for element in content_element(['script', 'style']):
                element.decompose()
            content = content_element.get_text().strip()

        # remove all new lines from content
        content = content.replace('\n', ' ')
            
        return title, content

    def extract_article_links(self, soup, base_url):
        """Extract all article links from the page"""
        links = set()
        for a in soup.find_all('a', href=True):
            url = urljoin(base_url, a['href'])
            if self.is_valid_thoughtco_url(url):
                links.add(url)
        return links

    def scrape_page(self, url):
        """Scrape a single page and return its content and new links"""
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            title, content = self.extract_article_content(soup)
            links = self.extract_article_links(soup, url)
            
            return {
                'title': title,
                'content': content,
                'url': url
            }, links
            
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return None, set()

    def store_in_vectordb(self, article_data):
        """Store article in ChromaDB"""
        if not article_data['title'] or not article_data['content']:
            return
        
        try:
            self.collection.add(
                documents=[article_data['content']],
                metadatas=[{
                    'title': article_data['title'],
                    'url': article_data['url']
                }],
                ids=[str(hash(article_data['url']))]
            )
        except Exception as e:
            print(f"Error storing article in vector DB: {str(e)}")

    def scrape_articles(self, start_url, max_articles=300):
        """Main scraping function"""
        urls_to_visit = {start_url}
        
        while len(self.visited_urls) < max_articles and urls_to_visit:
            # Get next URL to scrape
            current_url = urls_to_visit.pop()
            
            if current_url in self.visited_urls:
                continue
                
            print(f"Scraping {current_url}")
            
            # Scrape the page
            article_data, new_links = self.scrape_page(current_url)
            
            if article_data and len(article_data['content']) > 100:
                # Store in vector DB
                self.store_in_vectordb(article_data)
                
                # Mark as visited
                self.visited_urls.add(current_url)
                
                # Add new links to visit
                urls_to_visit.update(new_links - self.visited_urls)
                
                print(f"Processed {len(self.visited_urls)} articles")
                
                # Add delay to be respectful
                time.sleep(random.uniform(1, 3))
            
            if len(self.visited_urls) >= max_articles:
                break

# Example usage
if __name__ == "__main__":
    scraper = ThoughtCoScraper()
    start_url = "https://www.thoughtco.com/percentage-of-human-brain-used-4159438"
    scraper.scrape_articles(start_url)