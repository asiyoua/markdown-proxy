#!/usr/bin/env python3
"""Fetch WeChat (公众号) article as Markdown using Playwright DOM extraction."""

import asyncio
import json
import sys
from pathlib import Path


EXTRACT_ARTICLE_JS = r"""
() => {
  const clean = (value) => (value || "")
    .replace(/\u00a0/g, " ")
    .replace(/[ \t]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

  const q = (selector) => document.querySelector(selector);
  const text = (el) => el ? clean(el.innerText) : "";
  const currentUrl = location.href;

  const title = text(q("#activity-name")) || document.title || "";
  const author = text(q("#js_author_name")) || text(q(".rich_media_meta_text")) || "";
  const publishTime = text(q("#publish_time")) || "";
  const content = q("#js_content");

  if (!content) {
    return {
      error: "Could not find article content (#js_content)",
      title,
      author,
      publish_time: publishTime,
      url: currentUrl
    };
  }

  const bodyText = text(document.body);
  if (!title && bodyText.includes("环境异常") && bodyText.includes("完成验证后即可继续访问")) {
    return {
      error: "WeChat returned a verification page (环境异常). Open the article in a verified browser session and retry.",
      url: currentUrl
    };
  }

  function inline(node) {
    if (node.nodeType === Node.TEXT_NODE) return node.textContent || "";
    if (node.nodeType !== Node.ELEMENT_NODE) return "";

    const el = node;
    const tag = el.tagName.toLowerCase();

    if (tag === "img") {
      const src = el.getAttribute("data-src") || el.getAttribute("src") || "";
      const alt = clean(el.getAttribute("alt") || "image");
      return src ? `![${alt}](${src})` : "";
    }

    if (tag === "br") return "\n";

    const body = Array.from(el.childNodes).map(inline).join("");
    const normalized = clean(body);

    if (!normalized && !body.includes("![")) return "";

    if (tag === "strong" || tag === "b") return normalized ? `**${normalized}**` : "";
    if (tag === "em" || tag === "i") return normalized ? `*${normalized}*` : "";
    if (tag === "code") return normalized ? `\`${normalized}\`` : "";
    if (tag === "a") {
      const href = (el.getAttribute("href") || "").trim();
      const label = normalized || href;
      return href ? `[${label}](${href})` : label;
    }

    return body;
  }

  const lines = [];
  const images = Array.from(
    new Set(
      Array.from(content.querySelectorAll("img"))
        .map((img) => img.getAttribute("data-src") || img.getAttribute("src") || "")
        .filter(Boolean)
    )
  );

  for (const node of Array.from(content.children)) {
    const tag = node.tagName.toLowerCase();
    const body = Array.from(node.childNodes).map(inline).join("").trim();
    if (!body) continue;

    if (/^h[1-6]$/.test(tag)) {
      lines.push(`${"#".repeat(Number(tag[1]))} ${clean(body)}`);
      continue;
    }

    if (tag === "blockquote") {
      lines.push(
        body
          .split("\n")
          .map((line) => line.trim() ? `> ${clean(line)}` : "")
          .filter(Boolean)
          .join("\n")
      );
      continue;
    }

    if (tag === "ul" || tag === "ol") {
      const items = Array.from(node.querySelectorAll(":scope > li"))
        .map((li, idx) => {
          const itemBody = clean(Array.from(li.childNodes).map(inline).join(""));
          if (!itemBody) return "";
          return tag === "ol" ? `${idx + 1}. ${itemBody}` : `- ${itemBody}`;
        })
        .filter(Boolean);

      if (items.length) {
        lines.push(items.join("\n"));
      } else {
        lines.push(clean(body));
      }
      continue;
    }

    if (body.includes("![")) {
      lines.push(body);
      continue;
    }

    lines.push(body.includes("\n") ? body : clean(body));
  }

  return {
    title,
    author,
    publish_time: publishTime,
    content: lines.join("\n\n"),
    images,
    url: currentUrl
  };
}
"""

PREFERRED_CHROMIUM_EXECUTABLES = [
    "/Applications/Tabbit Browser.app/Contents/MacOS/Tabbit Browser",
]


def yaml_quote(value: str) -> str:
    """Quote YAML string safely using JSON escaping rules."""
    return json.dumps(value or "", ensure_ascii=False)


def resolve_browser_executable() -> str | None:
    """Prefer a locally installed Chromium-based browser before bundled Chromium."""
    for candidate in PREFERRED_CHROMIUM_EXECUTABLES:
        if Path(candidate).exists():
            return candidate
    return None


async def fetch_weixin_article(url: str) -> dict:
    """Fetch and parse a WeChat article into Markdown-compatible structure."""
    try:
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        from playwright.async_api import async_playwright
    except ImportError:
        return {"error": "playwright not installed. Run: pip install playwright && playwright install chromium"}

    async with async_playwright() as playwright:
        launch_kwargs = {"headless": True}
        browser_executable = resolve_browser_executable()
        if browser_executable:
            launch_kwargs["executable_path"] = browser_executable

        browser = await playwright.chromium.launch(**launch_kwargs)
        page = await browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 2200},
            locale="zh-CN",
        )

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(2500)
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except PlaywrightTimeoutError:
                pass

            try:
                await page.wait_for_selector("#js_content, .weui-msg__title", timeout=20000)
            except PlaywrightTimeoutError:
                return {"error": "Failed to load WeChat article body in time", "url": url}

            result = await page.evaluate(EXTRACT_ARTICLE_JS)
        except Exception as exc:
            return {"error": f"Failed to load page: {exc}", "url": url}
        finally:
            await browser.close()

    if not isinstance(result, dict):
        return {"error": "Unexpected extraction result", "url": url}

    result.setdefault("url", url)
    return result


def format_as_markdown(result: dict) -> str:
    """Format result dict as a Markdown document."""
    if "error" in result:
        return f"Error: {result['error']}"

    parts = ["---"]
    if result.get("title"):
        parts.append(f"title: {yaml_quote(result['title'])}")
    if result.get("author"):
        parts.append(f"author: {yaml_quote(result['author'])}")
    if result.get("publish_time"):
        parts.append(f"date: {yaml_quote(result['publish_time'])}")
    parts.append(f"url: {yaml_quote(result.get('url', ''))}")
    parts.append('source: "wechat"')
    parts.append("---")
    parts.append("")
    if result.get("title"):
        parts.append(f"# {result['title']}")
        parts.append("")
    parts.append(result.get("content", ""))
    return "\n".join(parts)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: fetch_weixin.py <weixin_url> [--json]", file=sys.stderr)
        sys.exit(1)

    target_url = sys.argv[1]
    use_json = "--json" in sys.argv

    article = asyncio.run(fetch_weixin_article(target_url))

    if use_json:
        print(json.dumps(article, ensure_ascii=False, indent=2))
    else:
        print(format_as_markdown(article))
