from flask import Flask, render_template_string
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get proxy port from environment variable
PROXY_PORT = os.getenv('PROXY_PORT', '3000')

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>LLM Proxy Monitor</title>
    <meta charset="utf-8">
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 20px; 
            background-color: #f5f5f5;
        }
        .request-card {
            border: 1px solid #ddd;
            margin: 10px 0;
            padding: 15px;
            border-radius: 5px;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .request-header { 
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #f8f9fa;
            padding: 10px;
            margin: -15px -15px 10px -15px;
            border-radius: 5px 5px 0 0;
            border-bottom: 1px solid #eee;
        }
        .success { color: #28a745; }
        .error { color: #dc3545; }
        pre {
            background: #f8f8f8;
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
            border: 1px solid #eee;
        }
        details {
            margin: 10px 0;
        }
        details summary {
            cursor: pointer;
            padding: 8px;
            background: #f8f9fa;
            border-radius: 4px;
        }
        details summary:hover {
            background: #e9ecef;
        }
        .timestamp {
            color: #666;
            font-size: 0.9em;
        }
        .method {
            font-weight: bold;
            padding: 3px 8px;
            border-radius: 3px;
            background: #e9ecef;
        }
        .status {
            font-weight: bold;
            padding: 3px 8px;
            border-radius: 3px;
        }
    </style>
    <script>
        function refreshData() {
            fetch(window.location.href)
                .then(response => response.text())
                .then(html => {
                    const parser = new DOMParser();
                    const newDoc = parser.parseFromString(html, 'text/html');
                    const currentContent = document.querySelector('#content');
                    const newContent = newDoc.querySelector('#content');
                    if (currentContent && newContent) {
                        currentContent.innerHTML = newContent.innerHTML;
                    }
                });
        }
        // 每5秒自动刷新
        setInterval(refreshData, 5000);
    </script>
</head>
<body>
    <h1>LLM Proxy Monitor</h1>
    <p>代理服务器地址: <code>http://localhost:{{ proxy_port }}</code></p>
    <div id="content">
    {% for request in requests %}
    <div class="request-card">
        <div class="request-header">
            <span class="timestamp">{{ request.timestamp }}</span>
            <span class="method">{{ request.method }}</span>
            <span class="status {{ 'success' if request.response.status_code < 400 else 'error' }}">
                状态码: {{ request.response.status_code }}
            </span>
        </div>
        <p><strong>客户端 IP:</strong> {{ request.client_ip }}</p>
        <p><strong>请求 URL:</strong> {{ request.url }}</p>
        <details>
            <summary>请求头</summary>
            <pre>{{ request.headers | tojson(indent=2) }}</pre>
        </details>
        <details>
            <summary>请求体</summary>
            <pre>{{ request.body }}</pre>
        </details>
        <details>
            <summary>响应内容</summary>
            <pre>{{ request.response.body }}</pre>
        </details>
    </div>
    {% endfor %}
    </div>
</body>
</html>
'''

def parse_log_file():
    requests = []
    log_file = 'proxy_requests.log'
    
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    log_entry = json.loads(line)
                    # 移除多余的日志字段，只保留我们需要的信息
                    if isinstance(log_entry, dict):
                        request_data = {
                            'timestamp': log_entry.get('asctime', ''),
                            'client_ip': log_entry.get('client_ip', ''),
                            'method': log_entry.get('method', ''),
                            'url': log_entry.get('url', ''),
                            'headers': log_entry.get('headers', {}),
                            'body': log_entry.get('body', ''),
                            'response': log_entry.get('response', {'status_code': 0, 'body': ''})
                        }
                        requests.append(request_data)
                except json.JSONDecodeError:
                    continue
    
    # 按时间戳倒序排序，最新的请求显示在前面
    requests.sort(key=lambda x: x['timestamp'], reverse=True)
    return requests[:100]  # 只返回最近的100个请求

@app.route('/')
def index():
    requests = parse_log_file()
    return render_template_string(HTML_TEMPLATE, requests=requests, proxy_port=PROXY_PORT)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)