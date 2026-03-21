# markdown-proxy

> Fetch any URL as clean Markdown — even login-required pages like X/Twitter and WeChat articles.
>
> 将任意 URL 转为干净的 Markdown，支持需要登录的页面（X/Twitter、微信公众号等）。

**[English](#english) | [中文](#中文)**

---

<a name="english"></a>
## English

### What it does

When you share a URL with Claude, this skill automatically fetches the full content as clean Markdown using proxy services. It works with pages that normally require login (X/Twitter, Instagram, etc.) and includes a built-in scraper for WeChat Official Account (公众号) articles.

### How it works

The skill routes URLs through the best available method:

| URL type | Method | Why |
|----------|--------|-----|
| WeChat 公众号 (`mp.weixin.qq.com`) | Built-in Playwright scraper | Anti-scraping protection requires headless browser |
| YouTube | Dedicated YouTube skill | Specialized tools for video content |
| Everything else | Proxy cascade: r.jina.ai → defuddle.md → agent-fetch → defuddle CLI | Free, no API key, handles login walls |

### Prerequisites

- [ ] **Claude Code** installed ([docs](https://docs.anthropic.com/en/docs/claude-code))
- [ ] **Python 3.8+** with `playwright` and `beautifulsoup4` (for WeChat scraping)
  ```bash
  python3 --version  # verify
  pip install playwright beautifulsoup4 lxml
  playwright install chromium
  ```
- [ ] **curl** (pre-installed on macOS/Linux)

### Installation

```bash
npx skills add joeseesun/markdown-proxy
```

Verify:
```bash
ls ~/.claude/skills/markdown-proxy/SKILL.md
```

### Usage

Just share a URL with Claude:

- "Read this article for me: https://example.com/post"
- "Fetch this tweet: https://x.com/user/status/123456"
- "Help me read this WeChat article: https://mp.weixin.qq.com/s/abc123"

### Proxy priority

1. **r.jina.ai** — most complete content, preserves image links
2. **defuddle.md** — cleaner output with YAML frontmatter
3. **agent-fetch** — local tool, no network proxy needed
4. **defuddle CLI** — local CLI for standard web pages

### Troubleshooting

| Problem | Solution |
|---------|----------|
| WeChat scraping fails | Run `playwright install chromium` to install browser |
| r.jina.ai returns empty | Try defuddle.md (automatic fallback) |
| All proxies fail | URL may be behind strict authentication; try agent-fetch directly |

---

<a name="中文"></a>
## 中文

### 功能

分享 URL 给 Claude 时，自动通过代理服务抓取完整内容并转为 Markdown。支持需要登录的页面（X/Twitter、Instagram 等），内置微信公众号专用抓取器。

### 路由规则

| URL 类型 | 抓取方式 | 原因 |
|----------|---------|------|
| 微信公众号 (`mp.weixin.qq.com`) | 内置 Playwright 抓取脚本 | 公众号有反爬，需要无头浏览器 |
| YouTube | 专用 YouTube skill | 视频内容有专用工具链 |
| 其他所有 URL | 代理级联：r.jina.ai → defuddle.md → agent-fetch → defuddle CLI | 免费、无需 API key |

### 前置条件

- [ ] 已安装 **Claude Code**
- [ ] **Python 3.8+** 及 `playwright`、`beautifulsoup4`（用于公众号抓取）
  ```bash
  pip install playwright beautifulsoup4 lxml
  playwright install chromium
  ```
- [ ] **curl**（macOS/Linux 自带）

### 安装

```bash
npx skills add joeseesun/markdown-proxy
```

### 使用示例

直接给 Claude 发 URL：

- "帮我读一下这篇文章：https://example.com/post"
- "抓取这条推文：https://x.com/user/status/123456"
- "读一下这篇公众号：https://mp.weixin.qq.com/s/abc123"

### 常见问题

| 问题 | 解决方法 |
|------|---------|
| 公众号抓取失败 | 运行 `playwright install chromium` 安装浏览器 |
| r.jina.ai 返回空内容 | 自动降级到 defuddle.md |
| 所有代理都失败 | URL 可能有严格认证限制，尝试直接用 agent-fetch |

---

## Credits

- [r.jina.ai](https://r.jina.ai) — Free URL-to-Markdown proxy by Jina AI
- [defuddle.md](https://defuddle.md) — Clean article extraction service
- [Playwright](https://playwright.dev/) — Browser automation for WeChat scraping

## 📱 关注作者

- **X (Twitter)**: [@vista8](https://x.com/vista8)
- **微信公众号「向阳乔木推荐看」**

<p align="center">
  <img src="https://github.com/joeseesun/terminal-boost/raw/main/assets/wechat-qr.jpg?raw=true" alt="向阳乔木推荐看公众号二维码" width="300">
</p>
