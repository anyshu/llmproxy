# LLM Proxy Server

一个简单但功能强大的 LLM API 代理服务器，支持请求转发和监控功能。

## 功能特点

- API 代理转发：将请求转发到指定的 LLM API 端点
- 实时监控：通过 Web UI 界面监控所有代理请求
- 自动日志记录：记录所有请求和响应的详细信息
- 环境变量配置：支持通过 .env 文件进行灵活配置

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件并设置以下配置：

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_API_BASE_URL=your_api_base_url_here
PROXY_PORT=3000
```

### 3. 启动服务

启动代理服务器：
```bash
python proxy_server.py
```

启动监控界面：
```bash
python web_ui.py
```

### 4. 访问服务

- 代理服务器地址：`http://localhost:3000`
- 监控界面地址：`http://localhost:8080`

## 项目结构

- `proxy_server.py`: 主要的代理服务器实现
- `web_ui.py`: Web 监控界面实现
- `requirements.txt`: 项目依赖列表
- `.env`: 环境变量配置文件

## 使用说明

1. 所有发往代理服务器的请求都会被自动转发到配置的 API 端点
2. 每个请求都会被记录到日志文件中
3. 可以通过 Web 监控界面实时查看请求历史
4. 监控界面会自动每 5 秒刷新一次，显示最新的请求信息

## 依赖项

- FastAPI: Web 框架
- uvicorn: ASGI 服务器
- Flask: Web UI 框架
- python-dotenv: 环境变量管理
- aiohttp: 异步 HTTP 客户端
- python-json-logger: JSON 格式日志

## 注意事项

1. 请确保 `.env` 文件中包含正确的 API 密钥和 URL
2. 建议将 `.env` 文件添加到 .gitignore 中以保护敏感信息
3. 所有请求都会被记录到 `proxy_requests.log` 文件中
