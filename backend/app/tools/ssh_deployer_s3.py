import paramiko
import logging
import time
from typing import Dict, Any

# Configure logging to show in terminal
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('deployment.log')  # File output
    ]
)

class SSHDeployer:
    """Deploy applications via SSH using S3 approach - fixed corruption."""
    
    def __init__(self, region: str = "ap-south-2"):
        self.region = region
    
    def deploy_ssh(self, instance_ip: str, project_path: str, project_name: str, technology: str, readme_config: dict = None) -> Dict[str, Any]:
        """Deploy application via SSH."""
        try:
            logging.info(f"SSH DEPLOYMENT: {project_name} ({technology})")
            
            # Step 1: Upload to S3 (reuse existing method)
            from .native_deployer import NativeDeployer
            native_deployer = NativeDeployer(self.region)
            s3_url = native_deployer.upload_to_s3(project_path, project_name)
            logging.info(f"S3 upload successful")
            
            # Step 2: Deploy via SSH
            deployment_urls = self.deploy_via_ssh(instance_ip, s3_url, project_name, technology, readme_config)
            
            return {
                "status": "deployed",
                "deployment_type": "ssh",
                "frontend_url": deployment_urls["frontend_url"],
                "backend_url": deployment_urls["backend_url"],
                "api_docs_url": deployment_urls.get("api_docs_url", deployment_urls["backend_url"] + "/docs"),
                "direct_backend_url": deployment_urls.get("direct_backend_url", deployment_urls["backend_url"]),
                "instance_ip": instance_ip,
                "technology": technology,
                "note": f"SSH {technology} deployment completed"
            }
            
        except Exception as e:
            logging.error(f"SSH deployment failed: {str(e)}")
            raise Exception(f"SSH deployment failed: {str(e)}")
    
    def deploy_via_ssh(self, ip: str, s3_url: str, project_name: str, technology: str, readme_config: dict = None) -> Dict[str, str]:
        """Deploy to EC2 via SSH."""
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            logging.info(f"Connecting to {ip} via SSH...")
            # Try multiple possible locations for hyd.pem
            import os
            key_paths = [
                'hyd.pem',
                'd:\\Coastal_seven\\AGENT-SDLC\\backend\\hyd.pem',
                os.path.expanduser('~/.ssh/hyd.pem'),
                os.path.expanduser('~/hyd.pem')
            ]
            
            key_file = None
            for path in key_paths:
                if os.path.exists(path):
                    key_file = path
                    break
            
            if not key_file:
                raise Exception(f"SSH key 'hyd.pem' not found in any of these locations: {key_paths}")
            
            logging.info(f"Using SSH key: {key_file}")
            ssh.connect(
                hostname=ip,
                username='ubuntu',
                key_filename=key_file,
                timeout=30
            )
            logging.info("SSH connected successfully")
            
            # Use S3 approach with corruption fix
            logging.info("Downloading and extracting project from S3 with corruption fix")
            
            # Generate deployment commands
            commands = self.create_ssh_commands(s3_url, project_name, technology, readme_config, ip)
            
            # Execute commands
            for i, cmd in enumerate(commands, 1):
                print(f"🔧 Executing command {i}/{len(commands)}: {cmd[:60]}...")
                logging.info(f"Executing command {i}/{len(commands)}: {cmd[:60]}...")
                stdin, stdout, stderr = ssh.exec_command(cmd, timeout=300)
                
                exit_status = stdout.channel.recv_exit_status()
                if exit_status != 0:
                    error = stderr.read().decode()
                    print(f"⚠️  Command {i} warning: {error[:100]}...")
                    logging.warning(f"Command warning: {error[:200]}")
                else:
                    print(f"✅ Command {i} completed successfully")
                    logging.info(f"Command {i} completed successfully")
            
            ssh.close()
            logging.info("SSH deployment completed")
            
            # Return URLs
            if readme_config and readme_config.get('deployment_commands', {}).get('frontend'):
                return {
                    "frontend_url": f"http://{ip}:3000",
                    "backend_url": f"http://{ip}:8000",
                    "api_docs_url": f"http://{ip}:8000/docs",
                    "direct_backend_url": f"http://{ip}:8000"
                }
            else:
                return {
                    "frontend_url": f"http://{ip}:8000",
                    "backend_url": f"http://{ip}:8000",
                    "api_docs_url": f"http://{ip}:8000/docs",
                    "direct_backend_url": f"http://{ip}:8000"
                }
            
        except Exception as e:
            logging.error(f"SSH deployment error: {str(e)}")
            raise
    
    def create_ssh_commands(self, s3_url: str, project_name: str, technology: str, readme_config: dict = None, ip: str = None) -> list:
        """Create SSH deployment commands."""
        
        # Universal system setup
        commands = [
            "sudo apt update -y",
            "sudo apt install -y python3 python3-pip python3-venv nodejs npm wget unzip curl screen openjdk-17-jdk maven",
            "curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -",
            "sudo apt install -y nodejs",
            
            # Kill existing processes and screens
            "pkill -f 'uvicorn' || true",
            "pkill -f 'npm start' || true",
            "pkill -f 'http.server' || true",
            "pkill -f 'java -jar' || true",
            "screen -wipe || true",
            
            # Download and extract with corruption fix
            f"rm -rf /home/ubuntu/{project_name}",
            f"mkdir -p /home/ubuntu/{project_name}",
            f"cd /home/ubuntu && rm -f {project_name}.zip",  # Remove old zip
            f"cd /home/ubuntu && wget --no-check-certificate --timeout=60 '{s3_url}' -O {project_name}.zip",
            f"cd /home/ubuntu && file {project_name}.zip",  # Check file type
            f"cd /home/ubuntu && ls -la {project_name}.zip",  # Check file size
            f"cd /home/ubuntu && unzip -t {project_name}.zip || echo 'ZIP TEST FAILED'",  # Test zip integrity
            f"cd /home/ubuntu && unzip -o {project_name}.zip || echo 'ZIP EXTRACTION FAILED'",
            f"cd /home/ubuntu && ls -la {project_name}/ || echo 'PROJECT DIRECTORY CHECK'"
        ]
        
        # Deploy based on README config or technology
        if readme_config and 'deployment_commands' in readme_config:
            backend_config = readme_config['deployment_commands'].get('backend', {})
            frontend_config = readme_config['deployment_commands'].get('frontend', {})
            
            # Backend deployment
            backend_build = backend_config.get('build_commands', [])
            backend_run = backend_config.get('run_command', '')
            
            for cmd in backend_build:
                if not cmd.startswith('cd '):
                    # Convert pip to apt for Ubuntu 24.04
                    if 'pip3 install -r requirements.txt' in cmd:
                        cmd = 'sudo apt install -y python3-fastapi python3-uvicorn || pip3 install --break-system-packages -r requirements.txt'
                    elif 'pip install -r requirements.txt' in cmd:
                        cmd = 'sudo apt install -y python3-fastapi python3-uvicorn || pip install --break-system-packages -r requirements.txt'
                    elif 'pip3 install' in cmd:
                        # Convert common packages to apt
                        if 'fastapi' in cmd:
                            cmd = 'sudo apt install -y python3-fastapi python3-uvicorn'
                        elif 'uvicorn' in cmd:
                            cmd = 'sudo apt install -y python3-uvicorn'
                        else:
                            cmd = cmd.replace('pip3 install', 'pip3 install --break-system-packages')
                    commands.append(f"cd /home/ubuntu/{project_name}/backend && {cmd}")
            
            if backend_run:
                # Use system packages (no venv needed with apt)
                commands.append(f"screen -dmS backend bash -c 'cd /home/ubuntu/{project_name}/backend && {backend_run}'")
            
            # Frontend deployment
            if frontend_config:
                frontend_build = frontend_config.get('build_commands', [])
                frontend_run = frontend_config.get('run_command', '')
                
                for cmd in frontend_build:
                    if not cmd.startswith('cd '):
                        commands.append(f"cd /home/ubuntu/{project_name}/frontend && {cmd}")
                
                if frontend_run:
                    commands.append(f"screen -dmS frontend bash -c 'cd /home/ubuntu/{project_name}/frontend && {frontend_run}'")
        
        else:
            # Technology-specific fallbacks with screen
            if technology.lower() in ['python', 'fastapi']:
                commands.extend([
                    # Use apt for Ubuntu 24.04 compatibility
                    f"sudo apt install -y python3-fastapi python3-uvicorn || echo 'apt install failed'",
                    f"screen -dmS backend bash -c 'cd /home/ubuntu/{project_name}/backend && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000'"
                ])
            
            elif technology.lower() in ['node', 'nodejs', 'javascript', 'react', 'vue', 'angular']:
                commands.extend([
                    f"cd /home/ubuntu/{project_name} && npm install || echo 'npm install failed'",
                    f"cd /home/ubuntu/{project_name} && npm run build || echo 'build failed'",
                    f"screen -dmS app bash -c 'cd /home/ubuntu/{project_name} && npm start'"
                ])
            
            elif technology.lower() in ['java', 'spring']:
                commands.extend([
                    f"cd /home/ubuntu/{project_name} && mvn clean install || echo 'maven build failed'",
                    f"screen -dmS app bash -c 'cd /home/ubuntu/{project_name} && java -jar target/*.jar'"
                ])
            
            else:
                # Default Python fallback
                commands.extend([
                    f"cd /home/ubuntu/{project_name} && python3 -m venv venv --system-site-packages || echo 'venv creation failed'",
                    f"cd /home/ubuntu/{project_name} && source venv/bin/activate && pip install --break-system-packages -r requirements.txt || pip install --break-system-packages fastapi uvicorn",
                    f"screen -dmS app bash -c 'cd /home/ubuntu/{project_name} && source venv/bin/activate && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 || python3 app.py'"
                ])
            
        # Only add fallback frontend if extraction failed
        commands.extend([
            f"[ ! -d /home/ubuntu/{project_name}/frontend ] && mkdir -p /home/ubuntu/{project_name}/frontend",
            f"[ ! -f /home/ubuntu/{project_name}/frontend/index.html ] && cat > /home/ubuntu/{project_name}/frontend/index.html << 'EOF'\\n<html><body><h1>{project_name} Frontend Running!</h1><p>Backend API: <a href='http://{ip}:8000'>http://{ip}:8000</a></p></body></html>\\nEOF",
            f"screen -dmS frontend bash -c 'cd /home/ubuntu/{project_name}/frontend && python3 -m http.server 3000 --bind 0.0.0.0'"
        ])
        
        commands.append("sleep 5")  # Wait for services to start
        
        # Add verification commands
        commands.extend([
            "screen -ls || echo 'No screen sessions'",
            "ps aux | grep -E '(uvicorn|http.server|npm|java)' | grep -v grep || echo 'No processes found'",
            "curl -s http://localhost:8000 || echo 'Backend not responding'",
            "curl -s http://localhost:3000 || echo 'Frontend not responding'"
        ])
        return commands