import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import uvicorn
import aiohttp
import json
from datetime import datetime
from pythonjsonlogger import jsonlogger
import logging

# Load environment variables from .env file
load_dotenv()

# Configure logging
logger = logging.getLogger('proxy_logger')
# 添加控制台处理器
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

# 添加文件处理器
fileHandler = logging.FileHandler('proxy_requests.log')
fileHandler.setFormatter(formatter)
logger.addHandler(fileHandler)

logger.setLevel(logging.INFO)

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_API_BASE_URL = os.getenv('OPENAI_API_BASE_URL')
PROXY_PORT = int(os.getenv('PROXY_PORT', 3000))

@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Log request details
    request_time = datetime.now()
    request_body = await request.body()
    request_body_str = request_body.decode() if request_body else ""
    
    log_data = {
        "timestamp": request_time.isoformat(),
        "client_ip": request.client.host,
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
        "body": request_body_str
    }
    
    # Forward the request to OpenAI
    try:
        async with aiohttp.ClientSession() as session:
            # Construct the target URL
            target_url = f"{OPENAI_API_BASE_URL}{request.url.path}"
            
            # Prepare headers
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # Forward the request
            async with session.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=request_body,
                params=request.query_params
            ) as response:
                response_body = await response.text()
                log_data["response"] = {
                    "status_code": response.status,
                    "body": response_body
                }
                logger.info("Request processed", extra=log_data)
                
                return Response(
                    content=response_body,
                    status_code=response.status,
                    headers=dict(response.headers)
                )
    except Exception as e:
        log_data["error"] = str(e)
        logger.error("Request failed", extra=log_data)
        return Response(
            content=json.dumps({"error": str(e)}),
            status_code=500,
            media_type="application/json"
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PROXY_PORT)