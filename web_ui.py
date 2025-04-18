from flask import Flask, render_template_string, jsonify, request
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

def delete_log_entry(timestamp):
    log_file = 'proxy_requests.log'
    temp_file = 'proxy_requests_temp.log'
    
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f, open(temp_file, 'w', encoding='utf-8') as temp:
            for line in f:
                try:
                    log_entry = json.loads(line)
                    if log_entry.get('asctime') != timestamp:
                        temp.write(line)
                except json.JSONDecodeError:
                    temp.write(line)
        
        os.replace(temp_file, log_file)
        return True
    return False

def clear_all_logs():
    log_file = 'proxy_requests.log'
    if os.path.exists(log_file):
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write('')
        return True
    return False

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
        .action-buttons {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
            margin: 20px 0;
        }
    </style>
    <script>
        // 保存展开状态的Map
        let expandedStates = new Map();
        // 记录最新的时间戳，用于判断新记录
        let latestTimestamp = '';

        // 保存当前所有details的展开状态
        function saveExpandedStates() {
            const details = document.querySelectorAll('.request-card details');
            expandedStates.clear();
            details.forEach((detail) => {
                const card = detail.closest('.request-card');
                const timestamp = card.querySelector('.timestamp').textContent;
                const key = `${timestamp}-${detail.querySelector('summary').textContent}`;
                expandedStates.set(key, detail.open);
            });
        }

        // 恢复展开状态
        function restoreExpandedStates() {
            const details = document.querySelectorAll('.request-card details');
            details.forEach((detail) => {
                const card = detail.closest('.request-card');
                const timestamp = card.querySelector('.timestamp').textContent;
                const key = `${timestamp}-${detail.querySelector('summary').textContent}`;
                if (expandedStates.has(key)) {
                    detail.open = expandedStates.get(key);
                }
            });
        }

        // 获取当前显示的第一条记录的时间戳
        function getLatestDisplayedTimestamp() {
            const firstCard = document.querySelector('.request-card');
            if (firstCard) {
                return firstCard.querySelector('.timestamp').textContent;
            }
            return '';
        }

        // 智能更新内容
        function smartUpdateContent(newContent) {
            const currentFirstTimestamp = getLatestDisplayedTimestamp();
            const container = document.querySelector('#content');
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = newContent;
            
            // 获取新内容中的所有卡片
            const newCards = Array.from(tempDiv.querySelectorAll('.request-card'));
            
            // 找到第一个时间戳匹配的卡片的索引
            const matchIndex = newCards.findIndex(card => 
                card.querySelector('.timestamp').textContent === currentFirstTimestamp
            );
            
            if (matchIndex > 0) {
                // 只插入新的记录
                const fragment = document.createDocumentFragment();
                for (let i = 0; i < matchIndex; i++) {
                    fragment.appendChild(newCards[i].cloneNode(true));
                }
                container.insertBefore(fragment, container.firstChild);
            } else if (matchIndex === -1 && container.children.length === 0) {
                // 如果页面为空，显示所有新记录
                container.innerHTML = tempDiv.innerHTML;
            }
        }

        function refreshData() {
            // 在刷新前保存展开状态
            saveExpandedStates();
            
            fetch(window.location.href)
                .then(response => response.text())
                .then(html => {
                    const parser = new DOMParser();
                    const newDoc = parser.parseFromString(html, 'text/html');
                    const newContent = newDoc.querySelector('#content').innerHTML;
                    
                    // 使用智能更新替代直接替换内容
                    smartUpdateContent(newContent);
                    
                    // 恢复展开状态
                    restoreExpandedStates();
                });
        }
        
        // 监听所有details的展开/折叠事件
        document.addEventListener('click', function(e) {
            if (e.target.matches('details summary')) {
                setTimeout(saveExpandedStates, 0);
            }
        });

        function deleteEntry(timestamp) {
            if (confirm('确定要删除这条记录吗？')) {
                fetch(`/delete/${encodeURIComponent(timestamp)}`, { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            refreshData();
                        } else {
                            alert('删除失败');
                        }
                    });
            }
        }
        
        function clearAllLogs() {
            if (confirm('确定要清除所有记录吗？此操作不可撤销。')) {
                fetch('/clear-all', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            refreshData();
                        } else {
                            alert('清除失败');
                        }
                    });
            }
        }
        
        // 页面加载完成后记录初始时间戳
        document.addEventListener('DOMContentLoaded', function() {
            latestTimestamp = getLatestDisplayedTimestamp();
        });

        // 每5秒自动刷新
        setInterval(refreshData, 5000);
    </script>
</head>
<body>
    <h1>LLM Proxy Monitor</h1>
    <p>代理服务器地址: <code>http://localhost:{{ proxy_port }}</code></p>
    <div class="action-buttons">
        <button id="clearAllBtn" class="btn btn-danger" onclick="clearAllLogs()">清除所有记录</button>
    </div>
    <div id="content">
    {% for request in requests %}
    <div class="request-card">
        <div class="request-header">
            <span class="timestamp">{{ request.timestamp }}</span>
            <span class="method">{{ request.method }}</span>
            <span class="status {{ 'success' if request.response.status_code < 400 else 'error' }}">
                状态码: {{ request.response.status_code }}
            </span>
            <button class="delete-btn" onclick="deleteEntry('{{ request.raw_timestamp }}')">删除</button>
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
                            'raw_timestamp': log_entry.get('asctime', ''),  # 保存原始时间戳用于删除操作
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

@app.route('/delete/<timestamp>', methods=['POST'])
def delete_entry(timestamp):
    success = delete_log_entry(timestamp)
    return jsonify({'success': success})

@app.route('/clear-all', methods=['POST'])
def clear_all():
    success = clear_all_logs()
    return jsonify({'success': success})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)