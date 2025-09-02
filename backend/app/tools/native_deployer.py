import boto3
import logging
import base64
import time
from typing import Dict, Any

class NativeDeployer:
    """Deploy applications natively without Docker - faster and simpler."""
    
    def __init__(self, region: str = "ap-south-2"):
        self.region = region
        self.ec2 = boto3.client('ec2', region_name=region)
        # Fix S3 client to use regional endpoint
        self.s3 = boto3.client(
            's3', 
            region_name=region,
            config=boto3.session.Config(
                s3={'addressing_style': 'virtual'},
                signature_version='s3v4'
            )
        )
    
    def deploy_native(self, project_path: str, project_name: str, technology: str, readme_config: dict = None) -> Dict[str, Any]:
        """Deploy application natively without Docker."""
        try:
            print(f"NATIVE DEPLOYER: Starting deployment for {project_name}")
            logging.info(f"NATIVE DEPLOYMENT: {project_name} ({technology})")
            
            # Upload to S3 for native deployer
            s3_url = self.upload_to_s3(project_path, project_name)
            logging.info(f"S3 upload successful")
            
            # Create placeholder instance_info for compatibility
            instance_info = {"instance_id": "pending", "public_ip": "pending", "ami_type": "ubuntu"}
            
            # Deploy to EC2 with user data script
            deployment_urls = self.deploy_to_ec2_native(
                instance_info, s3_url, project_name, technology, readme_config
            )
            
            print(f"NATIVE: Deployment completed successfully")
            print(f"Instance IP: {deployment_urls.get('latest_ip', 'unknown')}")
            logging.info(f"Deployment successful - IP: {deployment_urls.get('latest_ip')}")
            
            return {
                "status": "deployed",
                "deployment_type": "native",
                "frontend_url": deployment_urls["frontend_url"],
                "backend_url": deployment_urls["backend_url"],
                "api_docs_url": deployment_urls.get("api_docs_url", deployment_urls["backend_url"] + "/docs"),
                "direct_backend_url": deployment_urls.get("direct_backend_url", deployment_urls["backend_url"]),
                "instance_id": instance_info["instance_id"],
                "public_ip": deployment_urls.get("latest_ip", instance_info["public_ip"]),
                "deployment_verified": deployment_urls.get("verified", False),
                "technology": technology,
                "note": f"Native {technology} deployment completed"
            }
            
        except Exception as e:
            print(f"NATIVE DEPLOYER FAILED: {str(e)}")
            logging.error(f"Native deployment failed: {str(e)}")
            raise Exception(f"Native deployment failed: {str(e)}")
    
    def upload_to_s3(self, project_path: str, project_name: str) -> str:
        """Upload project to S3."""
        try:
            bucket_name = f"coastal-seven-native-{self.region}"
            
            # Create bucket
            try:
                if self.region == 'ap-south-2':
                    self.s3.create_bucket(Bucket=bucket_name)
                else:
                    self.s3.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': self.region}
                    )
            except:
                pass  # Bucket exists
            
            # Create zip
            import zipfile
            import io
            import os
            
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for root, dirs, files in os.walk(project_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, project_path)
                        zip_file.write(file_path, arc_name)
            
            # Upload to S3
            key = f"{project_name}.zip"
            self.s3.put_object(
                Bucket=bucket_name,
                Key=key,
                Body=zip_buffer.getvalue()
            )
            
            # Return public URL (bucket is configured for public read access)
            return f"https://{bucket_name}.s3.{self.region}.amazonaws.com/{key}"
            
        except Exception as e:
            logging.error(f"S3 upload failed: {str(e)}")
            raise
    
    def launch_new_instance(self, project_name: str, user_data_script: str) -> Dict[str, str]:
        """Launch fresh EC2 instance for each deployment."""
        try:
            print(f"NATIVE: Launching new instance for {project_name}")
            
            # Terminate old instances for this project (cost management)
            self._cleanup_old_instances(project_name)
            
            # Launch new instance with user data
            response = self.ec2.run_instances(
                ImageId='ami-0bd4cda58efa33d23',  # Your working Ubuntu 24.04 AMI
                MinCount=1,
                MaxCount=1,
                InstanceType='t3.large',  # Your working instance type
                KeyName='hyd',  # Your working key pair
                SecurityGroupIds=['sg-04bc63d3fe14b1811'],  # Your ec2 security group with 5 inbound rules
                UserData=user_data_script,
                Placement={'AvailabilityZone': 'ap-south-2c'},  # Use your preferred AZ
                TagSpecifications=[
                    {
                        'ResourceType': 'instance',
                        'Tags': [
                            {'Key': 'Name', 'Value': f'coastal-seven-{project_name}'},
                            {'Key': 'Project', 'Value': project_name},
                            {'Key': 'CreatedBy', 'Value': 'CoastalSevenAgent'}
                        ]
                    }
                ]
            )
            
            instance_id = response['Instances'][0]['InstanceId']
            print(f"NATIVE: Instance launched: {instance_id}")
            
            # Wait for instance to be running
            print(f"NATIVE: Waiting for instance to be running...")
            waiter = self.ec2.get_waiter('instance_running')
            waiter.wait(InstanceIds=[instance_id])
            
            # Get instance details
            response = self.ec2.describe_instances(InstanceIds=[instance_id])
            instance = response['Reservations'][0]['Instances'][0]
            public_ip = instance.get('PublicIpAddress', 'No-IP')
            
            print(f"NATIVE: Instance running with IP: {public_ip}")
            
            return {
                "instance_id": instance_id,
                "public_ip": public_ip,
                "ami_type": "ubuntu"
            }
            
        except Exception as e:
            logging.error(f"Failed to launch instance: {str(e)}")
            raise
    
    def _cleanup_old_instances(self, project_name: str) -> None:
        """Terminate old instances for the same project to manage costs."""
        try:
            print(f"NATIVE: Cleaning up old instances for {project_name}")
            
            # Find instances for this project
            response = self.ec2.describe_instances(
                Filters=[
                    {'Name': 'tag:Project', 'Values': [project_name]},
                    {'Name': 'tag:CreatedBy', 'Values': ['CoastalSevenAgent']},
                    {'Name': 'instance-state-name', 'Values': ['running', 'stopped']}
                ]
            )
            
            instances_to_terminate = []
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instances_to_terminate.append(instance['InstanceId'])
            
            if instances_to_terminate:
                print(f"NATIVE: Terminating {len(instances_to_terminate)} old instances")
                self.ec2.terminate_instances(InstanceIds=instances_to_terminate)
            else:
                print(f"NATIVE: No old instances to cleanup")
                
        except Exception as e:
            print(f"NATIVE: Cleanup failed: {str(e)} (continuing anyway)")
    
    def deploy_to_ec2_native(self, instance_info: Dict, s3_url: str, project_name: str, technology: str, readme_config: dict = None) -> Dict[str, str]:
        """Deploy to EC2 by launching fresh instance with user data."""
        
        # Create native deployment script using README commands
        print(f"NATIVE: Creating user data script")
        deployment_script = self.create_native_script(s3_url, project_name, technology, readme_config)
        print(f"NATIVE: User data script generated ({len(deployment_script)} chars)")
        print(f"Script preview: {deployment_script[:200]}...")
        
        try:
            # Launch NEW instance with user data (this will execute properly)
            instance_info = self.launch_new_instance(project_name, deployment_script)
            instance_id = instance_info["instance_id"]
            latest_ip = instance_info["public_ip"]
            
            print(f"NATIVE: Fresh instance launched with IP: {latest_ip}")
            print(f"NATIVE: User data script is now executing on fresh instance...")
            logging.info(f"Fresh instance launched with IP: {latest_ip}")
            logging.info(f"User data script executing on launch...")
            
            # WAIT FOR INSTANCE TO FULLY INITIALIZE
            print(f"NATIVE: Waiting for instance to fully initialize...")
            self._wait_for_instance_ready(instance_id)
            
            # MONITOR AWS INTERNAL PROCESSES
            print(f"NATIVE: Monitoring AWS internal processes...")
            self._monitor_aws_internals(instance_id, latest_ip)
            
            # WAIT FOR DEPLOYMENT TO COMPLETE
            deployment_successful = self._wait_for_deployment(latest_ip, readme_config, instance_id)
            
            if deployment_successful:
                print(f"NATIVE: Deployment verified - app is running!")
                logging.info(f"Deployment verified - app is running!")
            else:
                print(f"NATIVE: Deployment verification failed - check user data script")
                logging.warning(f"Deployment may still be in progress")
            
            # Use the LATEST IP for all URLs
            updated_ip = latest_ip
            
            # Return URLs based on technology
            if self._is_java_project(project_name, technology):
                # Java project - backend on 8000, frontend on 3000
                return {
                    "frontend_url": f"http://{updated_ip}:3000",
                    "backend_url": f"http://{updated_ip}:8000",
                    "api_docs_url": f"http://{updated_ip}:8000/api/employees",
                    "direct_backend_url": f"http://{updated_ip}:8000",
                    "latest_ip": updated_ip,
                    "verified": deployment_successful
                }
            elif readme_config and readme_config.get('deployment_commands', {}).get('frontend'):
                # Full-stack app - return frontend as main URL
                return {
                    "frontend_url": f"http://{updated_ip}:3000",
                    "backend_url": f"http://{updated_ip}:8000",
                    "api_docs_url": f"http://{updated_ip}:8000/docs",
                    "direct_backend_url": f"http://{updated_ip}:8000",
                    "latest_ip": updated_ip,
                    "verified": deployment_successful
                }
            elif technology.lower() in ['python', 'fastapi']:
                return {
                    "frontend_url": f"http://{updated_ip}:8000",
                    "backend_url": f"http://{updated_ip}:8000",
                    "api_docs_url": f"http://{updated_ip}:8000/docs",
                    "direct_backend_url": f"http://{updated_ip}:8000",
                    "latest_ip": updated_ip
                }
            elif technology.lower() in ['node', 'nodejs', 'express']:
                return {
                    "frontend_url": f"http://{updated_ip}:3000",
                    "backend_url": f"http://{updated_ip}:3000",
                    "api_docs_url": f"http://{updated_ip}:3000/docs",
                    "direct_backend_url": f"http://{updated_ip}:3000",
                    "latest_ip": updated_ip
                }
            else:
                return {
                    "frontend_url": f"http://{updated_ip}:8000",
                    "backend_url": f"http://{updated_ip}:8000",
                    "api_docs_url": f"http://{updated_ip}:8000/docs",
                    "direct_backend_url": f"http://{updated_ip}:8000",
                    "latest_ip": updated_ip
                }
            
        except Exception as e:
            print(f"NATIVE: Deploy to EC2 failed: {str(e)}")
            logging.error(f"Failed to deploy natively: {str(e)}")
            # Don't return fake success - raise the error
            raise Exception(f"EC2 deployment failed: {str(e)}")
    
    def create_native_script(self, s3_url: str, project_name: str, technology: str, readme_config: dict = None) -> str:
        """Create native deployment script using README commands from LLM."""
        
        # Pure shell script format - most reliable
        # Sanitize project name for filename
        safe_filename = project_name.replace(' ', '_').replace('/', '_')
        
        base_config = f'''#!/bin/bash
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
echo "=== DEPLOYMENT START $(date) ==="
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt update && apt install -y nodejs wget unzip python3 python3-pip python3-venv curl
cd /home/ubuntu && wget "{s3_url}" -O "{safe_filename}.zip"
cd /home/ubuntu && unzip -o "{safe_filename}.zip"
chown -R ubuntu:ubuntu /home/ubuntu/
echo "Project extracted"
'''
        
        # Detect Java project and handle it
        if self._is_java_project(project_name, technology):
            return self._create_java_deployment_script(base_config, project_name)
        
        # Use README-based commands if available
        if readme_config and 'deployment_commands' in readme_config:
            backend_config = readme_config['deployment_commands'].get('backend', {})
            frontend_config = readme_config['deployment_commands'].get('frontend', {})
            
            # Deploy backend
            backend_build = backend_config.get('build_commands', [])
            backend_run = backend_config.get('run_command', '')
            
            # Ensure backend_build is not None
            if backend_build is None:
                backend_build = []
            if backend_run is None:
                backend_run = ''
            
            # Add backend deployment with proper shell script format
            if backend_build or backend_run:
                base_config += f'echo "Deploying backend..." >> /var/log/deployment.log\n'
                # Install Python dependencies first
                base_config += f'cd /home/ubuntu/backend && python3 -m venv venv\n'
                base_config += f'cd /home/ubuntu/backend && source venv/bin/activate && pip install --upgrade pip\n'
                base_config += f'cd /home/ubuntu/backend && source venv/bin/activate && pip install fastapi uvicorn\n'
                base_config += f'cd /home/ubuntu/backend && source venv/bin/activate && pip install -r requirements.txt || echo "No requirements.txt found"\n'
                
                for cmd in backend_build:
                    linux_cmd = self._convert_to_linux_command(cmd)
                    if linux_cmd.startswith('cd '):
                        # Handle directory change - go to backend directly
                        base_config += f'cd /home/ubuntu/backend\n'
                    else:
                        # Execute command in backend directory with venv
                        base_config += f'cd /home/ubuntu/backend && source venv/bin/activate && {linux_cmd}\n'
                
                if backend_run:
                    linux_run_cmd = self._convert_to_linux_command(backend_run)
                    base_config += f'cd /home/ubuntu/backend && source venv/bin/activate && nohup {linux_run_cmd} > /var/log/backend.log 2>&1 &\n'
            
            # Add frontend deployment with proper shell script format
            if frontend_config:
                frontend_build = frontend_config.get('build_commands', [])
                frontend_run = frontend_config.get('run_command', '')
                
                # Ensure frontend_build is not None
                if frontend_build is None:
                    frontend_build = []
                if frontend_run is None:
                    frontend_run = ''
                
                if frontend_build or frontend_run:
                    base_config += f'echo "Deploying frontend..." >> /var/log/deployment.log\n'
                    # Fix npm permissions and install dependencies
                    base_config += f'chown -R ubuntu:ubuntu /home/ubuntu/frontend\n'
                    base_config += f'cd /home/ubuntu/frontend && npm cache clean --force\n'
                    base_config += f'cd /home/ubuntu/frontend && npm install --no-optional\n'
                    base_config += f'chmod +x /home/ubuntu/frontend/node_modules/.bin/*\n'
                    # Set backend URL environment variable for frontend and update source files
                    base_config += f'export REACT_APP_BACKEND_URL=http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8000\n'
                    base_config += f'PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)\n'
                    base_config += f'sed -i "s/localhost:8080/$PUBLIC_IP:8000/g" *.html *.js *.jsx *.ts *.tsx *.json 2>/dev/null || true\n'
                    base_config += f'sed -i "s/127.0.0.1:8080/$PUBLIC_IP:8000/g" *.html *.js *.jsx *.ts *.tsx *.json 2>/dev/null || true\n'
                    
                    for cmd in frontend_build:
                        linux_cmd = self._convert_to_linux_command(cmd)
                        if linux_cmd.startswith('cd '):
                            # Handle directory change - go to frontend directly
                            base_config += f'cd /home/ubuntu/frontend\n'
                        else:
                            # Execute command in frontend directory
                            base_config += f'cd /home/ubuntu/frontend && {linux_cmd}\n'
                    
                    if frontend_run:
                        linux_run_cmd = self._convert_to_linux_command(frontend_run)
                        base_config += f'cd /home/ubuntu/frontend && nohup {linux_run_cmd} > /var/log/frontend.log 2>&1 &\n'
            
            base_config += f'sleep 10\necho "=== DEPLOYMENT COMPLETED $(date) ===" >> /var/log/deployment.log\n'
            return base_config
        
        # Fallback to generic commands if no README config
        return self._create_fallback_config(base_config, technology, project_name)
    
    def _is_java_project(self, project_name: str, technology: str) -> bool:
        """Detect if this is a Java project"""
        return (
            'java' in technology.lower() or 
            'JAVA' in project_name.upper() or
            'spring' in technology.lower()
        )
    
    def _create_java_deployment_script(self, base_config: str, project_name: str) -> str:
        """Create Java-specific deployment script"""
        return base_config + f'''# Install Java
apt update && apt install -y openjdk-17-jdk
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export PATH=$JAVA_HOME/bin:$PATH

# Compile and run Java backend (modify to run on port 8000)
cd /home/ubuntu/backend
echo "Modifying Java source to use port 8000..." >> /var/log/deployment.log
# Change ALL port references to 8000 in Java source files
sed -i 's/8080/8000/g' *.java
sed -i 's/8081/8000/g' *.java
sed -i 's/8082/8000/g' *.java
sed -i 's/3000/8000/g' *.java
# Also change any hardcoded port numbers in comments or strings
sed -i 's/port 8080/port 8000/g' *.java
sed -i 's/port 8081/port 8000/g' *.java
echo "Compiling Java files..." >> /var/log/deployment.log
javac *.java
echo "Starting Java server on port 8000..." >> /var/log/deployment.log
nohup java EmployeeServer > /var/log/backend.log 2>&1 &

# Update frontend to use correct backend URL
cd /home/ubuntu/frontend
echo "Updating frontend to connect to backend..." >> /var/log/deployment.log
# Get public IP and update ALL possible backend URL references
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
# Replace all localhost references with public IP and port 8000
sed -i "s/localhost:8080/$PUBLIC_IP:8000/g" *.html *.js 2>/dev/null || true
sed -i "s/localhost:8081/$PUBLIC_IP:8000/g" *.html *.js 2>/dev/null || true
sed -i "s/localhost:8082/$PUBLIC_IP:8000/g" *.html *.js 2>/dev/null || true
sed -i "s/localhost:3000/$PUBLIC_IP:8000/g" *.html *.js 2>/dev/null || true
# Also handle 127.0.0.1 references
sed -i "s/127.0.0.1:8080/$PUBLIC_IP:8000/g" *.html *.js 2>/dev/null || true
sed -i "s/127.0.0.1:8081/$PUBLIC_IP:8000/g" *.html *.js 2>/dev/null || true
sed -i "s/127.0.0.1:3000/$PUBLIC_IP:8000/g" *.html *.js 2>/dev/null || true
echo "Frontend updated to use backend at $PUBLIC_IP:8000" >> /var/log/deployment.log
echo "Starting frontend server on port 3000..." >> /var/log/deployment.log
nohup python3 -m http.server 3000 > /var/log/frontend.log 2>&1 &

echo "=== DEPLOYMENT COMPLETED $(date) ===" >> /var/log/deployment.log
'''
    
    def _create_fallback_config(self, base_config: str, technology: str, project_name: str = "Demo2") -> str:
        """Universal fallback script for any programming language."""
        
        tech = technology.lower()
        
        # Python technologies
        if tech in ['python', 'fastapi', 'django', 'flask']:
            return base_config + f'''cd /home/ubuntu/backend
# Update Python source to use port 8000
sed -i 's/port=8080/port=8000/g' *.py 2>/dev/null || true
sed -i 's/port=3000/port=8000/g' *.py 2>/dev/null || true
sed -i 's/:8080/:8000/g' *.py 2>/dev/null || true
python3 -m venv venv
source venv/bin/activate && pip install --upgrade pip
source venv/bin/activate && pip install fastapi uvicorn django flask
source venv/bin/activate && pip install -r requirements.txt || echo "No requirements.txt found"
source venv/bin/activate && nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > /var/log/app.log 2>&1 & || nohup python3 manage.py runserver 0.0.0.0:8000 > /var/log/app.log 2>&1 & || nohup python3 app.py > /var/log/app.log 2>&1 &
# Update frontend if exists
if [ -d "/home/ubuntu/frontend" ]; then
  cd /home/ubuntu/frontend
  PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
  sed -i "s/localhost:8080/$PUBLIC_IP:8000/g" *.html *.js 2>/dev/null || true
  sed -i "s/127.0.0.1:8080/$PUBLIC_IP:8000/g" *.html *.js 2>/dev/null || true
fi
echo "Python app started" >> /var/log/deployment.log
'''
        
        # Node.js technologies
        elif tech in ['node', 'nodejs', 'javascript', 'express', 'react', 'vue', 'angular']:
            return base_config + f'''cd /home/ubuntu/frontend || cd /home/ubuntu/{project_name}
# Update Node.js source to use port 8000 for backend connections
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
sed -i "s/localhost:8080/$PUBLIC_IP:8000/g" *.js *.jsx *.ts *.tsx *.html *.json 2>/dev/null || true
sed -i "s/127.0.0.1:8080/$PUBLIC_IP:8000/g" *.js *.jsx *.ts *.tsx *.html *.json 2>/dev/null || true
sed -i 's/port.*8080/port: 8000/g' *.js *.json 2>/dev/null || true
chown -R ubuntu:ubuntu .
npm cache clean --force
npm install --no-optional
chmod +x node_modules/.bin/*
npm run build || echo "Build not needed"
nohup npm start > /var/log/app.log 2>&1 & || nohup npx serve -s build -l 3000 > /var/log/app.log 2>&1 &
echo "Node.js app started" >> /var/log/deployment.log
'''
        
        # Java technologies
        elif tech in ['java', 'spring', 'kotlin']:
            return base_config + f'''apt install -y openjdk-17-jdk maven
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export PATH=$JAVA_HOME/bin:$PATH
cd /home/ubuntu/backend
# Change ALL port references to 8000 in Java source
sed -i 's/8080/8000/g' *.java
sed -i 's/8081/8000/g' *.java
sed -i 's/8082/8000/g' *.java
sed -i 's/3000/8000/g' *.java
javac *.java
nohup java EmployeeServer > /var/log/app.log 2>&1 &
cd /home/ubuntu/frontend
# Update frontend to connect to backend on port 8000
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
sed -i "s/localhost:8080/$PUBLIC_IP:8000/g" *.html *.js 2>/dev/null || true
sed -i "s/localhost:8081/$PUBLIC_IP:8000/g" *.html *.js 2>/dev/null || true
sed -i "s/127.0.0.1:8080/$PUBLIC_IP:8000/g" *.html *.js 2>/dev/null || true
nohup python3 -m http.server 3000 > /var/log/frontend.log 2>&1 &
echo "Java app started" >> /var/log/deployment.log
'''
        
        # Go technologies
        elif tech in ['go', 'golang']:
            return base_config + f'''apt install -y golang-go
cd /home/ubuntu/{project_name}
go mod download && go build
nohup ./main > /var/log/app.log 2>&1 & || nohup go run main.go > /var/log/app.log 2>&1 &
echo "Go app started" >> /var/log/deployment.log
'''
        
        # PHP technologies
        elif tech in ['php', 'laravel', 'symfony']:
            return base_config + f'''apt install -y php php-cli composer
cd /home/ubuntu/{project_name}
composer install
nohup php artisan serve --host=0.0.0.0 --port=8000 > /var/log/app.log 2>&1 & || nohup php -S 0.0.0.0:8000 > /var/log/app.log 2>&1 &
echo "PHP app started" >> /var/log/deployment.log
'''
        
        # Ruby technologies
        elif tech in ['ruby', 'rails', 'sinatra']:
            return base_config + f'''apt install -y ruby ruby-dev bundler
cd /home/ubuntu/{project_name}
bundle install
nohup rails server -b 0.0.0.0 -p 3000 > /var/log/app.log 2>&1 & || nohup ruby app.rb > /var/log/app.log 2>&1 &
echo "Ruby app started" >> /var/log/deployment.log
'''
        
        # C# technologies
        elif tech in ['csharp', 'c#', 'dotnet', '.net']:
            return base_config + f'''wget https://packages.microsoft.com/config/ubuntu/24.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
dpkg -i packages-microsoft-prod.deb && apt update && apt install -y dotnet-sdk-8.0
cd /home/ubuntu/{project_name}
dotnet restore && dotnet build
nohup dotnet run --urls=http://0.0.0.0:5000 > /var/log/app.log 2>&1 &
echo "C# app started" >> /var/log/deployment.log
'''
        
        # Rust technologies
        elif tech in ['rust', 'actix', 'rocket']:
            return base_config + f'''curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source ~/.cargo/env && cd /home/ubuntu/{project_name} && cargo build --release
nohup ./target/release/* > /var/log/app.log 2>&1 & || nohup cargo run > /var/log/app.log 2>&1 &
echo "Rust app started" >> /var/log/deployment.log
'''
        
        # Static/HTML technologies
        elif tech in ['static', 'html', 'css', 'js']:
            return base_config + f'''cd /home/ubuntu/{project_name}
nohup python3 -m http.server 8080 --bind 0.0.0.0 > /var/log/app.log 2>&1 &
echo "Static site started" >> /var/log/deployment.log
'''
        
        else:
            # Universal detection fallback
            return base_config + f'''cd /home/ubuntu/{project_name}
echo "Detecting technology for: {technology}" >> /var/log/deployment.log
if [ -f requirements.txt ]; then python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > /var/log/app.log 2>&1 &; fi
if [ -f package.json ]; then npm install && nohup npm start > /var/log/app.log 2>&1 &; fi
if [ -f pom.xml ]; then apt install -y openjdk-17-jdk maven && mvn clean install && nohup java -jar target/*.jar > /var/log/app.log 2>&1 &; fi
if [ -f go.mod ]; then apt install -y golang-go && go build && nohup ./main > /var/log/app.log 2>&1 &; fi
echo "Universal deployment completed" >> /var/log/deployment.log
'''
    
    def _wait_for_deployment(self, ip: str, readme_config: dict = None, instance_id: str = None) -> bool:
        """Wait for deployment to complete by checking if ports are open."""
        import socket
        import time
        
        # Determine which ports to check based on technology
        ports_to_check = []
        
        # Check if this is a Java project by looking at instance tags
        try:
            response = self.ec2.describe_instances(InstanceIds=[instance_id])
            instance = response['Reservations'][0]['Instances'][0]
            project_name = next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Project'), '')
            
            if 'JAVA' in project_name.upper():
                ports_to_check = [3000, 8000]  # Frontend and Java backend
            elif readme_config and readme_config.get('deployment_commands', {}).get('frontend'):
                ports_to_check = [3000, 8000]  # Frontend and backend
            else:
                ports_to_check = [8000]  # Just backend
        except:
            # Fallback
            if readme_config and readme_config.get('deployment_commands', {}).get('frontend'):
                ports_to_check = [3000, 8000]  # Frontend and backend
            else:
                ports_to_check = [8000]  # Just backend
        
        logging.info(f"Checking ports {ports_to_check} on {ip}")
        
        # Wait up to 8 minutes for deployment with monitoring
        max_wait_time = 480  # 8 minutes
        check_interval = 30   # Check every 30 seconds
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            ports_open = 0
            
            for port in ports_to_check:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex((ip, port))
                    sock.close()
                    
                    if result == 0:
                        ports_open += 1
                        logging.info(f"Port {port} is OPEN")
                    else:
                        logging.info(f"Port {port} is still closed")
                        
                except Exception as e:
                    logging.info(f"Error checking port {port}: {str(e)}")
            
            # Check if all required ports are open
            if ports_open == len(ports_to_check):
                logging.info(f"All ports open - deployment successful!")
                return True
            
            # Wait before next check with progress update
            print(f"AWS MONITOR: Waiting {check_interval}s... ({elapsed_time}/{max_wait_time}s elapsed)")
            logging.info(f"Waiting {check_interval}s before next check... ({elapsed_time}/{max_wait_time}s elapsed)")
            time.sleep(check_interval)
            elapsed_time += check_interval
            
            # Re-check AWS internals every 2 minutes
            if elapsed_time % 120 == 0 and instance_id:
                print(f"AWS MONITOR: Re-checking AWS internals at {elapsed_time}s...")
                self._monitor_aws_internals(instance_id, ip)
        
        logging.warning(f"Deployment verification timed out after {max_wait_time}s")
        return False
    
    def _monitor_aws_internals(self, instance_id: str, ip: str) -> None:
        """Monitor AWS internal processes during deployment."""
        try:
            print(f"AWS MONITOR: Checking instance system status...")
            
            # Check instance status
            status_response = self.ec2.describe_instance_status(InstanceIds=[instance_id])
            if status_response['InstanceStatuses']:
                status = status_response['InstanceStatuses'][0]
                system_status = status['SystemStatus']['Status']
                instance_status = status['InstanceStatus']['Status']
                
                print(f"AWS MONITOR: System Status: {system_status}")
                print(f"AWS MONITOR: Instance Status: {instance_status}")
            else:
                print(f"AWS MONITOR: No status information available yet")
            
            # Check console output for user data execution
            print(f"AWS MONITOR: Checking console output for user data execution...")
            try:
                console_output = self.ec2.get_console_output(InstanceId=instance_id)
                output = console_output.get('Output', '')
                
                if output:
                    print(f"AWS MONITOR: Console output available ({len(output)} chars)")
                    
                    # Look for cloud-init and user data execution
                    if 'cloud-init' in output:
                        print(f"AWS MONITOR: cloud-init is running")
                    else:
                        print(f"AWS MONITOR: cloud-init not found in console")
                    
                    if 'DEPLOYMENT START' in output:
                        print(f"✅ AWS MONITOR: User data script started")
                    else:
                        print(f"❌ AWS MONITOR: User data script not started yet")
                    
                    if 'DEPLOYMENT COMPLETED' in output:
                        print(f"✅ AWS MONITOR: User data script completed")
                    else:
                        print(f"⏳ AWS MONITOR: User data script still running")
                    
                    # Check for errors
                    if 'error' in output.lower() or 'failed' in output.lower():
                        print(f"⚠️  AWS MONITOR: Errors detected in console output")
                        # Extract error lines
                        lines = output.split('\n')
                        error_lines = [line for line in lines if 'error' in line.lower() or 'failed' in line.lower()]
                        for error_line in error_lines[-5:]:  # Last 5 error lines
                            print(f"❌ AWS ERROR: {error_line}")
                    
                    # Show last few lines of console output
                    lines = output.split('\n')
                    print(f"📝 AWS MONITOR: Last 5 console lines:")
                    for line in lines[-5:]:
                        if line.strip():
                            print(f"   {line}")
                else:
                    print(f"❌ AWS MONITOR: No console output available yet")
                    
            except Exception as console_error:
                print(f"⚠️  AWS MONITOR: Console output error: {str(console_error)}")
            
            # Check CloudWatch logs if available
            print(f"🔍 AWS MONITOR: Checking for CloudWatch logs...")
            try:
                import boto3
                logs_client = boto3.client('logs', region_name=self.region)
                
                # Look for common log groups
                log_groups = ['/aws/ec2/user-data', f'/aws/ec2/{instance_id}']
                
                for log_group in log_groups:
                    try:
                        streams = logs_client.describe_log_streams(logGroupName=log_group)
                        if streams['logStreams']:
                            print(f"✅ AWS MONITOR: Found CloudWatch logs in {log_group}")
                        else:
                            print(f"❌ AWS MONITOR: No streams in {log_group}")
                    except:
                        print(f"❌ AWS MONITOR: Log group {log_group} not found")
                        
            except Exception as logs_error:
                print(f"⚠️  AWS MONITOR: CloudWatch logs error: {str(logs_error)}")
            
            # Check if SSH is available for direct log access
            print(f"🔍 AWS MONITOR: Testing SSH connectivity for direct log access...")
            try:
                import paramiko
                import os
                
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
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
                
                if key_file:
                    ssh.connect(
                        hostname=ip,
                        username='ubuntu',
                        key_filename=key_file,
                        timeout=10
                    )
                    
                    print(f"✅ AWS MONITOR: SSH connection successful")
                    
                    # Check deployment log
                    stdin, stdout, stderr = ssh.exec_command("cat /var/log/deployment.log")
                    deployment_log = stdout.read().decode('utf-8', errors='ignore')
                    
                    if deployment_log:
                        print(f"📝 AWS MONITOR: Deployment log found ({len(deployment_log)} chars)")
                        lines = deployment_log.split('\n')
                        print(f"📝 AWS MONITOR: Last 10 deployment log lines:")
                        for line in lines[-10:]:
                            if line.strip():
                                print(f"   {line}")
                    else:
                        print(f"❌ AWS MONITOR: No deployment log found")
                    
                    # Check cloud-init logs
                    stdin, stdout, stderr = ssh.exec_command("tail -20 /var/log/cloud-init-output.log")
                    cloud_init_log = stdout.read().decode('utf-8', errors='ignore')
                    
                    if cloud_init_log:
                        print(f"📝 AWS MONITOR: Cloud-init log found")
                        print(f"📝 AWS MONITOR: Last 10 cloud-init lines:")
                        lines = cloud_init_log.split('\n')
                        for line in lines[-10:]:
                            if line.strip():
                                print(f"   {line}")
                    
                    ssh.close()
                    
                else:
                    print(f"❌ AWS MONITOR: SSH key not found")
                    
            except Exception as ssh_error:
                print(f"⚠️  AWS MONITOR: SSH monitoring failed: {str(ssh_error)}")
            
        except Exception as e:
            print(f"⚠️  AWS MONITOR: Monitoring failed: {str(e)}")
    
    def _convert_to_linux_command(self, command: str) -> str:
        """Convert Windows commands to Linux equivalents."""
        if not command:
            return command
        
        # Windows to Linux command mappings
        conversions = {
            'python ': 'python3 ',
            'py ': 'python3 ',
            'pip ': 'pip3 ',
            'python.exe': 'python3',
            'py.exe': 'python3',
            'pip.exe': 'pip3',
            'node.exe': 'node',
            'npm.exe': 'npm',
            'dotnet.exe': 'dotnet',
            'java.exe': 'java',
            'mvn.cmd': 'mvn',
            'gradle.bat': 'gradle',
            'composer.phar': 'composer',
            'bundle.exe': 'bundle',
            'cargo.exe': 'cargo',
            'go.exe': 'go',
            'php.exe': 'php',
            'ruby.exe': 'ruby',
            'rails.exe': 'rails'
        }
        
        # Apply conversions
        linux_command = command
        for windows_cmd, linux_cmd in conversions.items():
            linux_command = linux_command.replace(windows_cmd, linux_cmd)
        
        # Fix common uvicorn mistakes
        linux_command = linux_command.replace('maiapp', 'main:app')  # Fix typo
        linux_command = linux_command.replace('main:app', 'main:app')  # Keep correct format
        
        # Fix path separators
        linux_command = linux_command.replace('\\', '/')
        
        # Fix drive letters (C:\ -> /) - only at start of paths
        import re
        linux_command = re.sub(r'\b[A-Za-z]:[/\\]', '/', linux_command)
        
        return linux_command
    
    def _wait_for_instance_ready(self, instance_id: str) -> None:
        """Wait for instance to be fully ready before checking deployment."""
        try:
            print(f"⏳ AWS MONITOR: Waiting for instance system checks to pass...")
            
            # Wait for system status checks to pass
            waiter = self.ec2.get_waiter('system_status_ok')
            waiter.wait(
                InstanceIds=[instance_id],
                WaiterConfig={
                    'Delay': 15,  # Check every 15 seconds
                    'MaxAttempts': 20  # Wait up to 5 minutes
                }
            )
            
            print(f"✅ AWS MONITOR: Instance system checks passed")
            
            # Additional wait for user data to start
            print(f"⏳ AWS MONITOR: Waiting additional 60s for user data to start...")
            import time
            time.sleep(60)
            
            print(f"✅ AWS MONITOR: Instance should be ready for user data execution")
            
        except Exception as e:
            print(f"⚠️  AWS MONITOR: Instance ready wait failed: {str(e)}")
            print(f"⏳ AWS MONITOR: Continuing anyway after 2 minutes...")
            import time
            time.sleep(120)  # Wait 2 minutes as fallback