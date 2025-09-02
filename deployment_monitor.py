#!/usr/bin/env python3
import boto3
import paramiko
import time
import json
from datetime import datetime
import os

class DeploymentMonitor:
    def __init__(self):
        self.region = 'ap-south-2'
        self.ec2 = boto3.client('ec2', region_name=self.region)
        self.key_file = 'd:\\Coastal_seven\\AGENT-SDLC\\backend\\hyd.pem'
        self.log_file = f"deployment_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
    def log(self, message):
        """Log message to both console and file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
    
    def monitor_deployment(self, project_name="JAVA FB"):
        """Monitor complete deployment process"""
        
        self.log("="*80)
        self.log("COASTAL SEVEN DEPLOYMENT MONITOR STARTED")
        self.log("="*80)
        
        # Step 1: Find the latest instance
        instance_info = self.find_latest_instance(project_name)
        if not instance_info:
            self.log("ERROR: No instances found for project")
            return
        
        instance_id = instance_info['instance_id']
        public_ip = instance_info['public_ip']
        
        self.log(f"MONITORING INSTANCE: {instance_id}")
        self.log(f"PUBLIC IP: {public_ip}")
        
        # Step 2: Wait for instance to be running
        self.wait_for_instance_running(instance_id)
        
        # Step 3: Wait for SSH to be available
        self.wait_for_ssh_ready(public_ip)
        
        # Step 4: Monitor cloud-init progress
        self.monitor_cloud_init(public_ip)
        
        # Step 5: Monitor user data execution
        self.monitor_user_data_execution(public_ip)
        
        # Step 6: Monitor S3 download
        self.monitor_s3_download(public_ip)
        
        # Step 7: Monitor project extraction
        self.monitor_project_extraction(public_ip)
        
        # Step 8: Monitor backend deployment
        self.monitor_backend_deployment(public_ip)
        
        # Step 9: Monitor frontend deployment
        self.monitor_frontend_deployment(public_ip)
        
        # Step 10: Monitor port availability
        self.monitor_port_availability(public_ip)
        
        # Step 11: Final status report
        self.generate_final_report(public_ip, instance_id)
        
        self.log("="*80)
        self.log("DEPLOYMENT MONITORING COMPLETED")
        self.log(f"Full logs saved to: {self.log_file}")
        self.log("="*80)
    
    def find_latest_instance(self, project_name):
        """Find the latest instance for the project"""
        try:
            self.log("STEP 1: Finding latest instance...")
            
            response = self.ec2.describe_instances(
                Filters=[
                    {'Name': 'tag:Project', 'Values': [project_name]},
                    {'Name': 'tag:CreatedBy', 'Values': ['CoastalSevenAgent']},
                    {'Name': 'instance-state-name', 'Values': ['running', 'pending']}
                ]
            )
            
            instances = []
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instances.append({
                        'instance_id': instance['InstanceId'],
                        'public_ip': instance.get('PublicIpAddress', 'No-IP'),
                        'launch_time': instance['LaunchTime'],
                        'state': instance['State']['Name']
                    })
            
            if not instances:
                return None
            
            # Get the latest instance
            latest = max(instances, key=lambda x: x['launch_time'])
            self.log(f"Found latest instance: {latest['instance_id']} ({latest['state']})")
            return latest
            
        except Exception as e:
            self.log(f"ERROR finding instance: {e}")
            return None
    
    def wait_for_instance_running(self, instance_id):
        """Wait for instance to be in running state"""
        self.log("STEP 2: Waiting for instance to be running...")
        
        try:
            waiter = self.ec2.get_waiter('instance_running')
            waiter.wait(InstanceIds=[instance_id])
            self.log("Instance is now RUNNING")
        except Exception as e:
            self.log(f"ERROR waiting for instance: {e}")
    
    def wait_for_ssh_ready(self, public_ip):
        """Wait for SSH to be available"""
        self.log("STEP 3: Waiting for SSH to be ready...")
        
        max_attempts = 20
        for attempt in range(max_attempts):
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(hostname=public_ip, username='ubuntu', key_filename=self.key_file, timeout=10)
                ssh.close()
                self.log("SSH is now READY")
                return True
            except Exception as e:
                self.log(f"SSH attempt {attempt+1}/{max_attempts}: {e}")
                time.sleep(15)
        
        self.log("ERROR: SSH never became available")
        return False
    
    def monitor_cloud_init(self, public_ip):
        """Monitor cloud-init status"""
        self.log("STEP 4: Monitoring cloud-init...")
        
        max_wait = 300  # 5 minutes
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(hostname=public_ip, username='ubuntu', key_filename=self.key_file, timeout=10)
                
                # Check cloud-init status
                stdin, stdout, stderr = ssh.exec_command("cloud-init status")
                status = stdout.read().decode('utf-8', errors='ignore').strip()
                
                self.log(f"Cloud-init status: {status}")
                
                if "done" in status:
                    self.log("Cloud-init COMPLETED")
                    ssh.close()
                    return True
                elif "error" in status:
                    self.log("Cloud-init FAILED")
                    ssh.close()
                    return False
                
                ssh.close()
                time.sleep(10)
                
            except Exception as e:
                self.log(f"Error checking cloud-init: {e}")
                time.sleep(10)
        
        self.log("Cloud-init monitoring TIMEOUT")
        return False
    
    def monitor_user_data_execution(self, public_ip):
        """Monitor user data script execution"""
        self.log("STEP 5: Monitoring user data execution...")
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=public_ip, username='ubuntu', key_filename=self.key_file, timeout=10)
            
            # Get full user data log
            stdin, stdout, stderr = ssh.exec_command("cat /var/log/user-data.log")
            user_data_log = stdout.read().decode('utf-8', errors='ignore')
            
            self.log("USER DATA LOG:")
            self.log("-" * 60)
            for line in user_data_log.split('\n'):
                if line.strip():
                    self.log(f"  {line}")
            self.log("-" * 60)
            
            # Check if script started
            if "DEPLOYMENT START" in user_data_log:
                self.log("User data script STARTED")
            else:
                self.log("ERROR: User data script did NOT start")
            
            ssh.close()
            
        except Exception as e:
            self.log(f"ERROR monitoring user data: {e}")
    
    def monitor_s3_download(self, public_ip):
        """Monitor S3 download process"""
        self.log("STEP 6: Monitoring S3 download...")
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=public_ip, username='ubuntu', key_filename=self.key_file, timeout=10)
            
            # Check for S3 download in logs
            stdin, stdout, stderr = ssh.exec_command("grep -A10 -B5 'wget.*s3.amazonaws.com' /var/log/user-data.log")
            s3_log = stdout.read().decode('utf-8', errors='ignore')
            
            if s3_log:
                self.log("S3 DOWNLOAD LOG:")
                self.log("-" * 40)
                for line in s3_log.split('\n'):
                    if line.strip():
                        self.log(f"  {line}")
                self.log("-" * 40)
                
                # Check what file was actually downloaded
                if "Demo2.zip" in s3_log:
                    self.log("WARNING: Downloaded Demo2.zip instead of JAVA FB.zip!")
                    self.log("This indicates S3 bucket has old Demo2.zip file")
                elif "JAVA FB.zip" in s3_log or "JAVA%20FB.zip" in s3_log:
                    self.log("SUCCESS: Downloaded correct JAVA FB project")
                
                if "200 OK" in s3_log:
                    self.log("S3 download SUCCESSFUL")
                elif "400 Bad Request" in s3_log or "ERROR 400" in s3_log:
                    self.log("ERROR: S3 download FAILED - Bad Request (URL expired?)")
                else:
                    self.log("S3 download status UNKNOWN")
            else:
                self.log("No S3 download found in logs")
            
            ssh.close()
            
        except Exception as e:
            self.log(f"ERROR monitoring S3 download: {e}")
    
    def monitor_project_extraction(self, public_ip):
        """Monitor project extraction"""
        self.log("STEP 7: Monitoring project extraction...")
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=public_ip, username='ubuntu', key_filename=self.key_file, timeout=10)
            
            # Check home directory first
            stdin, stdout, stderr = ssh.exec_command("ls -la /home/ubuntu/")
            home_contents = stdout.read().decode('utf-8', errors='ignore')
            
            self.log("HOME DIRECTORY CONTENTS:")
            self.log("-" * 40)
            for line in home_contents.split('\n'):
                if line.strip():
                    self.log(f"  {line}")
            self.log("-" * 40)
            
            # Check what zip file was downloaded
            stdin, stdout, stderr = ssh.exec_command("ls -la /home/ubuntu/*.zip 2>/dev/null")
            zip_files = stdout.read().decode('utf-8', errors='ignore')
            
            if zip_files:
                self.log("ZIP FILES FOUND:")
                for line in zip_files.split('\n'):
                    if line.strip():
                        self.log(f"  {line}")
            
            # Check if backend/frontend folders exist in extracted project
            stdin, stdout, stderr = ssh.exec_command("ls -la /home/ubuntu/backend/ /home/ubuntu/frontend/ 2>/dev/null")
            folders = stdout.read().decode('utf-8', errors='ignore')
            
            if folders:
                self.log("PROJECT FOLDERS FOUND:")
                for line in folders.split('\n'):
                    if line.strip():
                        self.log(f"  {line}")
            else:
                self.log("Backend/Frontend folders extracted to /home/ubuntu/ directly")
            
            ssh.close()
            
        except Exception as e:
            self.log(f"ERROR monitoring project extraction: {e}")
    
    def monitor_backend_deployment(self, public_ip):
        """Monitor backend deployment"""
        self.log("STEP 8: Monitoring backend deployment...")
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=public_ip, username='ubuntu', key_filename=self.key_file, timeout=10)
            
            # Check backend log
            stdin, stdout, stderr = ssh.exec_command("cat /var/log/backend.log 2>/dev/null")
            backend_log = stdout.read().decode('utf-8', errors='ignore')
            
            if backend_log:
                self.log("BACKEND LOG:")
                self.log("-" * 40)
                for line in backend_log.split('\n')[-20:]:  # Last 20 lines
                    if line.strip():
                        self.log(f"  {line}")
                self.log("-" * 40)
            else:
                self.log("No backend log found")
            
            # Check if uvicorn is running
            stdin, stdout, stderr = ssh.exec_command("ps aux | grep uvicorn | grep -v grep")
            uvicorn_process = stdout.read().decode('utf-8', errors='ignore')
            
            if uvicorn_process:
                self.log("UVICORN PROCESS RUNNING:")
                self.log(f"  {uvicorn_process.strip()}")
            else:
                self.log("ERROR: Uvicorn process NOT running")
            
            ssh.close()
            
        except Exception as e:
            self.log(f"ERROR monitoring backend: {e}")
    
    def monitor_frontend_deployment(self, public_ip):
        """Monitor frontend deployment"""
        self.log("STEP 9: Monitoring frontend deployment...")
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=public_ip, username='ubuntu', key_filename=self.key_file, timeout=10)
            
            # Check frontend log
            stdin, stdout, stderr = ssh.exec_command("cat /var/log/frontend.log 2>/dev/null")
            frontend_log = stdout.read().decode('utf-8', errors='ignore')
            
            if frontend_log:
                self.log("FRONTEND LOG:")
                self.log("-" * 40)
                for line in frontend_log.split('\n')[-20:]:  # Last 20 lines
                    if line.strip():
                        self.log(f"  {line}")
                self.log("-" * 40)
            else:
                self.log("No frontend log found")
            
            # Check if npm/node is running
            stdin, stdout, stderr = ssh.exec_command("ps aux | grep -E '(npm|node)' | grep -v grep")
            node_process = stdout.read().decode('utf-8', errors='ignore')
            
            if node_process:
                self.log("NODE/NPM PROCESS RUNNING:")
                for line in node_process.split('\n'):
                    if line.strip():
                        self.log(f"  {line}")
            else:
                self.log("ERROR: Node/NPM process NOT running")
            
            ssh.close()
            
        except Exception as e:
            self.log(f"ERROR monitoring frontend: {e}")
    
    def monitor_port_availability(self, public_ip):
        """Monitor port availability"""
        self.log("STEP 10: Monitoring port availability...")
        
        import socket
        
        ports_to_check = [22, 80, 3000, 8000]
        
        for port in ports_to_check:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((public_ip, port))
                sock.close()
                
                if result == 0:
                    self.log(f"Port {port}: OPEN")
                else:
                    self.log(f"Port {port}: CLOSED")
                    
            except Exception as e:
                self.log(f"Port {port}: ERROR - {e}")
    
    def generate_final_report(self, public_ip, instance_id):
        """Generate final deployment report"""
        self.log("STEP 11: Generating final report...")
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=public_ip, username='ubuntu', key_filename=self.key_file, timeout=10)
            
            # Get deployment log
            stdin, stdout, stderr = ssh.exec_command("cat /var/log/deployment.log")
            deployment_log = stdout.read().decode('utf-8', errors='ignore')
            
            self.log("FINAL DEPLOYMENT STATUS:")
            self.log("=" * 60)
            self.log(f"Instance ID: {instance_id}")
            self.log(f"Public IP: {public_ip}")
            self.log(f"Frontend URL: http://{public_ip}:3000")
            self.log(f"Backend URL: http://{public_ip}:8000")
            self.log(f"API Docs: http://{public_ip}:8000/docs")
            self.log("=" * 60)
            
            if deployment_log:
                self.log("DEPLOYMENT LOG:")
                for line in deployment_log.split('\n'):
                    if line.strip():
                        self.log(f"  {line}")
            
            ssh.close()
            
        except Exception as e:
            self.log(f"ERROR generating final report: {e}")

if __name__ == "__main__":
    monitor = DeploymentMonitor()
    monitor.monitor_deployment()