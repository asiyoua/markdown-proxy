---
name: markdown-proxy
description: |
  Fetch any URL as clean Markdown via proxy services (r.jina.ai / defuddle.md) or built-in scripts.
  Works with login-required pages like X/Twitter, WeChat 公众号, Instagram, etc.
  Use this BEFORE agent-fetch, defuddle CLI, or WebFetch when the URL might need authentication or when you want the cleanest markdown output.
  Triggers on any URL the user shares, "fetch this", "read this link", "get content from".
  Especially effective for X/Twitter posts, WeChat 公众号 articles, and login-walled pages.
---

# Markdown Proxy - URL to Markdown via Proxy Services

Fetch any URL as clean Markdown using web proxy services or built-in scripts. Works with login-required pages that local tools cannot access.

## URL 路由规则（先判断再执行）

收到 URL 后，先判断类型，不同类型走不同通道：

| URL 特征 | 路由到 | 原因 |
|----------|--------|------|
| `mp.weixin.qq.com` | 内置 `scripts/fetch_weixin.py` | 公众号有反爬，需 Playwright 抓取 |
| `youtube.com` / `youtu.be` | `yt-search-download` skill | YouTube 有专用工具链 |
| 其他所有 URL | 本 skill 的代理服务流程（见下方） |  |

## 代理服务优先级

| 优先级 | 服务 | URL 模式 | 优势 |
|--------|------|----------|------|
| 1 | **r.jina.ai** | `https://r.jina.ai/{url}` | 内容更完整，保留图片链接，覆盖面广 |
| 2 | **defuddle.md** | `https://defuddle.md/{url}` | 输出更干净，带 YAML frontmatter |
| 3 | `agent-fetch` | npx agent-fetch | 本地工具，无需网络代理 |
| 4 | `defuddle` CLI | defuddle parse | 本地 CLI，适合普通网页 |

## Workflow

### Step 0: URL 类型判断

```
if URL contains "mp.weixin.qq.com":
    → Step A: 公众号抓取
    → 结束

if URL contains "youtube.com" or "youtu.be":
    → 调用 yt-search-download skill
    → 结束

else:
    → 继续 Step 1
```

### Step A: 公众号文章抓取（内置）

使用本 skill 内置的 Playwright 脚本：

```bash
python3 /path/to/this/skill/scripts/fetch_weixin.py "WEIXIN_URL"
```

脚本路径（绝对）：`~/.claude/skills/markdown-proxy/scripts/fetch_weixin.py`

依赖：`playwright`（已安装在 conda 环境）、`beautifulsoup4`、`lxml`

输出格式：YAML frontmatter（title, author, date, url）+ Markdown 正文

如果脚本执行失败，尝试用代理服务（Step 1-2）作为备选。

### Step 1: 优先用 r.jina.ai

```bash
curl -sL "https://r.jina.ai/{original_url}" 2>/dev/null
```

如果返回非空且包含实际内容，使用此结果。

### Step 2: 如果 Jina 失败，用 defuddle.md

```bash
curl -sL "https://defuddle.md/{original_url}" 2>/dev/null
```

### Step 3: 如果两个代理都失败，回退本地工具

```bash
npx agent-fetch "{original_url}" --json
# 或
defuddle parse "{original_url}" -m -j
```

### Step 4: 展示内容

根据用户请求展示：
- 标题 / 作者 / 来源
- 内容摘要或全文
- 如需保存，写入知识库对应目录

## Examples

### X/Twitter 帖子或长文
```bash
curl -sL "https://r.jina.ai/https://x.com/username/status/1234567890"
```

### 普通网页文章
```bash
curl -sL "https://r.jina.ai/https://example.com/article"
```

### 公众号文章（内置脚本）
```bash
python3 ~/.claude/skills/markdown-proxy/scripts/fetch_weixin.py "https://mp.weixin.qq.com/s/abc123"
```

## Notes

- r.jina.ai 和 defuddle.md 均免费、无需 API key
- r.jina.ai 返回 Title/URL/Published Time 头信息 + Markdown 正文
- defuddle.md 返回 YAML frontmatter（title, author, site, word_count）+ Markdown 正文
- 对于超长内容，可用 `| head -n 200` 先预览
- 公众号文章使用内置 fetch_weixin.py 脚本（Playwright + BeautifulSoup）
- fetch_weixin.py 支持 `--json` 参数输出 JSON 格式
