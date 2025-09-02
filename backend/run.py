#!/usr/bin/env python3
"""
Run script for the Coastal Seven Universal Deployment Agent.
Usage: python run.py
"""

import os
os.environ["PYTHONWARNINGS"] = "ignore::DeprecationWarning"

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*TripleDES.*")
warnings.filterwarnings("ignore", message=".*CryptographyDeprecationWarning.*")

# Suppress cryptography warnings specifically
try:
    from cryptography.utils import CryptographyDeprecationWarning
    warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)
except ImportError:
    pass

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=8000,
        reload=True
    )