import json
from pathlib import Path
from astrbot.api import logger

class PluginStorage:
    def __init__(self, config, data_root=None):
        self.plugin_root = Path(__file__).resolve().parent

        # ✅ 默认 plugin_data/<插件名>
        if data_root:
            self.bot_data_root = Path(data_root).resolve()
        else:
            self.bot_data_root = self.plugin_root.parent.parent / "plugin_data" / self.plugin_root.name

        self.config_file = self.bot_data_root / "menu_config.json"
        self.template_dir = self.plugin_root / "templates"
        self.html_file = self.template_dir / "index.html"
        self.font_dir = self.bot_data_root / "fonts"

        logger.info(f"[menu-core] 数据目录: {self.bot_data_root}")
        logger.info(f"[menu-core] 模板文件: {self.html_file}")

        self.default_config = {
            "title": "我的机器人菜单",
            "subtitle": "发送指令使用功能",
            "design": {
                "layout_columns": 2,
                "title_align": "center",
                "theme": "dark"
            },
            "groups": [
                {
                    "title": "常用指令",
                    "enabled": True,
                    "align": "left",
                    "menus": [
                        {"name": "帮助", "desc": "查看所有指令", "enabled": True},
                        {"name": "关于", "desc": "机器人信息", "enabled": True}
                    ]
                }
            ]
        }

    def init_paths(self):
        if not self.bot_data_root.exists():
            self.bot_data_root.mkdir(parents=True, exist_ok=True)
        if not self.font_dir.exists():
            self.font_dir.mkdir(parents=True, exist_ok=True)
        if not self.config_file.exists():
            self.save_config(self.default_config)

    def load_config(self) -> dict:
        if not self.config_file.exists():
            return self.default_config
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "design" not in data:
                    data["design"] = self.default_config["design"]
                return data
        except Exception as e:
            logger.error(f"[menu-core] 加载配置失败: {e}")
            return self.default_config

    def save_config(self, data: dict):
        if not self.bot_data_root.exists():
            self.bot_data_root.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def get_html_content(self) -> str:
        if not self.html_file.exists():
            return "<h1>Error: Template file not found via storage path.</h1>"
        with open(self.html_file, 'r', encoding='utf-8') as f:
            return f.read()