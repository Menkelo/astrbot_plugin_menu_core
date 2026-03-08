# astrbot_plugin_menu_core

> AstrBot 菜单核心插件：基于 Web 可视化编辑器生成菜单图片，支持实时预览、配置保存、消息指令触发输出。

## 功能特性

- 🧩 **Web 可视化编辑**
  - 在线修改标题、副标题、分组、菜单项
  - 分组与菜单项支持拖拽排序
  - 深色 / 浅色主题切换
- 🖼️ **实时预览**
  - 前端点击「预览」后，后端调用 Playwright 实时渲染 PNG
- 💾 **配置持久化**
  - 配置保存至 `plugin_data/<插件名>/menu_config.json`
- ⚡ **渲染缓存**
  - 正式渲染会根据配置哈希复用上次生成图片，减少重复渲染开销
- 🔌 **自动启动 Web 后台**
  - 插件初始化后自动启动编辑后台
  - 端口占用时自动尝试后续可用端口
- 🤖 **消息触发**
  - `菜单` 或 `menu` 直接发送菜单图片
  - 提供 LLM Tool：`show_graphical_menu`

---

## 运行依赖

请确保你的环境已安装：

- Python 3.9+
- `flask`
- `playwright`

安装示例：

```bash
pip install flask playwright
playwright install
```

> 若缺少依赖，插件会在初始化阶段报错（如 Flask/Playwright 未安装）。

---

## 配置项

对应 `_conf_schema.json`：

| 配置项 | 类型 | 默认值 | 说明 |
|---|---|---:|---|
| `web_host` | string | `0.0.0.0` | Web 编辑器监听地址 |
| `web_port` | int | `9876` | Web 编辑器起始端口 |

> 当 `web_port` 被占用时，会自动向后尝试可用端口（最多 20 个）。

---

## 使用方式

### 1) 启动插件

插件加载后会自动初始化：
- 创建数据目录
- 检查 Playwright
- 启动 Web 后台

日志中会出现类似：

```text
✅ 菜单编辑器已启动: http://<你的局域网IP>:9876/
```

### 2) 打开 Web 编辑器

浏览器访问日志中的地址，进行菜单配置与预览。

### 3) 保存配置

点击「💾 保存」后会写入配置文件，后续消息触发时使用该配置渲染。

### 4) 发送菜单图片

在聊天中发送以下任一指令：

- `菜单`
- `menu`

插件会返回当前菜单图片。

---

## 数据文件结构

插件运行后会在 `plugin_data/<插件名>/` 下生成数据：

```text
plugin_data/astrbot_plugin_menu_core/
├─ menu_config.json        # 菜单配置
├─ menu_latest.png         # 正式渲染输出（固定文件名覆盖）
├─ render_cache.json       # 配置哈希缓存
├─ preview_****.png        # Web 预览临时图（随机名）
└─ fonts/                  # 字体目录（预留）
```

---

## 后端接口（WebManager）

- `GET /api/config`：读取配置
- `POST /api/config`：保存配置
- `POST /api/preview`：生成预览图（PNG）

---

## LLM Tool

插件提供工具：

- `show_graphical_menu`

调用后会主动发送菜单图片，并返回文本：`已发送菜单图片。`

---

## 常见问题

### Q1: 报错“缺少 Flask 库”
安装 Flask：

```bash
pip install flask
```

### Q2: 报错“缺少 Playwright”
安装并初始化浏览器：

```bash
pip install playwright
playwright install
```

### Q3: Web 打不开
- 检查日志中的实际启动端口（可能不是 9876，而是自动顺延端口）
- 若远程访问，请确认防火墙与监听地址配置

### Q4: 菜单没有更新
- 确认在 Web 端点击了「保存」
- 正式渲染有缓存机制：配置不变会复用旧图（这是正常行为）

---

## 开发说明

核心模块：

- `main.py`：插件入口、初始化、命令处理
- `storage.py`：配置与路径管理
- `renderer.py`：Playwright 渲染与缓存逻辑
- `web_server.py`：Flask Web 后台与 API
- `templates/index.html`：可视化编辑器前端
