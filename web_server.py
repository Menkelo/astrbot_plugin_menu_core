import threading
import socket
import logging
import traceback
from astrbot.api import logger

try:
    from flask import Flask, jsonify, request, send_file, make_response
    from werkzeug.serving import make_server
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False


class WebManager:
    def __init__(self, config, storage_instance):
        self.cfg = config
        self.storage = storage_instance
        self.server_thread = None
        self.server = None
        self.renderer = None

        self.has_error = False
        self.error_msg = None
        if not HAS_FLASK:
            self.has_error = True
            self.error_msg = "缺少 Flask 库，请 pip install flask"

    def set_error(self, msg: str):
        self.has_error = True
        self.error_msg = msg

    def set_renderer(self, renderer_instance):
        self.renderer = renderer_instance

    def _create_app(self):
        app = Flask(__name__)
        logging.getLogger('werkzeug').setLevel(logging.ERROR)

        @app.route('/')
        def index():
            return self.storage.get_html_content()

        @app.route('/api/config', methods=['GET', 'POST'])
        def handle_config():
            if request.method == 'GET':
                return jsonify(self.storage.load_config())
            elif request.method == 'POST':
                try:
                    self.storage.save_config(request.json)
                    return jsonify({"status": "ok"})
                except Exception as e:
                    return jsonify({"msg": str(e)}), 500

        @app.route('/api/preview', methods=['POST'])
        def preview():
            if not self.renderer:
                return jsonify({"error": "渲染器未初始化"}), 500
            try:
                path = self.renderer.render_sync_for_web(config_data=request.json)
                resp = make_response(send_file(str(path), mimetype='image/png'))
                resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
                resp.headers["Pragma"] = "no-cache"
                return resp
            except Exception as e:
                logger.error(f"[menu-core] Preview Error: {traceback.format_exc()}")
                return jsonify({"error": str(e)}), 500

        return app

    # ✅ 检测端口是否可用
    def _is_port_free(self, host, port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            s.close()
            return True
        except OSError:
            return False

    # ✅ 自动找可用端口
    def _find_free_port(self, host, start_port, max_try=20):
        for p in range(start_port, start_port + max_try):
            if self._is_port_free(host, p):
                return p
        return None

    async def start(self):
        if self.server_thread and self.server_thread.is_alive():
            return "⚠️ 后台已在运行中"
        if not HAS_FLASK:
            return "❌ 缺少 Flask 库"

        host = self.cfg.get("web_host", "0.0.0.0")
        port = self.cfg.get("web_port", 9876)

        try:
            free_port = self._find_free_port(host, port)
            if free_port is None:
                return f"❌ 端口 {port} 已被占用，且未找到可用端口"
            port = free_port

            app = self._create_app()
            self.server = make_server(host, port, app)

            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()

            return f"✅ 菜单编辑器已启动: http://{self._get_local_ip()}:{port}/"

        except SystemExit:
            return f"❌ 端口 {port} 已被占用，请修改 web_port"
        except BaseException as e:
            return f"❌ 启动失败: {e}"

    async def stop(self):
        if self.server:
            self.server.shutdown()
            self.server = None

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"