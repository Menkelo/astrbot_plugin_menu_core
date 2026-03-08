import asyncio
import traceback
from pathlib import Path

from astrbot.api.star import Context, Star
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.api import event, logger
from astrbot.api.event import filter

from . import storage
from .renderer import MenuRenderer
from .web_server import WebManager

MENU_REGEX_PATTERN = r"^(菜单|menu)$"


class MenuCore(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

        # ✅ 数据目录改为 plugin_data/<插件名>
        plugin_root = Path(__file__).resolve().parent
        data_root = plugin_root.parent.parent / "plugin_data" / plugin_root.name

        self.storage = storage.PluginStorage(config, data_root=data_root)
        self.web_manager = WebManager(config, self.storage)
        self.renderer = MenuRenderer(self.storage)
        self.web_manager.set_renderer(self.renderer)

        self._init_task = asyncio.create_task(self._async_init())

    async def _async_init(self):
        try:
            logger.info("[menu-core] 正在初始化资源...")
            self.storage.init_paths()

            try:
                import playwright  # noqa: F401
            except ImportError:
                raise ImportError("缺少 Playwright，请安装: pip install playwright && playwright install")

            logger.info("✅ [menu-core] 初始化完成")

            if not self.web_manager.has_error:
                result_msg = await self.web_manager.start()
                logger.info(f"[menu-core] {result_msg}")
            else:
                logger.error(f"[menu-core] Web 后台未启动: {self.web_manager.error_msg}")

        except Exception as e:
            logger.error(f"❌ 初始化失败: {traceback.format_exc()}")
            self.web_manager.set_error(str(e))

    async def on_unload(self):
        await self.web_manager.stop()

    async def _generate_menu(self, event_obj: event.AstrMessageEvent):
        if not self._init_task.done():
            await asyncio.wait([self._init_task], timeout=5.0)

        if self.web_manager.has_error:
            yield event_obj.plain_result(f"❌ 插件错误: {self.web_manager.error_msg}")
            return

        try:
            image_path = await self.renderer.render_menu_image()
            if image_path:
                yield event_obj.image_result(str(image_path))
            else:
                yield event_obj.plain_result("⚠️ 暂无菜单配置。")
        except Exception as e:
            logger.error(f"生成菜单失败: {traceback.format_exc()}")
            yield event_obj.plain_result(f"❌ 渲染错误: {e}")

    @filter.regex(MENU_REGEX_PATTERN)
    async def menu_regex_cmd(self, event: event.AstrMessageEvent):
        async for result in self._generate_menu(event):
            yield result

    @filter.llm_tool(name="show_graphical_menu")
    async def show_menu_tool(self, event: event.AstrMessageEvent):
        async for result in self._generate_menu(event):
            await event.send(result)
        return "已发送菜单图片。"