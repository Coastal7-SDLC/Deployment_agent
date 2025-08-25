from fastapi import HTTPException
from utils.git_utils import clone_repository, extract_repo_name
from utils.universal_deployment import UniversalDeployment
from services.llm_service import LLMService
import logging

class DeploymentService:
    @staticmethod
    async def deploy_repository(repo_url: str):
        """Universal deployment system - works with any technology stack."""
        try:
            # Clone repository
            repo_name = extract_repo_name(repo_url)
            local_dir = f"./deployments/{repo_name}"
            clone_repository(repo_url, local_dir)
            
            # LLM analyzes repository and generates deployment instructions
            llm_service = LLMService()
            instructions = llm_service.analyze_repository(local_dir)
            
            if "error" in instructions:
                return instructions
            
            # Update Java server to use dynamic port BEFORE compilation
            UniversalDeployment.update_java_server_port_before_deployment(local_dir, instructions)
            
            # Execute LLM deployment instructions
            result = UniversalDeployment.execute_deployment(local_dir, instructions)
            
            # Update frontend API URLs to connect with backend
            UniversalDeployment.update_frontend_api_urls(local_dir, result)
            
            # Add repository info to result
            result["repo_name"] = repo_name
            result["repo_url"] = repo_url
            
            return result

        except Exception as e:
            logging.error(f"Deployment error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")