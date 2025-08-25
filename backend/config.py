import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Using OpenRouter with Qwen model (hardcoded for this project)
OPENROUTER_API_KEY = "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"

logging.info("Using OpenRouter with Qwen model for LLM analysis")

# App configuration
APP_CONFIG = {
    "title": "Coastal Seven Universal Deployment Agent",
    "description": "AI-powered deployment agent using Qwen LLM for universal repository analysis and deployment",
    "version": "2.0.0"
}