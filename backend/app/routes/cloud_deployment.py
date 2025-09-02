from fastapi import APIRouter
from app.services.cloud_deployment_service import CloudDeploymentService

router = APIRouter(prefix="/api/cloud", tags=["cloud-deployment"])

@router.post("/deploy")
async def deploy_to_cloud(project_path: str):
    """Deploy a local project to AWS cloud automatically."""
    cloud_service = CloudDeploymentService()
    return await cloud_service.deploy_local_project(project_path)

@router.post("/auto-deploy")
async def auto_deploy_demo2():
    """Automatically deploy C:\Demo2 project without user input."""
    cloud_service = CloudDeploymentService()
    return await cloud_service.deploy_local_project("C:\\JAVA FB")