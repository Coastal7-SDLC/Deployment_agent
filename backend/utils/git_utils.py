import subprocess
import logging
from fastapi import HTTPException

def clone_repository(repo_url: str, local_dir: str) -> str:
    """Clone a GitHub repository to local directory."""
    logging.info(f"Cloning {repo_url} to {local_dir}")
    
    clone_result = subprocess.run(
        ["git", "clone", repo_url, local_dir],
        capture_output=True,
        text=True
    )
    
    if clone_result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Failed to clone repository: {clone_result.stderr}")
    
    logging.info(f"Repository cloned successfully to {local_dir}")
    return local_dir

def extract_repo_name(repo_url: str) -> str:
    """Extract repository name from GitHub URL."""
    return repo_url.split("/")[-1].replace(".git", "")