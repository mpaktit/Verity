# Installation Guide

This guide will help you set up Verity on your local machine or server.

## System Requirements

- **Python**: 3.12 or higher
- **Operating System**: Windows, Linux, or macOS
- **Memory**: Minimum 2GB RAM (4GB+ recommended)
- **Disk Space**: 500MB for installation, plus space for database growth
- **Network**: Internet connection for web scraping and AI API calls

## Step-by-Step Installation

### 1. Clone the Repository

```bash
git clone https://github.com/mpaktit/Verity.git
cd Verity
```

### 2. Create a Virtual Environment

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright Browsers

```bash
playwright install chromium
```

This downloads the Chromium browser used for automation (approximately 300MB).

### 5. Initialize the Database

```bash
python -c "from app.db import init_db; init_db()"
```

This creates the SQLite database at `data/verity.db` and runs all migrations.

### 6. Configure Environment Variables (Optional)

Create a `.env` file in the project root:

```bash
# Database
DATABASE_URL=sqlite:///./data/verity.db

# CORS Origins (comma-separated list)
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000

# Enable background scheduler
VERITY_ENABLE_SCHEDULER=true

# Crawl interval in seconds (default: 3600 = 1 hour)
CRAWL_INTERVAL_SECONDS=3600

# Application version
APP_VERSION=0.2.0
```

### 7. Run the Application

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The `--reload` flag enables auto-reloading during development. Remove it for production.

### 8. Access the Application

Open your browser to:
- **Dashboard**: http://localhost:8000/
- **API Health**: http://localhost:8000/api/health
- **API Documentation**: http://localhost:8000/docs

## Setting Up AI Providers

To use the agent system, you need to add API keys for at least one AI provider.

### Option 1: Via Dashboard UI

1. Sign up for an account at http://localhost:8000/
2. Login to your account
3. Navigate to the "Agents" tab
4. Click "Add API Key"
5. Enter your provider, key name, and API key

### Option 2: Via API

```bash
# Sign up
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"name": "Your Name", "email": "you@example.com", "password": "securepassword"}'

# Login (save the token)
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "securepassword"}'

# Add Anthropic API key
curl -X POST http://localhost:8000/api/ai/keys \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"provider": "anthropic", "key_name": "Claude Key", "api_key": "sk-ant-..."}'

# Add OpenAI API key
curl -X POST http://localhost:8000/api/ai/keys \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"provider": "openai", "key_name": "GPT Key", "api_key": "sk-..."}'

# Add Groq API key (free tier available)
curl -X POST http://localhost:8000/api/ai/keys \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"provider": "groq", "key_name": "Groq Key", "api_key": "gsk_..."}'
```

### Getting API Keys

- **Anthropic**: https://console.anthropic.com/
- **OpenAI**: https://platform.openai.com/api-keys
- **Groq**: https://console.groq.com/ (has a free tier)

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_agents.py -v

# Run with verbose output
pytest -v
```

## Troubleshooting

### Python Version Issues

If you get errors about Python version, ensure you're using Python 3.12:

```bash
python --version
```

If you have multiple Python versions, specify the path:

```bash
# Windows
C:\Python312\python.exe -m venv .venv

# Linux/macOS
python3.12 -m venv .venv
```

### Playwright Installation Issues

If Playwright fails to install browsers:

```bash
# Install Playwright system dependencies (Linux)
playwright install-deps chromium

# Manually download browsers
playwright install --with-deps chromium
```

### Database Lock Errors

If you get database lock errors, ensure only one instance is running:

```bash
# Kill existing processes
# Windows
taskkill /F /IM python.exe

# Linux/macOS
pkill -f uvicorn
```

### Port Already in Use

If port 8000 is already in use, use a different port:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

### Memory Issues

If you're running out of memory:

1. Reduce the number of concurrent agents in the orchestrator config
2. Limit the job queue size
3. Use a lighter AI model (e.g., Haiku instead of Opus)

## Production Deployment

### Using Docker (Recommended)

Create a `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium --with-deps

COPY . .

RUN python -c "from app.db import init_db; init_db()"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t verity .
docker run -p 8000:8000 -v $(pwd)/data:/app/data verity
```

### Using Systemd (Linux)

Create `/etc/systemd/system/verity.service`:

```ini
[Unit]
Description=Verity API
After=network.target

[Service]
Type=simple
User=verity
WorkingDirectory=/opt/verity
Environment="PATH=/opt/verity/.venv/bin"
ExecStart=/opt/verity/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable verity
sudo systemctl start verity
sudo systemctl status verity
```

### Using Nginx as Reverse Proxy

Create `/etc/nginx/sites-available/verity`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/verity /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Security Considerations

1. **Change default passwords**: Ensure you use strong passwords for user accounts
2. **Environment variables**: Store sensitive data in environment variables, not in code
3. **HTTPS**: Use HTTPS in production with a valid SSL certificate
4. **CORS**: Restrict CORS origins to your actual domain
5. **Rate limiting**: Configure rate limiting appropriate for your usage
6. **Database backups**: Regularly backup the SQLite database
7. **API keys**: Rotate API keys regularly and never commit them to git

## Next Steps

- Read the [API Reference](README.md#api-reference)
- Explore the [dashboard UI](http://localhost:8000/)
- Set up [agent automation](README.md#agent-system-endpoints)
- Configure [scheduled jobs](README.md#configuration)

## Support

If you encounter issues not covered here:

1. Check the [GitHub Issues](https://github.com/mpaktit/Verity/issues)
2. Review the [documentation](README.md)
3. Open a new issue with details about your environment and error
