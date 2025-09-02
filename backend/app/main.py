from fastapi import FastAPI
import os
import logging
import warnings
from app.routes import cloud_deployment
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import requests

# Setup detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('deployment.log')  # File output
    ]
)
# from app.config.agent_config import APP_CONFIG

# Create FastAPI app
app = FastAPI(
    title="Coastal Seven Cloud Deployment Agent",
    description="AI-powered cloud deployment agent for AWS",
    version="3.0.0"
)

@app.get("/", tags=["health"])
async def root():
    return {"message": "Coastal Seven Cloud Deployment Agent - Ready for AWS deployments!"}

@app.post("/deploy-now", tags=["auto-deploy"])
async def deploy_now():
    """One-click deployment of C:\Demo2 project."""
    from app.services.cloud_deployment_service import CloudDeploymentService
    cloud_service = CloudDeploymentService()
    return await cloud_service.deploy_local_project("C:\\JAVA FB")

@app.get("/deployment-progress/{project_name}", tags=["progress"])
async def get_deployment_progress(project_name: str):
    """Get deployment progress using port checking."""
    # Simple progress tracking without external dependency
    import socket

    
    # Simple port check for deployment status
    public_ip = "34.204.215.170"
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((public_ip, 3000))
        sock.close()
        
        if result == 0:
            return {"status": "deployed", "message": "Application is running"}
        else:
            return {"status": "deploying", "message": "Application is still deploying"}
    except:
        return {"status": "unknown", "message": "Cannot check deployment status"}

# Include cloud deployment router
app.include_router(cloud_deployment.router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")