import os
import subprocess
import logging

def clone_repository(repo_url: str, local_dir: str) -> bool:
    """Clone GitHub repository to local directory."""
    try:
        if os.path.exists(local_dir):
            subprocess.run(f'rmdir /s /q "{local_dir}"', shell=True, check=True)
        
        subprocess.run(f'git clone {repo_url} "{local_dir}"', shell=True, check=True)
        logging.info(f"Repository cloned to {local_dir}")
        return True
    except Exception as e:
        logging.error(f"Failed to clone repository: {str(e)}")
        return False

def extract_repo_name(repo_url: str) -> str:
    """Extract repository name from GitHub URL."""
    return repo_url.split('/')[-1].replace('.git', '')