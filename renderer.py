import asyncio
import json
import random
import threading
import hashlib
from pathlib import Path

class MenuRenderer:
    def __init__(self, storage_instance):
        self.storage = storage_instance
        self._lock = threading.Lock()
        self.cache_file = self.storage.bot_data_root / "render_cache.json"

    async def render_menu_image(self) -> Path:
        """正式渲染：若配置没变，直接返回旧图；变化则覆盖旧图"""
        config = self.storage.load_config()
        config_hash = self._calc_config_hash(config)

        cache = self._load_cache()
        if cache and cache.get("hash") == config_hash:
            fname = cache.get("file")
            if fname:
                path = self.storage.bot_data_root / fname
                if path.exists():
                    return path  # ✅ 配置未变，直接复用

        # 配置变化 -> 重新渲染并覆盖
        new_path = await asyncio.to_thread(self._render_sync, config, False)

        # 更新缓存
        self._save_cache(config_hash, new_path.name)
        return new_path

    def render_sync_for_web(self, config_data) -> Path:
        """预览始终重新渲染"""
        return self._render_sync(config_data, True)

    def _render_sync(self, config_data, is_preview=False) -> Path:
        config = json.loads(json.dumps(config_data))
        if is_preview:
            config["is_preview"] = True

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise ImportError("缺少 Playwright，请安装: pip install playwright && playwright install")

        with self._lock:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )
                page = browser.new_page(viewport={"width": 900, "height": 1200})

                config_json = json.dumps(config, ensure_ascii=False)
                page.add_init_script(
                    f"window.__RENDER_DATA__ = {config_json}; window.__RENDER_ONLY__ = true;"
                )

                html_url = self.storage.html_file.resolve().as_uri()
                page.goto(html_url, wait_until="networkidle")

                selector = ".canvas-list"
                page.wait_for_selector(selector, timeout=15000)

                page.evaluate("() => document.fonts.ready")

                width = page.eval_on_selector(selector, "el => el.scrollWidth")
                height = page.eval_on_selector(selector, "el => el.scrollHeight")
                page.set_viewport_size({"width": int(width), "height": int(height)})
                page.wait_for_timeout(100)

                element = page.query_selector(selector)
                png_bytes = element.screenshot(type="png")

                browser.close()

        return self._save_image_bytes(png_bytes, config)

    def _save_image_bytes(self, png_bytes: bytes, config: dict) -> Path:
        if config.get("is_preview"):
            # 预览图仍然随机
            filename = f"preview_{random.randint(1000,9999)}.png"
            save_path = self.storage.bot_data_root / filename
            with open(save_path, "wb") as f:
                f.write(png_bytes)
            return save_path
        else:
            # ✅ 正式渲染图固定文件名，直接覆盖
            filename = "menu_latest.png"
            save_path = self.storage.bot_data_root / filename

            # 可选：写临时文件再替换，避免中途读取
            tmp_path = self.storage.bot_data_root / f".tmp_{random.randint(1000,9999)}.png"
            with open(tmp_path, "wb") as f:
                f.write(png_bytes)
            tmp_path.replace(save_path)
            return save_path

    def _calc_config_hash(self, config: dict) -> str:
        raw = json.dumps(config, ensure_ascii=False, sort_keys=True)
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def _load_cache(self):
        if not self.cache_file.exists():
            return None
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return None

    def _save_cache(self, config_hash: str, filename: str):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump({"hash": config_hash, "file": filename}, f)
        except:
            pass