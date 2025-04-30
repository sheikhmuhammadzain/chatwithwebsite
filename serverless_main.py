import os
import hashlib
import asyncio
from typing import Dict
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

import httpx
from bs4 import BeautifulSoup
from llama_index.core import (
    VectorStoreIndex, Document, get_response_synthesizer,
    QueryBundle
)
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.llms import ChatMessage
from llama_index.core.storage.chat_store import SimpleChatStore
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ServerlessWebsiteRAG:
    def __init__(self):
        # Ensure API keys are loaded
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables.")

        self.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
        self.llm = OpenAI(model="gpt-4o-mini", temperature=0.2, max_tokens=1024)
        
        # In-memory storage for indices and chat history
        self.indices: Dict[str, VectorStoreIndex] = {}
        self.chat_stores: Dict[str, SimpleChatStore] = {}

    async def scrape_website(self, url: str) -> list[Document]:
        """Scrape website content using httpx and BeautifulSoup"""
        try:
            # Use httpx instead of Selenium for simpler scraping
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Parse HTML content
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract text content (remove script and style elements)
                for script in soup(['script', 'style']):
                    script.extract()
                
                # Get text from page
                text = soup.get_text(separator='\n', strip=True)
                
                # Create document from text
                if text:
                    document = Document(text=text, metadata={"source": url})
                    return [document]
                    
                return []
                
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return []

    async def get_or_create_index(self, url: str) -> VectorStoreIndex:
        """Get or create vector index for a website"""
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Create a unique ID for this website
        website_id = hashlib.md5(base_url.encode()).hexdigest()
        
        # Return existing index if available
        if website_id in self.indices:
            return self.indices[website_id]
            
        # Scrape and create new index
        documents = await self.scrape_website(base_url)
        
        if not documents:
            raise ValueError(f"No content could be scraped from {base_url}")
            
        # Create index from documents
        index = VectorStoreIndex.from_documents(documents)
        
        # Store in memory
        self.indices[website_id] = index
        return index

    async def chat_with_website(self, url: str, message: str) -> str:
        """Chat with a website using RAG"""
        try:
            # Get or create index
            index = await self.get_or_create_index(url)
            
            # Get website ID for chat history
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            website_id = hashlib.md5(base_url.encode()).hexdigest()
            
            # Initialize chat store if needed
            if website_id not in self.chat_stores:
                self.chat_stores[website_id] = SimpleChatStore()
                
            # Create memory buffer with chat history
            memory = ChatMemoryBuffer.from_defaults(
                chat_store=self.chat_stores[website_id],
                token_limit=3000
            )
            
            # Retrieve relevant context
            retriever = VectorIndexRetriever(index=index, similarity_top_k=5)
            query_bundle = QueryBundle(message)
            retrieved_nodes = retriever.retrieve(query_bundle)
            
            # Prepare context string
            context_str = "\n\n".join([n.node.get_content() for n in retrieved_nodes])
            
            # Get chat history
            chat_history = memory.get()
            
            # Define base prompt
            greeting_and_base_prompt = f"""You are an AI assistant for the website {url}. Your goal is to answer user questions based *only* on the provided context information from the website. If the answer is not in the context, say you don't have that information.

**Initial Greeting (Use ONLY if chat history is empty):**
Hello! 👋 I'm your AI assistant for this website. Ask me questions about it and I'll do my best to help!

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
            
            # Synthesize response based on chat history
            if not chat_history:
                # First message
                response_synthesizer = get_response_synthesizer(response_mode="compact")
                response = await response_synthesizer.asynthesize(
                    query=greeting_and_base_prompt,
                    nodes=retrieved_nodes
                )
            else:
                # Follow-up message
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
            print(f"Error during chat processing: {e}")
            raise RuntimeError(f"Chat failed for {url}: {str(e)}")

# FastAPI app
app = FastAPI(
    title="Serverless Website RAG Chat API",
    description="API to chat with websites using Retrieval-Augmented Generation.",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Initialize RAG system
try:
    rag_system = ServerlessWebsiteRAG()
except ValueError as e:
    print(f"CRITICAL ERROR: Failed to initialize ServerlessWebsiteRAG: {e}")
    exit(1)

# Pydantic models
class ChatRequest(BaseModel):
    url: HttpUrl
    message: str
    debug: bool = False

class ChatResponse(BaseModel):
    response: str
    website_id: str
    debug_info: dict = None

# API endpoint
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Chat with a website.
    
    - **url**: The full URL of the website to chat with.
    - **message**: The user's message or question.
    - **debug**: Set to true to include debugging information.
    """
    debug_info = {}
    try:
        url_str = str(request.url)
        
        # Add debugging info
        if request.debug:
            # Attempt to scrape and return information about what was found
            try:
                documents = await rag_system.scrape_website(url_str)
                debug_info["scrape_success"] = True
                debug_info["documents_found"] = len(documents)
                if documents:
                    debug_info["first_doc_preview"] = documents[0].text[:200] + "..."
                else:
                    debug_info["scrape_error"] = "No documents found"
            except Exception as e:
                debug_info["scrape_success"] = False
                debug_info["scrape_error"] = str(e)
        
        response_text = await rag_system.chat_with_website(url_str, request.message)
        
        # Get website ID for response
        parsed = urlparse(url_str)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        website_id = hashlib.md5(base_url.encode()).hexdigest()
        
        return ChatResponse(
            response=response_text, 
            website_id=website_id,
            debug_info=debug_info if request.debug else None
        )
        
    except ValueError as e:
        if request.debug:
            debug_info["error_type"] = "ValueError"
            debug_info["error_details"] = str(e)
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        if request.debug:
            debug_info["error_type"] = "RuntimeError"
            debug_info["error_details"] = str(e)
        print(f"Runtime Error: {e}")
        raise HTTPException(
            status_code=500, 
            detail={"message": f"Internal Server Error: {str(e)}", "debug": debug_info if request.debug else None}
        )
    except Exception as e:
        if request.debug:
            debug_info["error_type"] = "Exception"
            debug_info["error_details"] = str(e)
        print(f"Unexpected Error: {e}")
        raise HTTPException(
            status_code=500, 
            detail={"message": "An unexpected internal error occurred.", "debug": debug_info if request.debug else None}
        )

@app.get("/api")
async def root():
    return {"message": "Welcome to the Serverless Website RAG Chat API. Use the /api/chat endpoint for chatting."} 