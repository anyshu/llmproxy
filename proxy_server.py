import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn
import openai
import json
import logging
from datetime import datetime
from typing import AsyncGenerator, Optional

# 加载环境变量
load_dotenv()

# 自定义日志处理器
class JSONFormatter(logging.Formatter):
    def format(self, record):
        # 确保 record.msg 是一个字典
        if isinstance(record.msg, dict):
            log_data = record.msg
        else:
            log_data = {"message": str(record.msg)}
        
        # 添加时间戳
        log_data["asctime"] = datetime.now().isoformat()
        
        # 添加日志级别
        log_data["levelname"] = record.levelname
        
        return json.dumps(log_data, ensure_ascii=False)

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 文件处理器
file_handler = logging.FileHandler('proxy_requests.log', encoding='utf-8')
file_handler.setFormatter(JSONFormatter())
logger.addHandler(file_handler)

# 控制台处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

app = FastAPI()

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 环境变量
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_API_BASE_URL = os.getenv('OPENAI_API_BASE_URL')
PROXY_PORT = int(os.getenv('PROXY_PORT', 3000))

if not OPENAI_API_KEY:
    raise ValueError("请设置 OPENAI_API_KEY 环境变量")

# 配置 OpenAI 客户端
client = openai.AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_API_BASE_URL if OPENAI_API_BASE_URL else None
)

@app.middleware("http")
async def proxy_middleware(request: Request, call_next):
    try:
        # 读取请求内容
        body = await request.body()
        body_str = body.decode() if body else ""
        print(body_str)
        body_json = json.loads(body_str) if body_str else {}
        
        # 获取请求路径
        path = request.url.path
        if path.startswith('/v1/'):
            path = path[3:]  # 移除 /v1 前缀
        
        # 移除开头的斜杠
        path = path.lstrip('/')
        
        # 准备日志数据
        log_data = {
            "client_ip": request.client.host,
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "body": body_json if body_json else body_str
        }
        
        # 根据不同的 API 端点调用相应的 OpenAI 方法
        try:
            if path == 'chat/completions':
                response = await client.chat.completions.create(**body_json)
            elif path == 'completions':
                response = await client.completions.create(**body_json)
            elif path == 'embeddings':
                response = await client.embeddings.create(**body_json)
            elif path == 'models':
                response = await client.models.list()
            else:
                error_response = {"error": f"未支持的 API 端点: {path}"}
                log_data["response"] = {"status_code": 400, "body": error_response}
                logger.info(log_data)
                return JSONResponse(content=error_response, status_code=400)
            
            # 处理流式响应
            if body_json.get('stream', False):
                async def generate() -> AsyncGenerator[str, None]:
                    try:
                        async for chunk in response:
                            yield f"data: {json.dumps(chunk.dict())}\n\n"
                        yield "data: [DONE]\n\n"
                    except Exception as e:
                        error_msg = {"error": str(e)}
                        log_data["response"] = {"status_code": 500, "body": error_msg}
                        logger.info(log_data)
                        yield f"data: {json.dumps(error_msg)}\n\n"
                
                log_data["response"] = {"status_code": 200, "body": "Stream response"}
                logger.info(log_data)
                return StreamingResponse(
                    generate(),
                    media_type='text/event-stream'
                )
            else:
                response_dict = response.dict()
                log_data["response"] = {"status_code": 200, "body": response_dict}
                logger.info(log_data)
                return JSONResponse(
                    content=response_dict,
                    status_code=200
                )
                    
        except Exception as e:
            error_msg = {"error": str(e),"proxy": "proxy server error"}
            log_data["response"] = {"status_code": 500, "body": error_msg}
            logger.info(log_data)
            return JSONResponse(
                content=error_msg,
                status_code=500
            )
            
    except Exception as e:
        error_msg = {"error": str(e)}
        logger.error({
            "client_ip": request.client.host,
            "method": request.method,
            "url": str(request.url),
            "error": str(e),
            "response": {"status_code": 500, "body": error_msg}
        })
        return JSONResponse(
            content=error_msg,
            status_code=500
        )

if __name__ == "__main__":
    logger.info({
        "message": f"代理服务器启动于端口 {PROXY_PORT}",
        "client_ip": "system",
        "method": "START",
        "url": f"http://0.0.0.0:{PROXY_PORT}",
        "response": {"status_code": 200, "body": "Server started"}
    })
    uvicorn.run(app, host="0.0.0.0", port=PROXY_PORT)