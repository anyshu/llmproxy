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
from collections import defaultdict
import time

# 加载环境变量
load_dotenv()

# 请求计数器
request_counter = defaultdict(lambda: {"count": 0, "timestamp": 0})

# 清理过期的请求计数
def cleanup_request_counter():
    current_time = time.time()
    expired_requests = []
    for key, value in request_counter.items():
        if current_time - value["timestamp"] > 60:  # 60秒后清理
            expired_requests.append(key)
    for key in expired_requests:
        del request_counter[key]

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
    # 打印请求信息到控制台
    print(f"\n{'='*50}")
    print(f"收到请求: {request.method} {request.url.path}")
    print(f"客户端IP: {request.client.host}")
    print(f"请求时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 只处理 OpenAI API 相关的请求
    if not any(request.url.path.strip('/').startswith(prefix) for prefix in ['v1/', 'chat/', 'completions', 'embeddings', 'models']):
        print(f"非 API 请求，转发给下一个处理器")
        return await call_next(request)

    # 生成请求唯一标识
    request_id = f"{request.client.host}:{request.url.path}:{int(time.time())}"
    print(f"请求ID: {request_id}")
    
    # 更新请求计数
    request_counter[request_id]["count"] += 1
    request_counter[request_id]["timestamp"] = time.time()
    
    # 清理过期的请求计数
    if len(request_counter) > 1000:  # 防止内存泄漏
        cleanup_request_counter()
    
    # 检查是否重复请求
    if request_counter[request_id]["count"] > 1:
        logger.warning({
            "message": f"检测到重复请求",
            "request_id": request_id,
            "count": request_counter[request_id]["count"]
        })
        return JSONResponse(
            content={"error": "重复请求"},
            status_code=429
        )

    try:
        # 读取请求内容
        body = await request.body()
        body_str = body.decode() if body else ""
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
            "body": body_json if body_json else body_str,
            "request_id": request_id
        }
        
        # 根据不同的 API 端点调用相应的 OpenAI 方法
        try:
            if path == 'chat/completions':
                print(f"处理 chat/completions 请求")
                response = await client.chat.completions.create(**body_json)
            elif path == 'completions':
                print(f"处理 completions 请求")
                response = await client.completions.create(**body_json)
            elif path == 'embeddings':
                print(f"处理 embeddings 请求")
                response = await client.embeddings.create(**body_json)
            elif path == 'models':
                print(f"处理 models 请求")
                response = await client.models.list()
            else:
                print(f"未支持的 API 端点: {path}")
                error_response = {"error": f"未支持的 API 端点: {path}"}
                log_data["response"] = {"status_code": 400, "body": error_response}
                logger.info(log_data)
                return JSONResponse(content=error_response, status_code=400)
            
            # 处理流式响应
            if body_json.get('stream', False):
                print("开始处理流式响应")
                async def generate() -> AsyncGenerator[str, None]:
                    try:
                        chunk_count = 0
                        async for chunk in response:
                            chunk_count += 1
                            if chunk_count % 10 == 0:  # 每10个chunk打印一次
                                print(f"已发送 {chunk_count} 个响应块")
                            yield f"data: {json.dumps(chunk.dict())}\n\n"
                        print(f"流式响应完成，总共发送 {chunk_count} 个响应块")
                        yield "data: [DONE]\n\n"
                    except Exception as e:
                        print(f"流式响应出错: {str(e)}")
                        error_msg = {"error": str(e)}
                        log_data["response"] = {"status_code": 500, "body": error_msg}
                        logger.info(log_data)
                        yield f"data: {json.dumps(error_msg)}\n\n"
                    finally:
                        print(f"请求处理完成: {request_id}")
                        if request_id in request_counter:
                            del request_counter[request_id]
                
                log_data["response"] = {"status_code": 200, "body": "Stream response"}
                logger.info(log_data)
                return StreamingResponse(
                    generate(),
                    media_type='text/event-stream'
                )
            else:
                response_dict = response.dict()
                print(f"请求处理完成: {request_id}")
                log_data["response"] = {"status_code": 200, "body": response_dict}
                logger.info(log_data)
                if request_id in request_counter:
                    del request_counter[request_id]
                return JSONResponse(
                    content=response_dict,
                    status_code=200
                )
                    
        except Exception as e:
            print(f"请求处理出错: {str(e)}")
            error_msg = {"error": str(e)}
            log_data["response"] = {"status_code": 500, "body": error_msg}
            logger.info(log_data)
            if request_id in request_counter:
                del request_counter[request_id]
            return JSONResponse(
                content=error_msg,
                status_code=500
            )
            
    except Exception as e:
        print(f"请求处理出错: {str(e)}")
        error_msg = {"error": str(e)}
        logger.error({
            "client_ip": request.client.host,
            "method": request.method,
            "url": str(request.url),
            "error": str(e),
            "response": {"status_code": 500, "body": error_msg},
            "request_id": request_id
        })
        if request_id in request_counter:
            del request_counter[request_id]
        return JSONResponse(
            content=error_msg,
            status_code=500
        )

if __name__ == "__main__":
    import multiprocessing

    # 获取 CPU 核心数
    workers_count = multiprocessing.cpu_count()
    
    # 使用 CPU 核心数作为工作进程数（保留至少一个核心给系统）
    workers = max(2, workers_count - 1)
    
    logger.info({
        "message": f"代理服务器启动于端口 {PROXY_PORT}，工作进程数：{workers}",
        "client_ip": "system",
        "method": "START",
        "url": f"http://0.0.0.0:{PROXY_PORT}",
        "workers": workers,
        "response": {"status_code": 200, "body": "Server started"}
    })
    
    # 使用新的启动方式
    if workers > 1:
        # 使用多进程模式时，需要使用字符串形式的导入路径
        uvicorn.run(
            "proxy_server:app",  # 使用模块路径字符串
            host="0.0.0.0", 
            port=PROXY_PORT,
            workers=workers,
            loop="auto"
        )
    else:
        # 单进程模式下可以直接传递应用实例
        uvicorn.run(
            app,
            host="0.0.0.0", 
            port=PROXY_PORT,
            loop="auto"
        )