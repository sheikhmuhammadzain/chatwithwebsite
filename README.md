# Website RAG Chat System

A FastAPI application that allows users to chat with websites using Retrieval-Augmented Generation (RAG).

## Setup

1. Clone this repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Create a `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key
   ```

## Running the Application

Start the FastAPI server:
```
uvicorn main:app --reload
```

The API will be available at http://127.0.0.1:8000

## API Endpoints

- **POST /chat**: Chat with a website by providing a URL and message
- **GET /**: Welcome message
- **GET /docs**: Swagger documentation

## Requirements

- Python 3.8+
- Chrome browser (for Selenium web scraping) 