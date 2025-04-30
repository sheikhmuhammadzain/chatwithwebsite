# main.py (or your preferred filename)

import os
import shutil
import asyncio
import datetime
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, HttpUrl

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from llama_index.core import (
    VectorStoreIndex, SimpleDirectoryReader, StorageContext,
    load_index_from_storage, Settings, get_response_synthesizer,
    QueryBundle
)
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.llms import ChatMessage
from llama_index.core.storage.chat_store import SimpleChatStore
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# --- WebsiteRAGSystem Class (Slightly modified for backend context) ---
# (Removed print statements for cleaner backend logs, kept error prints)

class WebsiteRAGSystem:
    def __init__(self):
        # Ensure API keys are loaded before initializing these
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables.")

        self.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
        self.llm = OpenAI(model="gpt-4o-mini", temperature=0.2, max_tokens=1024)
        self.scraped_dir = "scraped_content"
        self.persist_dir = "storage"
        self.chat_stores: Dict[str, SimpleChatStore] = {}
        # Use asyncio's default executor for FastAPI compatibility or keep ThreadPoolExecutor
        # Using ThreadPoolExecutor explicitly for potentially long-running scrape task
        self.executor = ThreadPoolExecutor(max_workers=4)

        Settings.llm = self.llm
        Settings.embed_model = self.embed_model
        Settings.chunk_size = 512
        Settings.chunk_overlap = 10

        Path(self.scraped_dir).mkdir(exist_ok=True)
        Path(self.persist_dir).mkdir(exist_ok=True)

    def _setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        # Consider specifying cache directory if running in restricted environments
        # chrome_options.add_argument("--disk-cache-dir=/tmp/chrome-cache")
        # chrome_options.add_argument("--user-data-dir=/tmp/chrome-user-data")
        try:
            service = Service(ChromeDriverManager().install())
            return webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            print(f"Error setting up Chrome Driver: {e}")
            print("Attempting to find existing chromedriver...")
            # Fallback or specific path if webdriver-manager fails in some envs
            try:
                # Specify path directly if needed:
                # service = Service('/path/to/your/chromedriver')
                # Or rely on PATH:
                service = Service()
                return webdriver.Chrome(service=service, options=chrome_options)
            except Exception as e2:
                 print(f"Fallback driver setup failed: {e2}")
                 raise RuntimeError("Could not initialize WebDriver.") from e2


    def _find_existing_embedding_domain(self, domain: str) -> str | None:
        persist_path = Path(self.persist_dir)
        if not persist_path.is_dir():
            return None
        for item in persist_path.iterdir():
            if item.is_dir() and item.name == domain:
                return item.name
        return None

    def _last_scrape_path(self, website_id: str) -> Path:
        return Path(self.persist_dir) / website_id / "last_scraped.txt"

    def _scraped_today(self, website_id: str) -> bool:
        last_scrape_file = self._last_scrape_path(website_id)
        if not last_scrape_file.exists():
            return False
        try:
            with open(last_scrape_file, "r") as f:
                last_scrape = datetime.datetime.strptime(f.read().strip(), "%Y-%m-%d").date()
                return last_scrape == datetime.date.today()
        except Exception as e:
            print(f"Error checking last scrape date for {website_id}: {e}")
            return False # Force rescrape if file is corrupted or unreadable

    def _mark_scraped_today(self, website_id: str):
        website_persist_dir = Path(self.persist_dir) / website_id
        website_persist_dir.mkdir(parents=True, exist_ok=True)
        last_scrape_file = self._last_scrape_path(website_id)
        try:
            with open(last_scrape_file, "w") as f:
                f.write(datetime.date.today().strftime("%Y-%m-%d"))
        except IOError as e:
            print(f"Error writing last scrape date for {website_id}: {e}")

    async def scrape_website(self, base_url: str) -> None:
        # Run the synchronous scraping function in the thread pool executor
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self._sync_scrape_website, base_url)

    def _sync_scrape_website(self, base_url: str) -> None:
        """Synchronous website scraping logic."""
        driver = None
        scraped_something = False
        try:
            print(f"Starting scrape for: {base_url}")
            driver = self._setup_driver()
            visited_urls = set()
            # Use a list as a queue
            urls_to_visit = [base_url]
            max_urls_to_visit = 50 # Limit crawl depth/breadth
            visited_count = 0

            # Ensure clean scrape directory
            scrape_path = Path(self.scraped_dir)
            if scrape_path.exists():
                 shutil.rmtree(scrape_path)
            scrape_path.mkdir(exist_ok=True)

            while urls_to_visit and visited_count < max_urls_to_visit:
                current_url = urls_to_visit.pop(0)
                if current_url in visited_urls or not current_url.startswith(base_url):
                    continue

                print(f"Attempting to scrape: {current_url}")
                visited_urls.add(current_url)
                visited_count += 1

                try:
                    driver.get(current_url)
                    # Wait for page load (consider more robust waits if needed)
                    WebDriverWait(driver, 15).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                    # Optional delay if pages load dynamically after 'complete'
                    # time.sleep(1)

                    # Extract text content - consider libraries like BeautifulSoup for better parsing
                    body_element = driver.find_element(By.TAG_NAME, "body")
                    page_content = body_element.text # Simple text extraction

                    # Create a safe filename
                    parsed_url = urlparse(current_url)
                    path_part = parsed_url.path.strip('/').replace('/', '_').replace('.', '_') # Sanitize
                    # Truncate long filenames
                    safe_path = (path_part or 'home')[:100] # Limit length
                    file_name = f"{parsed_url.netloc}_{safe_path}.txt"
                    file_path = scrape_path / file_name

                    if page_content and page_content.strip():
                        try:
                            with open(file_path, "w", encoding="utf-8") as file:
                                file.write(page_content)
                            # print(f"Successfully scraped and saved: {current_url}")
                            scraped_something = True
                        except IOError as e:
                             print(f"Error writing file {file_path} for {current_url}: {e}")


                    # Find new links on the same domain
                    links = driver.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        try:
                           href = link.get_attribute("href")
                           if href:
                               # Normalize URL (e.g., remove fragments)
                               parsed_href = urlparse(href)
                               normalized_href = f"{parsed_href.scheme}://{parsed_href.netloc}{parsed_href.path}"
                               if normalized_href.startswith(base_url) and normalized_href not in visited_urls and normalized_href not in urls_to_visit:
                                   urls_to_visit.append(normalized_href)
                        except Exception:
                            # Ignore stale element references or other link errors
                            pass

                except Exception as page_error:
                    print(f"Error scraping {current_url}: {str(page_error)}")
                    # Continue with the next URL

            print(f"Finished scraping {base_url}. Visited {visited_count} URLs.")
            if not scraped_something:
                 print(f"Warning: No text content could be scraped from {base_url}")


        except Exception as e:
            print(f"Critical error during scraping process for {base_url}: {e}")
            # Optionally re-raise or handle more gracefully
        finally:
            if driver:
                driver.quit()
            # Optional: Clean up scrape dir immediately if no content was found?
            # Or rely on the caller (_setup_index) to clean up


    async def _setup_index(self, website_id: str, url: str) -> VectorStoreIndex:
        persist_path = Path(self.persist_dir) / website_id
        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

        should_scrape = not self._scraped_today(website_id)
        if should_scrape:
            print(f"Scraping needed for {website_id} ({base_url})")
            await self.scrape_website(base_url)

            scrape_dir_path = Path(self.scraped_dir)
            scraped_files = list(scrape_dir_path.glob("*.txt"))

            if not scraped_files:
                 # If scraping happened but yielded no files, check if persistence exists
                 if persist_path.exists():
                     print(f"Scraping yielded no new content for {website_id}, but existing index found. Using existing.")
                     try:
                         storage_context = StorageContext.from_defaults(persist_dir=str(persist_path))
                         return load_index_from_storage(storage_context)
                     except Exception as e:
                         print(f"Error loading existing index for {website_id} after failed scrape: {e}. Attempting re-index.")
                         # Force re-indexing below might fail if scrape dir is empty
                 # If no files and no persistence, raise error.
                 raise ValueError(f"No content was scraped from the website {base_url} and no existing index found.")

            print(f"Indexing scraped content for {website_id}...")
            # Ensure directory exists before reading
            if not scrape_dir_path.is_dir():
                 raise FileNotFoundError(f"Scrape directory {self.scraped_dir} not found after scraping.")

            try:
                 # Load data only if directory is not empty
                 documents = SimpleDirectoryReader(input_dir=str(scrape_dir_path), required_exts=[".txt"]).load_data()
                 if not documents:
                     raise ValueError(f"No documents loaded from {self.scraped_dir} for {website_id}.")

                 # If persistence dir exists, remove old one before creating new index
                 if persist_path.exists():
                     print(f"Removing existing index at {persist_path} before re-indexing.")
                     shutil.rmtree(persist_path)

                 index = VectorStoreIndex.from_documents(documents)
                 persist_path.mkdir(parents=True, exist_ok=True) # Ensure dir exists before persist
                 index.storage_context.persist(persist_dir=str(persist_path))
                 self._mark_scraped_today(website_id)
                 print(f"Successfully indexed and persisted data for {website_id}")
                 return index
            except Exception as e:
                print(f"Error during indexing for {website_id}: {e}")
                raise RuntimeError(f"Failed to create or persist index for {website_id}") from e
            finally:
                # Clean up scrape directory after indexing attempt
                shutil.rmtree(scrape_dir_path, ignore_errors=True)


        else:
            print(f"Using existing index for {website_id} (scraped today).")
            if not persist_path.exists():
                 print(f"Error: Marked as scraped today, but persistence directory {persist_path} not found. Forcing rescrape.")
                 # Reset scraped marker and call setup again, which will trigger scraping
                 try:
                     self._last_scrape_path(website_id).unlink(missing_ok=True)
                 except OSError as e:
                     print(f"Could not remove potentially incorrect scrape marker: {e}")
                 return await self._setup_index(website_id, url) # Recursive call to rescrape/reindex

            try:
                storage_context = StorageContext.from_defaults(persist_dir=str(persist_path))
                index = load_index_from_storage(storage_context)
                print(f"Successfully loaded existing index for {website_id}")
                return index
            except Exception as e:
                print(f"Error loading index from storage for {website_id}: {e}. Attempting rebuild.")
                # If loading fails, try rebuilding it. Clear persistence first.
                shutil.rmtree(persist_path, ignore_errors=True)
                try:
                    self._last_scrape_path(website_id).unlink(missing_ok=True) # Allow rescraping
                except OSError as unlink_e:
                     print(f"Could not remove scrape marker during rebuild attempt: {unlink_e}")

                return await self._setup_index(website_id, url) # Recursive call


    async def chat_with_website(self, url: str, message: str) -> str:
        # URL validation happens via Pydantic in FastAPI now, but keep basic check
        if not url.startswith(('http://', 'https://')):
            raise ValueError("Invalid URL format. Must start with http:// or https://")

        parsed = urlparse(url)
        domain = parsed.netloc
        # Sanitize domain to create a valid directory name if needed
        website_id = "".join(c for c in domain if c.isalnum() or c in ('-', '.'))
        website_id = website_id.replace('.', '_') # Replace dots commonly

        persist_path = Path(self.persist_dir) / website_id

        # Check if index setup is needed (first time or needs refresh)
        # _setup_index handles loading or creating/scraping
        try:
            index = await self._setup_index(website_id, url)
        except (ValueError, RuntimeError, FileNotFoundError) as e:
             # These errors from _setup_index indicate failure to get/create index
             raise RuntimeError(f"Failed to setup index for {url}: {e}") from e
        except Exception as e:
            # Catch unexpected errors during setup
            raise RuntimeError(f"Unexpected error during index setup for {url}: {e}") from e


        # Proceed with chat logic
        try:
            if website_id not in self.chat_stores:
                self.chat_stores[website_id] = SimpleChatStore()

            # Consider token limit based on LLM context window
            memory = ChatMemoryBuffer.from_defaults(
                chat_store=self.chat_stores[website_id], token_limit=3000 # Adjust as needed
            )

            # Retrieve relevant context
            retriever = VectorIndexRetriever(index=index, similarity_top_k=5) # Adjust k as needed
            query_bundle = QueryBundle(message)
            retrieved_nodes = retriever.retrieve(query_bundle)

            # Prepare context string (optional, useful for prompt engineering)
            context_str = "\n\n".join([n.node.get_content() for n in retrieved_nodes])

            # Get chat history
            chat_history = memory.get()

            # --- Define the base prompt ---
            # Note: HTML formatting is included here. The frontend needs to render it.
            greeting_and_base_prompt = f"""You are an AI assistant for the website {url}. Your goal is to answer user questions based *only* on the provided context information from the website. If the answer is not in the context, say you don't have that information.

**Initial Greeting (Use ONLY if chat history is empty):**
Hello! 👋 Welcome to Qubit Dynamics! I’m your AI assistant. Here’s how I can help you today:
🔹 **AI Trainings**: Explore our hands-on, advanced AI training programs designed to boost your technical skills and industry readiness.
🔹 **Industry Solutions**: Discover our cutting-edge AI products tailored for sectors focused on sustainability, security, and operational efficiency.
🔹 **Research & Development**: Learn about our innovative R&D initiatives driving progress in artificial intelligence and machine learning.
If you have a specific question, just ask — I’m here to assist!
---
📌 **Registration**: Ready to join our programs or learn more? [Register here](https://torch-rhubarb-2b8.notion.site/1e30226a7d028155ab50ce92ec50abfc)

**Answering Subsequent Questions:**
Use the following retrieved context from the website {url} to answer the user's question. Format your answer clearly, using HTML elements like `<b>`, `<i>`, `<p>`, `<ul>`, `<li>`, `<a>` where appropriate for readability. Reference the source website ({url}) if relevant.

**Retrieved Context:**
---
{context_str}
---

**User Question:**
{message}

**Your Answer (HTML formatted):**
"""
            # --- Synthesize the response ---
            # Choose method based on whether there's chat history
            if not chat_history:
                 # First message, use the full prompt including greeting
                 # Note: We are directly using the prompt with synthesize, not a dedicated chat engine here
                 # For more complex chat, consider `index.as_chat_engine(memory=memory, ...)`
                 response_synthesizer = get_response_synthesizer(response_mode="compact") # Or other modes
                 response = await response_synthesizer.asynthesize(
                     query=greeting_and_base_prompt, # Pass the full prompt as the query here
                     nodes=retrieved_nodes # Provide nodes for context grounding
                 )

                 # The greeting is part of the prompt, the LLM *should* generate it,
                 # but we might need to manually prepend if it doesn't reliably include it.
                 # Let's assume the LLM follows the instruction for now.

            else:
                 # Follow-up message, use a simpler prompt structure for `synthesize`
                 # or ideally, switch to a proper chat engine for history management.
                 # Sticking with synthesize for consistency with the original code:
                 follow_up_prompt = f"""Use the following retrieved context from the website {url} to answer the user's question, considering the previous conversation. Format your answer clearly using HTML.

                 **Retrieved Context:**
                 ---
                 {context_str}
                 ---

                 **Conversation History:**
                 {memory.get_all()}

                 **User Question:**
                 {message}

                 **Your Answer (HTML formatted):**
                 """
                 response_synthesizer = get_response_synthesizer(response_mode="compact")
                 response = await response_synthesizer.asynthesize(
                      query=follow_up_prompt,
                      nodes=retrieved_nodes
                 )


            response_text = str(response)

            # Update memory
            memory.put(ChatMessage(role="user", content=message))
            memory.put(ChatMessage(role="assistant", content=response_text))

            return response_text

        except Exception as e:
            # Log the error for debugging
            print(f"Error during chat processing for {website_id}: {e}")
            # Raise a runtime error that FastAPI can catch and turn into a 500
            raise RuntimeError(f"Chat failed for {url}: {str(e)}")


# --- FastAPI Setup ---

app = FastAPI(
    title="Website RAG Chat API",
    description="API to chat with websites using Retrieval-Augmented Generation.",
    version="1.0.0"
)

# Instantiate the RAG system globally
# This ensures it's initialized once when the app starts
# Ensure .env is loaded before this line executes
try:
    rag_system = WebsiteRAGSystem()
except ValueError as e:
     print(f"CRITICAL ERROR: Failed to initialize WebsiteRAGSystem: {e}")
     # Exit or prevent app startup if essential components (like API key) are missing
     exit(1)


# --- Pydantic Models ---

class ChatRequest(BaseModel):
    url: HttpUrl # Use Pydantic's HttpUrl for automatic validation
    message: str

class ChatResponse(BaseModel):
    response: str
    website_id: str # Return the identifier used for context/memory

# --- API Endpoint ---

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Chat with a website.

    - **url**: The full URL (starting with http:// or https://) of the website to chat with.
               The system will scrape this website if not recently indexed.
    - **message**: The user's message or question.
    """
    try:
        # Convert Pydantic HttpUrl back to string for the function
        url_str = str(request.url)
        response_text = await rag_system.chat_with_website(url_str, request.message)

        # Determine website_id again for the response model
        parsed = urlparse(url_str)
        domain = parsed.netloc
        website_id = "".join(c for c in domain if c.isalnum() or c in ('-', '.'))
        website_id = website_id.replace('.', '_')

        return ChatResponse(response=response_text, website_id=website_id)

    except ValueError as e:
        # Handle specific user input errors (like invalid URL format handled inside the class)
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # Handle errors during scraping, indexing, or chat processing
        # These often indicate server-side issues or problems with external resources
        print(f"Runtime Error processing request for {request.url}: {e}") # Log the error server-side
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    except Exception as e:
        # Catch any other unexpected errors
        print(f"Unexpected Error processing request for {request.url}: {e}") # Log the error server-side
        raise HTTPException(status_code=500, detail="An unexpected internal error occurred.")


@app.get("/")
async def root():
    return {"message": "Welcome to the Website RAG Chat API. Use the /docs endpoint for API documentation."}

# --- Main block for running with uvicorn ---
# This part is usually not included directly if you run with `uvicorn main:app`
# but can be useful for direct execution (though `uvicorn` is preferred).
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)