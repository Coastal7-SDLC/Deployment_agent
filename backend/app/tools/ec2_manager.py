import boto3
import paramiko
import time
import logging
from typing import Dict, Any

class EC2Manager:
    def __init__(self, region: str = "ap-south-2"):
        self.ec2 = boto3.client('ec2', region_name=region)
        self.region = region
    
    def use_existing_instance(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Use existing EC2 instance for deployment."""
        try:
            instance_id = config.get("existing_instance_id")
            public_ip = config.get("existing_instance_ip")
            
            if not instance_id or not public_ip:
                raise Exception("Missing existing_instance_id or existing_instance_ip in config")
            
            logging.info(f"Using existing EC2 instance: {instance_id}")
            
            # Skip verification - directly use provided details
            return {
                "instance_id": instance_id,
                "public_ip": public_ip,
                "status": "running"
            }
            
        except Exception as e:
            logging.error(f"Failed to use existing EC2 instance: {str(e)}")
            raise
    
    def deploy_to_instance(self, instance_ip: str, project_name: str, s3_url: str, port: int, mock_mode: bool = False) -> Dict[str, Any]:
        """Deploy application to EC2 instance."""
        try:
            if mock_mode:
                logging.info(f"🎭 MOCK MODE: Simulating deployment to {instance_ip}")
                logging.info(f"🎭 MOCK: Would download {s3_url}")
                logging.info(f"🎭 MOCK: Would build Docker image for {project_name}")
                logging.info(f"🎭 MOCK: Would run container on port {port}")
                return {
                    "status": "deployed",
                    "url": f"http://{instance_ip}:{port}",
                    "port": port,
                    "mock": True
                }
            
            logging.info(f"🔑 Testing SSH connection to {instance_ip}...")
            
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Test SSH connection with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logging.info(f"SSH connection attempt {attempt + 1}/{max_retries}")
                    ssh.connect(
                        hostname=instance_ip,
                        username='ec2-user',
                        key_filename='hyd.pem',
                        timeout=60,
                        banner_timeout=60,
                        auth_timeout=60
                    )
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    logging.warning(f"SSH attempt {attempt + 1} failed, retrying...")
                    time.sleep(10)
            
            logging.info(f"✅ SSH connection successful to {instance_ip}")
            
            # Download and deploy with proper commands
            commands = [
                f"sudo yum update -y",
                f"sudo yum install -y docker wget unzip",
                f"sudo service docker start",
                f"sudo usermod -a -G docker ec2-user",
                f"wget {s3_url} -O {project_name}.zip",
                f"unzip -o {project_name}.zip",
                f"cd {project_name} && sudo docker build -t {project_name} .",
                f"sudo docker stop {project_name} || true",
                f"sudo docker rm {project_name} || true",
                f"sudo docker run -d -p {port}:8000 --name {project_name} {project_name}"
            ]
            
            for i, cmd in enumerate(commands, 1):
                logging.info(f"🔧 Executing command {i}/{len(commands)}: {cmd}")
                stdin, stdout, stderr = ssh.exec_command(cmd, timeout=300)
                
                # Wait for command to complete
                exit_status = stdout.channel.recv_exit_status()
                output = stdout.read().decode().strip()
                error = stderr.read().decode().strip()
                
                if exit_status != 0:
                    logging.error(f"❌ Command {i} failed (exit code {exit_status}): {cmd}")
                    logging.error(f"Error: {error}")
                    if "docker" in cmd.lower():
                        logging.error("Docker command failed - check if Docker is installed and running")
                    raise Exception(f"Command failed: {cmd} - {error}")
                else:
                    logging.info(f"✅ Command {i} successful")
                    if output:
                        logging.info(f"Output: {output[:200]}...")
            
            # Verify deployment
            logging.info(f"🔍 Verifying deployment...")
            stdin, stdout, stderr = ssh.exec_command(f"sudo docker ps | grep {project_name}")
            container_status = stdout.read().decode().strip()
            
            if container_status:
                logging.info(f"✅ Container is running: {container_status}")
                deployment_status = "deployed"
            else:
                logging.warning(f"⚠️ Container might not be running properly")
                deployment_status = "deployed_with_warnings"
            
            ssh.close()
            
            return {
                "status": deployment_status,
                "url": f"http://{instance_ip}:{port}",
                "port": port,
                "container_status": container_status
            }
            
        except Exception as e:
            if not mock_mode:
                logging.error(f"❌ SSH connection failed to {instance_ip}: {str(e)}")
                logging.error("💡 Possible issues:")
                logging.error("   1. Security Group doesn't allow SSH (port 22) from your IP")
                logging.error("   2. EC2 instance might be stopped")
                logging.error("   3. SSH key format might be wrong")
                logging.error("   4. Instance IP might have changed")
            raise Exception(f"SSH connection failed to {instance_ip}: {str(e)}")
    
    def _get_user_data_script(self) -> str:
        """Get user data script to install Docker on EC2."""
        return """#!/bin/bash
yum update -y
yum install -y docker
service docker start
usermod -a -G docker ec2-user
yum install -y nginx
service nginx start
chkconfig nginx on
"""