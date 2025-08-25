import subprocess
import threading
import os
import logging
import time
import random

class UniversalDeployment:
    @staticmethod
    def execute_deployment(local_dir: str, instructions: dict) -> dict:
        """Execute LLM deployment instructions for any technology."""
        try:
            services = instructions.get("services", [])
            if not services:
                return {"error": "No services found in LLM instructions"}
            
            deployed_services = []
            
            for service in services:
                result = UniversalDeployment._deploy_service(local_dir, service)
                deployed_services.append(result)
            
            return {
                "deployment_results": {
                    service["name"]: {
                        "technology": service.get("technology", "unknown"),
                        "framework": service.get("framework", "unknown"),
                        "status": "success",
                        "port": service.get("port"),
                        "url": f"http://127.0.0.1:{service.get('port')}",
                        "details": f"{service.get('technology')} service deployed successfully"
                    } for service in services
                }
            }
            
        except Exception as e:
            logging.error(f"Deployment execution failed: {str(e)}")
            return {"error": f"Deployment execution failed: {str(e)}"}
    
    @staticmethod
    def _deploy_service(local_dir: str, service: dict) -> dict:
        """Deploy a single service based on LLM instructions."""
        try:
            name = service.get("name", "service")
            work_dir_relative = service.get("work_dir", "")
            work_dir = os.path.join(local_dir, work_dir_relative) if work_dir_relative else local_dir
            
            # Ensure work_dir exists and is valid
            if not os.path.exists(work_dir):
                logging.error(f"Work directory does not exist: {work_dir}")
                work_dir = local_dir  # Fallback to repo root
            
            logging.info(f"Using work directory: {work_dir}")
            
            build_commands = service.get("build_commands", [])
            run_command = service.get("run_command", "")
            port = service.get("port", random.randint(7000, 9999))
            env_vars = service.get("env_vars", {})
            
            # Replace PORT_PLACEHOLDER with actual port
            run_command = run_command.replace("PORT_PLACEHOLDER", str(port))
            
            def deploy_process():
                try:
                    # Validate working directory
                    if not os.path.exists(work_dir):
                        logging.error(f"Invalid work directory: {work_dir}")
                        return
                    
                    logging.info(f"Working in directory: {os.path.abspath(work_dir)}")
                    
                    # Execute build commands
                    for build_cmd in build_commands:
                        logging.info(f"Building {name}: {build_cmd}")
                        result = subprocess.run(
                            build_cmd,
                            shell=True,
                            cwd=work_dir,
                            capture_output=True,
                            text=True,
                            timeout=300  # 5 minute timeout
                        )
                        if result.returncode != 0:
                            logging.error(f"Build failed for {name}: {result.stderr}")
                            logging.error(f"Build stdout: {result.stdout}")
                            return
                    
                    # Set environment variables
                    env = os.environ.copy()
                    env.update(env_vars)
                    env["PORT"] = str(port)
                    
                    # Execute run command
                    if not os.path.exists(work_dir):
                        logging.error(f"Invalid work directory for run: {work_dir}")
                        return
                    
                    logging.info(f"Starting {name}: {run_command} in {os.path.abspath(work_dir)}")
                    subprocess.run(
                        run_command,
                        shell=True,
                        cwd=work_dir,
                        env=env
                    )
                    
                except subprocess.TimeoutExpired:
                    logging.error(f"Build timeout for {name}")
                except Exception as e:
                    logging.error(f"Failed to deploy {name}: {str(e)}")
            
            # Start service in background thread
            thread = threading.Thread(target=deploy_process, daemon=True)
            thread.start()
            
            # Wait a moment for service to start
            time.sleep(2)
            
            return {
                "name": name,
                "port": port,
                "status": "deployed"
            }
            
        except Exception as e:
            logging.error(f"Service deployment failed: {str(e)}")
            return {"name": name, "status": "failed", "error": str(e)}
    
    @staticmethod
    def update_frontend_api_urls(local_dir: str, deployment_result: dict) -> bool:
        """Update frontend API URLs to connect with backend."""
        try:
            # Get backend port from deployment results
            backend_port = None
            deployment_results = deployment_result.get("deployment_results", {})
            
            for service_name, service_info in deployment_results.items():
                if "backend" in service_name.lower() or service_info.get("technology") in ["python", "java", "csharp", "go"]:
                    backend_port = service_info.get("port")
                    break
            
            if not backend_port:
                return False
            
            # Update frontend API files
            api_files = [
                "frontend/src/services/api.js",
                "frontend/src/api/config.js", 
                "frontend/src/config/api.js",
                "frontend/src/utils/api.js",
                "src/services/api.js",
                "src/api/config.js"
            ]
            
            updated = False
            for api_file in api_files:
                file_path = os.path.join(local_dir, api_file)
                if os.path.exists(file_path):
                    if UniversalDeployment._update_api_file(file_path, backend_port):
                        updated = True
                        logging.info(f"Updated API URLs in {api_file}")
            
            return updated
            
        except Exception as e:
            logging.error(f"Failed to update API URLs: {str(e)}")
            return False
    
    @staticmethod
    def _update_api_file(file_path: str, backend_port: int) -> bool:
        """Update API URLs in a specific file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Update various URL patterns
            import re
            patterns = [
                (r'const\s+API_BASE_URL\s*=\s*["\']http://localhost:\d+["\']', f'const API_BASE_URL = "http://localhost:{backend_port}"'),
                (r'const\s+API_URL\s*=\s*["\']http://localhost:\d+["\']', f'const API_URL = "http://localhost:{backend_port}"'),
                (r'"baseURL":\s*"http://localhost:\d+"', f'"baseURL": "http://localhost:{backend_port}"'),
                (r'baseURL:\s*"http://localhost:\d+"', f'baseURL: "http://localhost:{backend_port}"'),
                (r'http://localhost:\d+', f'http://localhost:{backend_port}')
            ]
            
            for pattern, replacement in patterns:
                content = re.sub(pattern, replacement, content)
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"Failed to update file {file_path}: {str(e)}")
            return False
    
    @staticmethod
    def update_java_server_port(local_dir: str, deployment_result: dict) -> bool:
        """Update Java server to use dynamic port instead of hardcoded 8080."""
        try:
            # Find backend port
            backend_port = None
            deployment_results = deployment_result.get("deployment_results", {})
            
            for service_name, service_info in deployment_results.items():
                if "backend" in service_name.lower() and service_info.get("technology") == "java":
                    backend_port = service_info.get("port")
                    break
            
            if not backend_port:
                return False
            
            # Update EmployeeServer.java to use dynamic port
            java_file = os.path.join(local_dir, "backend", "EmployeeServer.java")
            if os.path.exists(java_file):
                with open(java_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Replace hardcoded port with dynamic port logic
                old_main = '''    public static void main(String[] args) throws IOException {
        // Add some test data
        employees.add(new Employee(nextId++, "John Doe", "Developer", 50000, "IT"));
        employees.add(new Employee(nextId++, "Jane Smith", "Manager", 60000, "HR"));
        
        HttpServer server = HttpServer.create(new InetSocketAddress(8080), 0);'''
                
                new_main = '''    public static void main(String[] args) throws IOException {
        // Add some test data
        employees.add(new Employee(nextId++, "John Doe", "Developer", 50000, "IT"));
        employees.add(new Employee(nextId++, "Jane Smith", "Manager", 60000, "HR"));
        
        // Use dynamic port from command line argument or default to 8080
        int port = 8080;
        if (args.length > 0) {
            try {
                port = Integer.parseInt(args[0]);
            } catch (NumberFormatException e) {
                System.out.println("Invalid port number, using default 8080");
            }
        }
        
        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);'''
                
                # Replace hardcoded print statements
                content = content.replace(old_main, new_main)
                content = content.replace('System.out.println("Server started on http://localhost:8080");', 
                                        'System.out.println("Server started on http://localhost:" + port);')
                content = content.replace('System.out.println("Test: http://localhost:8080/api/employees");', 
                                        'System.out.println("Test: http://localhost:" + port + "/api/employees");')
                
                with open(java_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logging.info(f"Updated Java server to use dynamic port {backend_port}")
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"Failed to update Java server port: {str(e)}")
            return False
    
    @staticmethod
    def update_java_server_port_before_deployment(local_dir: str, instructions: dict) -> bool:
        """Update Java server to use dynamic port BEFORE compilation starts."""
        try:
            # Find Java backend service
            services = instructions.get("services", [])
            java_service = None
            
            for service in services:
                if service.get("technology") == "java" and "backend" in service.get("name", "").lower():
                    java_service = service
                    break
            
            if not java_service:
                return False
            
            backend_port = java_service.get("port")
            if not backend_port:
                return False
            
            # Update EmployeeServer.java to use dynamic port
            java_file = os.path.join(local_dir, "backend", "EmployeeServer.java")
            if os.path.exists(java_file):
                with open(java_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Replace hardcoded port with dynamic port logic
                old_main = '''    public static void main(String[] args) throws IOException {
        // Add some test data
        employees.add(new Employee(nextId++, "John Doe", "Developer", 50000, "IT"));
        employees.add(new Employee(nextId++, "Jane Smith", "Manager", 60000, "HR"));
        
        HttpServer server = HttpServer.create(new InetSocketAddress(8080), 0);'''
                
                new_main = '''    public static void main(String[] args) throws IOException {
        // Add some test data
        employees.add(new Employee(nextId++, "John Doe", "Developer", 50000, "IT"));
        employees.add(new Employee(nextId++, "Jane Smith", "Manager", 60000, "HR"));
        
        // Use dynamic port from command line argument or default to 8080
        int port = 8080;
        if (args.length > 0) {
            try {
                port = Integer.parseInt(args[0]);
            } catch (NumberFormatException e) {
                System.out.println("Invalid port number, using default 8080");
            }
        }
        
        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);'''
                
                # Replace hardcoded print statements
                content = content.replace(old_main, new_main)
                content = content.replace('System.out.println("Server started on http://localhost:8080");', 
                                        'System.out.println("Server started on http://localhost:" + port);')
                content = content.replace('System.out.println("Test: http://localhost:8080/api/employees");', 
                                        'System.out.println("Test: http://localhost:" + port + "/api/employees");')
                
                with open(java_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logging.info(f"✅ Modified Java server to use dynamic port {backend_port} BEFORE compilation")
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"Failed to update Java server port before deployment: {str(e)}")
            return False