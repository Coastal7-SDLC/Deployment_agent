# Coastal Seven Universal Deployment Agent

AI-powered deployment agent that can deploy GitHub repositories of any programming language and framework using LLM analysis.

## Project Structure

```
AGENT-SDLC/
├── backend/
│   ├── routers/
│   │   ├── __init__.py
│   │   └── deployment.py        # Deployment endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── deployment_service.py # Main deployment logic
│   │   ├── health_service.py     # Health checking
│   │   └── llm_service.py        # LLM analysis service
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── git_utils.py          # Git operations
│   │   ├── universal_deployment.py # Universal deployment
│   │   └── frontend_utils.py     # Frontend utilities
│   ├── deployments/              # Deployed repositories
│   ├── config.py                 # Configuration
│   ├── main.py                   # FastAPI app entry point
│   ├── requirements.txt          # Python dependencies
│   └── .env                     # Environment variables
└── README.md
```

## Supported Technologies

### Backend:
- **Python**: FastAPI, Django, Flask
- **Java**: Spring Boot, Maven projects
- **Node.js**: Express, NestJS
- **C#**: .NET Core, ASP.NET
- **Go**: Gin, Echo
- **PHP**: Laravel, Symfony
- **Ruby**: Rails, Sinatra

### Frontend:
- **React**: Create React App, Next.js
- **Vue**: Vue CLI, Nuxt.js
- **Angular**: Angular CLI
- **Svelte**: SvelteKit
- **Flutter**: Flutter Web/Mobile

## Quick Start

1. **Install dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   # OpenRouter API key is already configured in the code
   # No additional setup required
   ```

3. **Run the server:**
   ```bash
   python main.py
   ```

4. **Access the API:**
   - API Documentation: http://127.0.0.1:8000/docs
   - Deploy endpoint: `POST /api/deploy`
   - Status endpoint: `GET /api/status/{repo_name}`

## API Endpoints

### Deployment
- `POST /api/deploy` - Deploy any GitHub repository
- `GET /api/status/{repo_name}` - Check deployment status



## Usage Examples

### Deploy Python FastAPI + React:
```bash
curl -X POST "http://127.0.0.1:8000/api/deploy" \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/user/python-react-app.git"}'
```

### Deploy Java Spring Boot:
```bash
curl -X POST "http://127.0.0.1:8000/api/deploy" \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/user/spring-boot-app.git"}'
```

### Deploy Node.js + Vue:
```bash
curl -X POST "http://127.0.0.1:8000/api/deploy" \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/user/nodejs-vue-app.git"}'
```

## Response Examples

### Full-Stack Deployment:
```json
{
  "message": "Deployment successful",
  "repo_name": "my-app",
  "backend_url": "http://127.0.0.1:8080",
  "frontend_url": "http://127.0.0.1:3000",
  "backend_technology": "java (spring)",
  "frontend_technology": "react",
  "note": "Both java backend and react frontend are running"
}
```

### Backend-Only Deployment:
```json
{
  "message": "Deployment successful",
  "repo_name": "api-server",
  "backend_url": "http://127.0.0.1:8080",
  "backend_technology": "java (spring)",
  "note": "Only java backend is running",
  "warning": "Frontend not found in repository"
}
```

## Features

- ✅ **Universal Language Support** - Python, Java, Node.js, C#, Go, PHP, Ruby
- ✅ **AI-Powered Analysis** - LLM analyzes repository structure
- ✅ **Smart Command Generation** - Automatic build/run commands
- ✅ **Automatic Port Management** - No port conflicts
- ✅ **API URL Synchronization** - Frontend connects to backend automatically
- ✅ **Health Checks** - Monitor deployment status
- ✅ **Pure LLM Analysis** - 100% AI-powered deployment decisions
- ✅ **Technology Detection** - Identifies frameworks and versions

## How It Works

1. **Repository Analysis**: LLM analyzes the cloned repository structure
2. **Technology Detection**: Identifies programming languages and frameworks
3. **Command Generation**: Creates appropriate build and run commands
4. **Universal Deployment**: Executes deployment regardless of technology
5. **Health Monitoring**: Checks if services are running properly

## Configuration

### OpenRouter + Qwen Model:
- Full LLM-powered analysis
- Supports any programming language
- Smart command generation
- No manual fallback required

### LLM-Only Architecture:
- Pure AI-powered analysis
- No manual fallback patterns
- Supports any programming language through AI

## Error Handling

The system gracefully handles:
- Unknown technologies (with LLM analysis)
- Build failures (with detailed error messages)
- Port conflicts (automatic port assignment)
- Missing dependencies (clear error reporting)