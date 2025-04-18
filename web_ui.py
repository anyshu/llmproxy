from flask import Flask, render_template_string
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get proxy port from environment variable
PROXY_PORT = os.getenv('PROXY_PORT', '3000')

def format_json(json_str):
    try:
        if isinstance(json_str, str):
            # Try to parse JSON string
            data = json.loads(json_str)
        else:
            data = json_str
        return json.dumps(data, indent=2, ensure_ascii=False)
    except:
        return json_str

def format_datetime(timestamp_str):
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return timestamp_str

app = Flask(__name__)

# Register the custom filter
app.jinja_env.filters['format_json'] = format_json

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
            line-height: 1.6;
        }
        .request-card {
            border: 1px solid #ddd;
            margin: 15px 0;
            padding: 15px;
            border-radius: 8px;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .request-header { 
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #f8f9fa;
            padding: 12px;
            margin: -15px -15px 10px -15px;
            border-radius: 8px 8px 0 0;
            border-bottom: 1px solid #eee;
            flex-wrap: wrap;
            gap: 8px;
        }
        .success { 
            color: #28a745; 
            background: #e8f5e9;
            padding: 3px 8px;
            border-radius: 4px;
        }
        .error { 
            color: #dc3545; 
            background: #ffebee;
            padding: 3px 8px;
            border-radius: 4px;
        }
        pre {
            background: #f8f8f8;
            padding: 12px;
            border-radius: 6px;
            overflow-x: auto;
            border: 1px solid #eee;
            font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.5;
            white-space: pre-wrap;
            word-wrap: break-word;
            max-width: 100%;
        }
        pre code {
            display: block;
            width: 100%;
        }
        details {
            margin: 12px 0;
            background: white;
            border-radius: 6px;
        }
        details summary {
            cursor: pointer;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 6px;
            font-weight: 500;
            color: #1a73e8;
        }
        details summary:hover {
            background: #e9ecef;
        }
        .timestamp {
            color: #666;
            font-size: 0.9em;
            font-family: monospace;
        }
        .method {
            font-weight: bold;
            padding: 3px 8px;
            border-radius: 4px;
            background: #e3f2fd;
            color: #1565c0;
        }
        .url {
            font-family: monospace;
            background: #f5f5f5;
            padding: 4px 8px;
            border-radius: 4px;
            word-break: break-all;
            word-wrap: break-word;
            max-width: 100%;
        }
        .status {
            font-weight: 500;
            padding: 3px 8px;
            border-radius: 4px;
        }
        .request-info {
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 8px;
            align-items: start;
            margin: 12px 0;
        }
        .request-info strong {
            white-space: nowrap;
        }
        .request-info span {
            word-break: break-word;
        }
        .refresh-info {
            color: #666;
            font-size: 0.9em;
            text-align: center;
            margin-top: 20px;
            padding: 10px;
            background: #fff;
            border-radius: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
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
        <div class="request-info">
            <strong>客户端 IP:</strong>
            <span>{{ request.client_ip }}</span>
            <strong>请求 URL:</strong>
            <span class="url">{{ request.url }}</span>
        </div>
        <details>
            <summary>请求头</summary>
            <pre><code>{{ request.headers | tojson(indent=2) }}</code></pre>
        </details>
        <details>
            <summary>请求体</summary>
            <pre><code>{{ request.body | format_json }}</code></pre>
        </details>
        <details>
            <summary>响应内容</summary>
            <pre><code>{{ request.response.body | format_json }}</code></pre>
        </details>
    </div>
    {% endfor %}
    </div>
    <div class="refresh-info">
        页面每 5 秒自动刷新一次 | 最近显示 100 条请求记录
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
                            'timestamp': format_datetime(log_entry.get('asctime', '')),
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
    return render_template_string(HTML_TEMPLATE, 
                                requests=requests, 
                                proxy_port=PROXY_PORT,
                                format_json=format_json)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)