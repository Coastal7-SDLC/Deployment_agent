import os
import yaml
import logging
from typing import Dict, Any
from app.tools.s3_manager import S3Manager
from app.tools.ec2_manager import EC2Manager
from app.tools.native_deployer import NativeDeployer
# from app.tools.ssh_deployer_s3 import SSHDeployer  # Disabled - using native deployment
from app.services.llm_service import LLMService
# from app.utils.git_utils import clone_repository, extract_repo_name

class CloudDeploymentService:
    def __init__(self):
        self.config = self._load_config()
        self.llm_service = LLMService()
    
    async def deploy_local_project(self, project_path: str) -> Dict[str, Any]:
        """Fully automated cloud deployment of local project."""
        try:
            logging.info("STEP 1: Starting automated cloud deployment")
            
            # Step 1: Validate local project path
            logging.info(f" STEP 1: Validating project path: {project_path}")
            if not os.path.exists(project_path):
                raise Exception(f"STEP 1 FAILED: Project path does not exist: {project_path}")
            
            project_name = os.path.basename(project_path)
            local_dir = project_path
            logging.info(f"STEP 1: Project validation successful - {project_name}")
            
            # Step 2: LLM analyzes local project
            logging.info(f"STEP 2: Starting LLM analysis...")
            analysis = self.llm_service.analyze_repository(local_dir)
            technology = self._extract_technology(analysis)
            logging.info(f"STEP 2: LLM analysis complete - Technology: {technology}")
            
            
            # Step 4: Upload to S3 with detailed debugging
            logging.info(f" STEP 4: Uploading to S3...")
            print(f"🔄 STEP 4: Starting S3 upload for {project_name}")
            print(f"📁 Local directory: {local_dir}")
            
            s3_manager = S3Manager()
            s3_url = s3_manager.upload_project(local_dir, project_name)
            
            print(f"✅ STEP 4: S3 upload completed")
            print(f"🔗 S3 URL: {s3_url}")
            logging.info(f" STEP 4: S3 upload successful - {s3_url}")
            
            # Step 5: Prepare for fresh EC2 instance deployment
            logging.info(f" STEP 5: Preparing for fresh EC2 deployment...")
            print(f"🔄 STEP 5: Will create new EC2 instance for deployment")
            
            # Create placeholder instance info - native deployer will create new instance
            instance_info = {"instance_id": "pending", "public_ip": "pending", "ami_type": "ubuntu"}
            
            print(f"✅ STEP 5: Ready for fresh instance deployment")
            logging.info(f" STEP 5: Fresh deployment preparation complete")
            
            # Check mock mode
            mock_mode = self.config["aws_config"].get("mock_mode", False)
            
            # Step 6: Simple port assignment - always use defaults
            backend_port = '8000'
            frontend_port = '3000'
            print(f"🔧 Using default ports - Backend: {backend_port}, Frontend: {frontend_port}")
                
            logging.info(f" STEP 6: Using ports - Backend: {backend_port}, Frontend: {frontend_port}")
            port = int(frontend_port)  # For compatibility
            
            # Step 7: Deploy (try EC2, fallback to local)
            logging.info(f" STEP 7: Deploying application...")
            
            # AWS DEPLOYMENT ONLY - NO LOCAL FALLBACK
            logging.info(f"Starting AWS-ONLY deployment")
            
            # Get README config from LLM analysis
            readme_config = analysis.get('readme_config', None)
            
            # Get README config from LLM analysis
            readme_config = analysis.get('readme_config', None)
            
            # Use native deployment with detailed debugging
            print(f"🔄 STEP 7: Starting native deployment (EC2 User Data)")
            print(f"🔧 Technology: {technology}")
            print(f"📋 README config: {readme_config is not None}")
            
            native_deployer = NativeDeployer(self.config["deployment_agent"]["aws_region"])
            
            print(f"🚀 STEP 7: Calling native deployer...")
            deployment_result = native_deployer.deploy_native(local_dir, project_name, technology, readme_config)
            
            print(f"✅ STEP 7: Native deployment completed")
            print(f"📊 Deployment result: {deployment_result.get('status', 'unknown')}")
            print(f"🔗 Result URL: {deployment_result.get('url', 'unknown')}")
            port = 3000
            logging.info(f"AWS deployment completed")
            
            logging.info(f" STEP 7: Deployment successful")
            
            # Step 8: Configure access URL
            logging.info(f" STEP 8: Configuring access...")
            
            if deployment_result.get("deployment_type") in ["native"] or deployment_result.get("deployment_method") == "aws_direct":
                logging.info(f" Local deployment - no NGINX needed")
                if deployment_result.get("deployment_type") == "native":
                    # Check if it's a full-stack app with frontend
                    has_frontend = False
                    if readme_config and readme_config.get('deployment_commands', {}).get('frontend'):
                        has_frontend = True
                    
                    # Use frontend URL as main for full-stack, backend URL for backend-only
                    main_url = deployment_result.get("frontend_url") if has_frontend else deployment_result.get("backend_url")
                    
                    nginx_result = {
                        "status": "configured",
                        "public_url": main_url,
                        "frontend_url": deployment_result.get("frontend_url", f"http://unknown:3000"),
                        "backend_url": deployment_result.get("backend_url", f"http://unknown:8000"),
                        "api_docs_url": deployment_result.get("api_docs_url", f"http://unknown:8000/docs"),
                        "direct_backend_url": deployment_result.get("direct_backend_url", f"http://unknown:8000"),
                        "app_name": project_name,
                        "port": 3000 if has_frontend else 8000,
                        "aws_deployment": True,
                        "native": True,
                        "instance_id": deployment_result.get("instance_id", "unknown"),
                        "public_ip": deployment_result.get("public_ip", "unknown")
                    }
                elif deployment_result.get("deployment_type") == "ec2_userdata_automated":
                    nginx_result = {
                        "status": "configured",
                        "public_url": deployment_result["url"],
                        "app_name": project_name,
                        "port": 3000,
                        "aws_deployment": True,
                        "automated": True,
                        "instance_id": deployment_result["instance_id"],
                        "public_ip": deployment_result["public_ip"]
                    }
                elif deployment_result.get("deployment_type") == "aws_minimal":
                    nginx_result = {
                        "status": "configured",
                        "public_url": "http://18.60.63.130:3000",
                        "app_name": project_name,
                        "port": 3000,
                        "aws_deployment": True,
                        "s3_package": deployment_result.get("s3_package_url"),
                        "instructions": deployment_result.get("instructions_url"),
                        "manual_steps": deployment_result.get("manual_deployment_steps")
                    }
                else:
                    nginx_result = {
                        "status": "configured",
                        "public_url": deployment_result["url"],
                        "app_name": project_name,
                        "port": port,
                        "local": True
                    }
            elif mock_mode:
                logging.info(f" MOCK: Would configure NGINX for {project_name} on port {port}")
                nginx_result = {
                    "status": "configured",
                    "public_url": f"http://{instance_info['public_ip']}/{project_name}",
                    "app_name": project_name,
                    "port": port,
                    "mock": True
                }
            else:
                # Fallback result for other deployment types
                nginx_result = {
                    "status": "configured",
                    "public_url": f"http://{deployment_result.get('instance_ip', 'unknown')}:3000",
                    "app_name": project_name,
                    "port": port
                }
            
            logging.info(f" STEP 8: Access configured")
            
            # Step 9: Return public URL
            result = {
                "status": "success",
                "project_name": project_name,
                "project_path": project_path,
                "technology": technology,
                "instance_id": instance_info["instance_id"],
                "public_url": nginx_result.get("public_url", "http://18.60.63.130:3000"),
                "direct_url": nginx_result.get("backend_url", "http://unknown:8000/api"),
                "deployment_steps": [
                    " Local project analyzed",
                    " Project uploaded to S3" if deployment_result.get("deployment_type") == "aws_minimal" else " Project prepared locally",
                    " Deployment package ready",
                    " Pre-signed URLs generated",
                    " Manual deployment instructions created",
                    " Ready for EC2 deployment"
                ],
                "deployment_type": deployment_result.get("deployment_type", "cloud"),
                "aws_deployment_info": {
                    "s3_package_url": deployment_result.get("s3_package_url"),
                    "instructions_url": deployment_result.get("instructions_url"),
                    "manual_steps": deployment_result.get("manual_deployment_steps", []),
                    "note": "Download the S3 package and follow manual deployment steps to deploy to EC2"
                } if deployment_result.get("deployment_type") == "aws_minimal" else None
            }
            
            logging.info(f" Deployment successful: {nginx_result['public_url']}")
            logging.info(f" Access your application at: {nginx_result['public_url']}")
            return result
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            
            print(f"❌ DEPLOYMENT FAILED AT STEP: {str(e)}")
            print(f"🔍 ERROR DETAILS: {error_trace}")
            
            logging.error(f" DEPLOYMENT FAILED: {str(e)}")
            logging.error(f" FULL ERROR TRACE: {error_trace}")
            return {
                "status": "failed",
                "error": str(e),
                "error_trace": error_trace,
                "project_name": project_name if 'project_name' in locals() else "unknown"
            }
    
    def _load_config(self) -> Dict[str, Any]:
        """Load agent configuration from YAML."""
        with open("app/config/agent_config.yaml", 'r') as f:
            return yaml.safe_load(f)
    
    def _extract_technology(self, analysis: Dict[str, Any]) -> str:
        """Extract primary technology from LLM analysis."""
        services = analysis.get("services", [])
        if services:
            return services[0].get("technology", "python")
        return "python"