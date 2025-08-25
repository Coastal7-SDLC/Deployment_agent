from fastapi import APIRouter
from services.deployment_service import DeploymentService

router = APIRouter(prefix="/api", tags=["deployment"])

@router.post("/deploy")
async def deploy_repository(repo_url: str):
    """Deploy a GitHub repository locally for testing."""
    return await DeploymentService.deploy_repository(repo_url)