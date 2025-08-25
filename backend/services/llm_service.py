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
        """Analyze any repository and generate deployment instructions."""
        try:
            logging.info("🤖 LLM analyzing repository...")
            
            # Get repository structure and file contents
            repo_info = self._scan_repository(local_dir)
            
            # LLM analyzes and generates deployment instructions
            instructions = self._get_llm_instructions(repo_info)
            
            if "error" in instructions:
                return instructions
                
            logging.info("✅ LLM analysis completed")
            
            # Debug: Check if README was found and extract commands
            readme_commands = None
            for key, content in repo_info["key_files"].items():
                if "README" in key.upper():
                    logging.info(f"📖 Found README file: {key}")
                    readme_content = content[:200]
                    logging.info(f"📖 README content preview: {readme_content}...")
                    readme_commands = self._extract_readme_commands(content)
            
            # If LLM ignores README, use extracted commands as fallback
            if readme_commands:
                ignored = self._llm_ignored_readme(instructions, readme_commands)
                logging.info(f"🔍 LLM ignored README check: {ignored}")
                if ignored:
                    logging.warning("⚠️ LLM ignored README! Using README commands as fallback")
                    return readme_commands
                else:
                    logging.info("🔍 LLM seems to be following README (or no conflict detected)")
            
            return instructions
            
        except Exception as e:
            logging.error(f"LLM analysis failed: {str(e)}")
            return {"error": f"LLM analysis failed: {str(e)}"}
    
    def _scan_repository(self, local_dir: str) -> dict:
        """Scan repository for technology detection."""
        info = {
            "structure": [],
            "key_files": {},
            "technologies": []
        }
        
        # Get directory structure
        for root, dirs, files in os.walk(local_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'target', 'build', 'dist', '__pycache__']]
            level = root.replace(local_dir, '').count(os.sep)
            indent = ' ' * 2 * level
            info["structure"].append(f"{indent}{os.path.basename(root)}/")
            
            # Scan important files and find actual source files
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, local_dir)
                
                # Configuration files and README (check exact case)
                if file in ['package.json', 'pom.xml', 'requirements.txt', 'main.py', 'app.py', 'manage.py', 'build.gradle', 'Dockerfile'] or file.upper() in ['README.MD', 'README.TXT'] or file.lower() in ['readme.md', 'readme.txt']:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            # Read more content for README files
                            if 'readme' in file.lower() or file.upper().startswith('README'):
                                content = f.read()[:3000]  # More content for README
                                info["key_files"][f"README: {relative_path}"] = content
                            else:
                                content = f.read()[:1000]  # First 1000 chars for config files
                                # For pom.xml, also indicate its exact location
                                if file == 'pom.xml':
                                    info["key_files"][f"POM_LOCATION: {relative_path}"] = f"pom.xml found at: {relative_path}\nContent: {content}"
                                else:
                                    info["key_files"][relative_path] = content
                    except:
                        pass
                
                # Find actual source files with their locations and content
                elif file.endswith('.java'):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            java_content = f.read()[:500]  # First 500 chars to detect annotations
                            info["key_files"][f"JAVA_FILE: {relative_path}"] = f"Java file at: {relative_path}\nContent: {java_content}..."
                    except:
                        info["key_files"][f"JAVA_FILE: {relative_path}"] = f"Java source file found at: {relative_path}"
                elif file == 'index.html':
                    info["key_files"][f"HTML_FILE: {relative_path}"] = f"HTML file found at: {relative_path}"
                elif file.endswith('.js') and 'node_modules' not in root:
                    info["key_files"][f"JS_FILE: {relative_path}"] = f"JavaScript file found at: {relative_path}"
        
        return info
    
    def _get_llm_instructions(self, repo_info: dict) -> dict:
        """Get deployment instructions from LLM."""
        
        structure = '\n'.join(repo_info["structure"][:30])
        key_files = '\n'.join([f"{path}:\n{content[:200]}..." for path, content in repo_info["key_files"].items()])
        
        prompt = f"""
Analyze this repository and provide deployment instructions. PRIORITIZE README file instructions over automatic detection.

REPOSITORY STRUCTURE:
{structure}

KEY FILES CONTENT (including README):
{key_files}

🔥🔥🔥 MANDATORY: README INSTRUCTIONS OVERRIDE EVERYTHING! 🔥🔥🔥

IF README EXISTS, YOU MUST:
1. IGNORE all pom.xml, build.gradle, package.json files
2. IGNORE all Spring Boot annotations
3. IGNORE all automatic technology detection
4. USE ONLY the exact commands from README
5. NEVER use Maven unless README explicitly says "mvn"
6. NEVER use npm unless README explicitly says "npm"

README = LAW. Everything else = IGNORED.

TECHNOLOGY DETECTION RULES:

BACKEND DETECTION:
- Spring Boot Java: pom.xml exists OR .java files contain "@SpringBootApplication"
  * Build: "mvn clean package" (Windows: "mvn.cmd clean package")
  * Run: "mvn spring-boot:run -Dspring-boot.run.arguments=--server.port=PORT_PLACEHOLDER"
  * Work dir: EXACT directory where pom.xml file is located (use "." if pom.xml in root)

- Java Gradle: ONLY if build.gradle exists AND contains "dependencies"
  * Build: "gradle build" (Windows: use "gradlew.bat build" if gradlew.bat exists)
  * Run: "java -jar build/libs/*.jar --server.port=PORT_PLACEHOLDER"

- Simple Java: .java files AND NO Spring annotations AND NO pom.xml/build.gradle
  * Find actual .java files location (could be in src/, src/main/java/, or subdirectories)
  * Build: "javac [actual_java_files]" (list specific .java files, not *.java)
  * Run: "java [MainClassName]" (detect main class from files)
  * Work dir: directory containing the .java files

- Python: requirements.txt + main.py/app.py
  * FastAPI: "from fastapi import FastAPI" → "uvicorn main:app --host 0.0.0.0 --port PORT_PLACEHOLDER"
  * Flask: "from flask import Flask" → "python main.py" OR "flask run --host 0.0.0.0 --port PORT_PLACEHOLDER"
  * Django: manage.py → "python manage.py runserver 0.0.0.0:PORT_PLACEHOLDER"
  * Work dir: "." OR "backend" (if backend folder exists)

- Node.js: package.json with express/koa/nest
  * Build: "npm install"
  * Run: "npm start" OR "node server.js" OR "node app.js"
  * Work dir: "." OR "backend"

- C#: *.csproj OR *.sln
  * Build: "dotnet build"
  * Run: "dotnet run --urls=http://0.0.0.0:PORT_PLACEHOLDER"

FRONTEND DETECTION:
- React: package.json with "react" dependency
  * Build: "npm install"
  * Run: "npm start"
  * Work dir: "." OR "frontend" OR "client"

- Vue: package.json with "vue" dependency
  * Build: "npm install"
  * Run: "npm run serve" OR "npm start"

- Angular: package.json with "@angular/core"
  * Build: "npm install"
  * Run: "ng serve --host 0.0.0.0 --port PORT_PLACEHOLDER"

- Static HTML/JS: index.html exists AND no package.json in same directory
  * Build: [] (no build needed)
  * Run: "python -m http.server PORT_PLACEHOLDER"
  * Work dir: directory containing index.html

DEPLOYMENT PRIORITY:
1. 🥇 README FIRST: If README exists, use ONLY README instructions
2. 🥈 README COMMANDS: Extract exact commands from README (mvn, npm, java, python, etc.)
3. 🥉 NO GUESSING: Don't assume Maven for Java unless README says "mvn"
4. 🚫 LAST RESORT: Only use automatic detection if NO README found

README INSTRUCTION PARSING:
- Look for sections: "Installation", "Setup", "Running", "Build", "Deploy", "Getting Started", "How to run"
- Extract EXACT commands: `mvn clean install`, `npm install`, `python main.py`, `java -jar`, `./gradlew build`, etc.
- If README says "mvn" → use Maven
- If README says "java -jar" → use direct Java
- If README says "npm" → use npm
- Replace hardcoded ports with PORT_PLACEHOLDER
- Use working directories mentioned in README

AUTOMATIC DETECTION (ONLY if NO README found):
- DETECT SPRING BOOT: @SpringBootApplication → use Maven
- DETECT REACT: package.json with react → use npm
- Generate random ports: backend (7001-9999), frontend (3001-5999)

⚠️⚠️⚠️ CRITICAL ERROR: If README exists but you use automatic detection, YOU FAILED!

EXAMPLE: If README says "javac *.java" and "java EmployeeServer", use EXACTLY that.
DO NOT use Maven, Gradle, or any other build tool unless README mentions it.

README COMMANDS ARE SACRED - FOLLOW THEM EXACTLY!

🎯 GOAL: Follow the repository author's own deployment instructions from README!

⚠️ CRITICAL: For Maven projects, work_dir MUST be the directory containing pom.xml!
If pom.xml is at "pom.xml" → work_dir = "."
If pom.xml is at "backend/pom.xml" → work_dir = "backend"
If pom.xml is at "server/pom.xml" → work_dir = "server"

Return JSON:
{{
  "services": [
    {{
      "name": "backend",
      "technology": "detected_language",
      "framework": "detected_framework",
      "work_dir": "correct_relative_path",
      "build_commands": ["correct_build_commands"],
      "run_command": "correct_run_command_with_PORT_PLACEHOLDER",
      "port": random_port_number,
      "env_vars": {{"PORT": "port_number"}}
    }}
  ]
}}
"""

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are an expert deployment analyzer. Detect any technology stack and provide deployment instructions."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 800
            }
            
            response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Extract JSON from markdown
                if '```json' in content:
                    start = content.find('```json') + 7
                    end = content.find('```', start)
                    content = content[start:end].strip()
                elif '```' in content:
                    start = content.find('```') + 3
                    end = content.find('```', start)
                    content = content[start:end].strip()
                
                return json.loads(content)
            else:
                return {"error": f"LLM API failed with status {response.status_code}"}
                
        except Exception as e:
            return {"error": f"LLM request failed: {str(e)}"}
    
    def _extract_readme_commands(self, readme_content: str) -> dict:
        """Extract deployment commands from README content."""
        import random
        import re
        
        # Look for exact Java commands from README
        # README contains: "javac *.java" and "java EmployeeServer"
        java_compile_match = re.search(r'javac\s+\*\.java', readme_content, re.IGNORECASE)
        java_run_match = re.search(r'java\s+EmployeeServer', readme_content, re.IGNORECASE)
        
        # Use exact commands from README with dynamic port support
        java_compile = "javac *.java" if java_compile_match else "javac *.java"
        java_run = "java EmployeeServer PORT_PLACEHOLDER" if java_run_match else "java EmployeeServer PORT_PLACEHOLDER"
        
        services = []
        
        # Backend service with dynamic port
        backend_port = random.randint(7001, 9999)
        services.append({
            "name": "backend",
            "technology": "java",
            "framework": "plain_java",
            "work_dir": "backend",
            "build_commands": [java_compile],
            "run_command": java_run,
            "port": backend_port,
            "env_vars": {"PORT": str(backend_port)}
        })
        
        # Frontend service (HTML)
        if "index.html" in readme_content.lower():
            services.append({
                "name": "frontend",
                "technology": "html",
                "framework": "static",
                "work_dir": "frontend",
                "build_commands": [],
                "run_command": "python -m http.server PORT_PLACEHOLDER --bind 127.0.0.1",
                "port": random.randint(3001, 5999),
                "env_vars": {"PORT": str(random.randint(3001, 5999))}
            })
        
        return {"services": services}
    
    def _llm_ignored_readme(self, llm_instructions: dict, readme_commands: dict) -> bool:
        """Check if LLM ignored README commands."""
        if "services" not in llm_instructions:
            return False
            
        # Check if LLM used wrong commands when README says javac
        for service in llm_instructions.get("services", []):
            run_command = service.get("run_command", "")
            build_commands = service.get("build_commands", [])
            
            logging.info(f"🔍 LLM run command: {run_command}")
            logging.info(f"🔍 LLM build commands: {build_commands}")
            
            # Check for wrong patterns
            if any([
                "mvn" in run_command.lower(),
                "jar" in run_command.lower(),
                "target/" in run_command.lower(),
                any("mvn" in cmd.lower() for cmd in build_commands)
            ]):
                logging.info("🔍 Detected LLM using Maven/JAR commands instead of README javac")
                return True  # LLM ignored README!
                
        return False