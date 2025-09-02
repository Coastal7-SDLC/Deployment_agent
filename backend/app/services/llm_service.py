import os
import json
import logging
import requests

class LLMService:
    def __init__(self):
        self.api_key = "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"
        self.model = "qwen/qwen-2.5-72b-instruct:free"
        self.base_url = "https://openrouter.ai/api/v1"
    
    def analyze_repository(self, local_dir: str) -> dict:
        """Analyze repository using README.md first, fallback to structure analysis."""
        try:
            logging.info(f"Analyzing project structure in: {local_dir}")
            
            # Step 1: Try to read README.md first
            readme_path = os.path.join(local_dir, "README.md")
            if os.path.exists(readme_path):
                logging.info(f"Found README.md - using structured analysis")
                return self._analyze_from_readme(readme_path)
            
            # Step 2: Fallback to structure analysis
            logging.info(f"No README.md found - using structure analysis")
            return self._analyze_from_structure(local_dir)
            
        except Exception as e:
            logging.error(f"LLM analysis failed: {str(e)}")
            return {"services": [{"technology": "python", "framework": "fastapi", "path": ".", "type": "backend"}]}
    
    def _analyze_from_readme(self, readme_path: str) -> dict:
        """Analyze project using README.md structure."""
        try:
            # Read README content
            with open(readme_path, 'r', encoding='utf-8') as f:
                readme_content = f.read()
            
            # Universal LLM prompt for ANY language/framework
            prompt = f"""You are a universal deployment expert. Analyze this project and detect ANY programming language and framework.

Project Content:
{readme_content}

UNIVERSAL LANGUAGE DETECTION:

BACKEND TECHNOLOGIES:
- Python: FastAPI, Django, Flask, Tornado, Pyramid
- Node.js: Express, NestJS, Koa, Hapi, Fastify
- Java: Spring Boot, Spring MVC, Quarkus, Micronaut
- C#: .NET Core, ASP.NET, Blazor Server
- Go: Gin, Echo, Fiber, Gorilla Mux, Chi
- PHP: Laravel, Symfony, CodeIgniter, Slim, CakePHP
- Ruby: Rails, Sinatra, Hanami, Grape
- Rust: Actix-web, Rocket, Warp, Axum
- C++: Crow, Drogon, Pistache
- Kotlin: Ktor, Spring Boot
- Scala: Play Framework, Akka HTTP
- Elixir: Phoenix
- Dart: Shelf, Angel

FRONTEND TECHNOLOGIES:
- React: Create React App, Next.js, Gatsby
- Vue.js: Vue CLI, Nuxt.js, Vite
- Angular: Angular CLI, Ionic
- Svelte: SvelteKit, Vite
- Static: HTML/CSS/JS, Jekyll, Hugo, Eleventy
- Mobile: Flutter Web, React Native Web
- Blazor: Blazor WebAssembly

PROJECT TYPE DETECTION:
- "frontend_only": Only frontend code (HTML/CSS/JS, React without backend, static sites)
- "backend_only": Only backend code (API, microservice, no frontend)
- "full_stack": Both frontend and backend components

COMMAND CONVERSION (Windows → Ubuntu):
- "python" → "python3"
- "pip" → "pip3"
- "py" → "python3"
- "dotnet" → "dotnet" (same)
- "go run" → "go run" (same)
- "cargo run" → "cargo run" (same)

PORT ASSIGNMENTS:
- Python: 8000, Node.js: 3000, Java: 8080, Go: 8080, PHP: 8000, Ruby: 3000
- C#: 5000, Rust: 8000, C++: 8080, Kotlin: 8080, Scala: 9000
- Frontend: React/Vue/Angular: 3000, Static: 8080

BUILD COMMANDS BY TECHNOLOGY:
- Python: ["pip3 install -r requirements.txt"] or ["poetry install"]
- Node.js: ["npm install"] or ["yarn install"]
- Java: ["mvn clean install"] or ["gradle build"]
- Go: ["go mod download", "go build"]
- PHP: ["composer install"]
- Ruby: ["bundle install"]
- Rust: ["cargo build --release"]
- C#: ["dotnet restore", "dotnet build"]
- Static: ["npm install", "npm run build"] if package.json exists

RUN COMMANDS BY TECHNOLOGY:
- Python FastAPI: "python3 -m uvicorn main:app --host 0.0.0.0 --port 8000"
- Python Django: "python3 manage.py runserver 0.0.0.0:8000"
- Python Flask: "python3 app.py" or "flask run --host=0.0.0.0 --port=8000"
- Node.js: "npm start" or "node server.js" or "node index.js"
- Java Spring: "java -jar target/*.jar"
- Go: "./main" or "go run main.go"
- PHP: "php -S 0.0.0.0:8000" or "php artisan serve --host=0.0.0.0 --port=8000"
- Ruby Rails: "rails server -b 0.0.0.0 -p 3000"
- Rust: "./target/release/app"
- C#: "dotnet run --urls=http://0.0.0.0:5000"
- Static: "python3 -m http.server 8080" or "npx serve -s build -l 8080"

FRONTEND RUN COMMANDS:
- React: "npm start" or "serve -s build"
- Vue: "npm run serve" or "npm run dev"
- Angular: "ng serve --host 0.0.0.0"
- Static: "python3 -m http.server 3000"

Analyze the project and return JSON:
{{
  "project_type": "frontend_only" | "backend_only" | "full_stack",
  "backend_technology": "detected_language",
  "frontend_technology": "detected_framework" | null,
  "backend_port": "port_number",
  "frontend_port": "port_number" | null,
  "backend_build_commands": ["command1", "command2"],
  "frontend_build_commands": ["command1", "command2"] | null,
  "backend_run_command": "run_command",
  "frontend_run_command": "run_command" | null
}}

IMPORTANT: 
- Detect ANY programming language, not just common ones
- If only frontend exists, set backend_technology to null
- If only backend exists, set frontend_technology to null
- Convert ALL commands to Ubuntu Linux format
- Return ONLY JSON, no explanations"""
            
            # Send to LLM
            response = self._send_llm_request(prompt)
            
            if "error" in response:
                raise Exception(f"LLM analysis failed: {response['error']}")
            
            # Debug LLM response
            llm_content = response.get("content", "")
            logging.info(f"LLM Raw Response: {llm_content[:300]}...")  # First 300 chars
            logging.info(f"Auto-converting Windows commands to Ubuntu Linux")
            
            # Parse LLM response
            try:
                if not llm_content or llm_content.strip() == "":
                    raise Exception("LLM returned empty response")
                
                # Try to extract JSON from response (LLM might add extra text)
                json_start = llm_content.find('{')
                json_end = llm_content.rfind('}') + 1
                
                if json_start == -1 or json_end == 0:
                    raise Exception(f"No JSON found in LLM response: {llm_content}")
                
                json_content = llm_content[json_start:json_end]
                deployment_config = json.loads(json_content)
                
                logging.info(f"Parsed deployment config: {deployment_config}")
                
                # Convert to services format for compatibility
                services = []
                
                # Add backend service
                if deployment_config.get("backend_technology") and deployment_config.get("backend_technology") != "null":
                    services.append({
                        "type": "backend",
                        "technology": deployment_config.get("backend_technology", "python"),
                        "framework": "from_readme",
                        "path": "backend" if deployment_config.get("project_type") == "full_stack" else ".",
                        "port": deployment_config.get("backend_port", "8000"),
                        "run_command": self._convert_to_linux_command(deployment_config.get("backend_run_command", "python3 main.py"))
                    })
                
                # Add frontend service if exists
                if deployment_config.get("frontend_technology") and deployment_config.get("frontend_technology") != "null":
                    services.append({
                        "type": "frontend",
                        "technology": deployment_config.get("frontend_technology", "react"),
                        "framework": "from_readme",
                        "path": "frontend",
                        "port": deployment_config.get("frontend_port", "3000")
                    })
                    logging.info(f"Frontend detected: {deployment_config.get('frontend_technology')}")
                elif deployment_config.get("project_type") == "frontend_only":
                    # Frontend-only project
                    services.append({
                        "type": "frontend",
                        "technology": deployment_config.get("frontend_technology", "static"),
                        "framework": "from_readme",
                        "path": ".",
                        "port": deployment_config.get("frontend_port", "8080")
                    })
                    logging.info(f"Frontend-only project detected: {deployment_config.get('frontend_technology')}")
                
                return {
                    "services": services,
                    "deployment_strategy": "readme_based",
                    "readme_config": {
                        "deployment_commands": {
                            "backend": {
                                "build_commands": self._convert_commands_to_linux(deployment_config.get("backend_build_commands", ["cd backend", "pip3 install -r requirements.txt"])),
                                "run_command": self._convert_to_linux_command(deployment_config.get("backend_run_command", "python3 -m uvicorn main:app --host 0.0.0.0 --port 8000")),
                                "port": deployment_config.get("backend_port", "8000")
                            } if deployment_config.get("backend_technology") and deployment_config.get("backend_technology") != "null" else None,
                            "frontend": {
                                "build_commands": self._convert_commands_to_linux(deployment_config.get("frontend_build_commands", ["cd frontend", "npm install", "npm run build"])),
                                "run_command": self._convert_to_linux_command(deployment_config.get("frontend_run_command", "npm start")),
                                "port": deployment_config.get("frontend_port", "3000")
                            } if deployment_config.get("frontend_technology") and deployment_config.get("frontend_technology") != "null" else None
                        }
                    }
                }
                
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse LLM JSON response: {str(e)}")
                logging.error(f"Raw LLM response: {llm_content}")
                raise Exception(f"LLM returned invalid JSON: {str(e)}")
            except Exception as e:
                logging.error(f"JSON processing error: {str(e)}")
                raise
            
        except Exception as e:
            logging.error(f"README analysis failed: {str(e)}")
            # Fallback to structure analysis
            return self._analyze_from_structure(os.path.dirname(readme_path))
    
    def _analyze_from_structure(self, local_dir: str) -> dict:
        """Fallback: Analyze project structure when no README.md."""
        services = []
        
        # Check for backend folder
        backend_dir = os.path.join(local_dir, "backend")
        if os.path.exists(backend_dir):
            logging.info(f"Found backend folder")
            if os.path.exists(os.path.join(backend_dir, "requirements.txt")):
                services.append({
                    "technology": "python", 
                    "framework": "fastapi",
                    "path": "backend",
                    "type": "backend"
                })
            elif os.path.exists(os.path.join(backend_dir, "package.json")):
                services.append({
                    "technology": "node", 
                    "framework": "express",
                    "path": "backend",
                    "type": "backend"
                })
        
        # Check for frontend folder
        frontend_dir = os.path.join(local_dir, "frontend")
        if os.path.exists(frontend_dir):
            logging.info(f"Found frontend folder")
            if os.path.exists(os.path.join(frontend_dir, "package.json")):
                services.append({
                    "technology": "react", 
                    "framework": "react",
                    "path": "frontend",
                    "type": "frontend"
                })
        
        # Check root directory if no backend/frontend folders
        if not services:
            if os.path.exists(os.path.join(local_dir, "requirements.txt")):
                services.append({"technology": "python", "framework": "fastapi", "path": ".", "type": "backend"})
            elif os.path.exists(os.path.join(local_dir, "package.json")):
                services.append({"technology": "node", "framework": "express", "path": ".", "type": "backend"})
            else:
                services.append({"technology": "python", "framework": "fastapi", "path": ".", "type": "backend"})
        
        logging.info(f"Analysis complete - Found {len(services)} services")
        return {"services": services}
    
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
        
        # Fix path separators
        linux_command = linux_command.replace('\\', '/')
        
        # Fix drive letters (C: -> /)
        import re
        linux_command = re.sub(r'[A-Za-z]:', '', linux_command)
        
        return linux_command
    
    def _convert_commands_to_linux(self, commands: list) -> list:
        """Convert list of Windows commands to Linux equivalents."""
        if not commands:
            return commands
        
        return [self._convert_to_linux_command(cmd) for cmd in commands]
    
    def _send_llm_request(self, prompt: str) -> dict:
        """Send request to LLM API."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {"content": result["choices"][0]["message"]["content"]}
            else:
                return {"error": f"API request failed: {response.status_code}"}
                
        except Exception as e:
            return {"error": str(e)}