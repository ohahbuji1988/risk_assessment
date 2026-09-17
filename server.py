import os
import sys
import json
import mimetypes
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8000
WEB_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(WEB_DIR, '.env')

AVAILABLE_MODELS = {
    "groq": [
        {"id": "openai/gpt-oss-120b", "name": "GPT OSS 120B (Recommended)"},
        {"id": "openai/gpt-oss-20b", "name": "GPT OSS 20B (Ultra Fast)"},
        {"id": "qwen/qwen3.8-27b", "name": "Qwen 3.8 27B"},
        {"id": "groq/compound", "name": "Groq Compound (131k Context)"}
    ],
    "gemini": [
        {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash (Recommended)"},
        {"id": "gemini-2.0-flash-lite", "name": "Gemini 2.0 Flash Lite"},
        {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro (Deep Reasoning)"},
        {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash"}
    ]
}

def load_env():
    env_vars = {
        "GROQ_API_KEY": "",
        "GEMINI_API_KEY": "",
        "AI_PROVIDER": "groq",
        "GROQ_MODEL": "openai/gpt-oss-120b",
        "GEMINI_MODEL": "gemini-2.0-flash"
    }
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    env_vars[key.strip()] = val.strip()
    return env_vars

def save_env(data):
    env_vars = load_env()
    if 'groqApiKey' in data: env_vars['GROQ_API_KEY'] = data['groqApiKey']
    if 'geminiApiKey' in data: env_vars['GEMINI_API_KEY'] = data['geminiApiKey']
    if 'aiProvider' in data: env_vars['AI_PROVIDER'] = data['aiProvider']
    if 'groqModel' in data: env_vars['GROQ_MODEL'] = data['groqModel']
    if 'geminiModel' in data: env_vars['GEMINI_MODEL'] = data['geminiModel']

    lines = [
        "# Groq & Google Gemini API Keys\n",
        f"GROQ_API_KEY={env_vars.get('GROQ_API_KEY', '')}\n",
        f"GEMINI_API_KEY={env_vars.get('GEMINI_API_KEY', '')}\n\n",
        "# Default AI Provider (groq or gemini)\n",
        f"AI_PROVIDER={env_vars.get('AI_PROVIDER', 'groq')}\n\n",
        "# Default Models for each Provider\n",
        f"GROQ_MODEL={env_vars.get('GROQ_MODEL', 'openai/gpt-oss-120b')}\n",
        f"GEMINI_MODEL={env_vars.get('GEMINI_MODEL', 'gemini-2.0-flash')}\n"
    ]
    with open(ENV_PATH, 'w', encoding='utf-8') as f:
        f.writelines(lines)

class CleanHandler(BaseHTTPRequestHandler):
    def address_string(self):
        return self.client_address[0]

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        print(f"[HTTP] {format % args}", flush=True)

    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            rel_path = parsed.path.lstrip('/')
            if not rel_path or rel_path == 'index.html':
                rel_path = 'index.html'

            if rel_path == 'api/config':
                env_vars = load_env()
                res_data = {
                    "groqApiKey": env_vars.get("GROQ_API_KEY", ""),
                    "geminiApiKey": env_vars.get("GEMINI_API_KEY", ""),
                    "aiProvider": env_vars.get("AI_PROVIDER", "groq"),
                    "groqModel": env_vars.get("GROQ_MODEL", "openai/gpt-oss-120b"),
                    "geminiModel": env_vars.get("GEMINI_MODEL", "gemini-2.0-flash"),
                    "availableModels": AVAILABLE_MODELS
                }
                body = json.dumps(res_data, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            file_path = os.path.join(WEB_DIR, rel_path)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                ctype, _ = mimetypes.guess_type(file_path)
                if not ctype: ctype = 'application/octet-stream'
                with open(file_path, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', ctype)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_response(404)
                self.end_headers()
        except Exception as e:
            print(f"Error in do_GET: {e}", flush=True)
            import traceback
            traceback.print_exc()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/config':
            content_length = int(self.headers.get('Content-Length', 0))
            body_str = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body_str)
            save_env(data)
            res_body = json.dumps({"success": True}).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(res_body)))
            self.end_headers()
            self.wfile.write(res_body)
            return

        self.send_response(404)
        self.end_headers()

if __name__ == '__main__':
    os.chdir(WEB_DIR)
    server = ThreadingHTTPServer(('0.0.0.0', PORT), CleanHandler)
    print(f"Cost Analytics Server running on http://localhost:{PORT}", flush=True)
    server.serve_forever()
