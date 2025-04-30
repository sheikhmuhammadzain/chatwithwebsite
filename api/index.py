from fastapi import FastAPI, Request
import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the FastAPI app from serverless_main.py
from serverless_main import app

# Export the app for Vercel serverless function 