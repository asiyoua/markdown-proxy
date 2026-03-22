#!/usr/bin/env python3
"""Fetch Zhihu Zhuanlan article as Markdown using Playwright DOM extraction."""

import asyncio
import json
import sys
from pathlib import Path


PREFERRED_CHROMIUM_EXECUTABLES = [
    "/Applications/Tabbit Browser.app/Contents/MacOS/Tabbit Browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


EXTRACT_ARTICLE_JS = r"""
() => {
  const clean = (value) => (value || "")
    .replace(/\u00a0/g, " ")
    .replace(/[ \t]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

  const article = document.querySelector("article");
  if (!article) {
    return { error: "No article element found", url: location.href };
  }

  const header = article.querySelector("header.Post-Header");
  const contentRoot = article.querySelector(".Post-RichTextContainer");
  if (!contentRoot) {
    return { error: "No Post-RichTextContainer found", url: location.href };
  }

  const title = clean(
    header?.querySelector("h1")?.innerText ||
    document.querySelector("h1")?.innerText ||
    document.title ||
    ""
  );
  const author = clean(
    header?.querySelector('a[href*="/people/"]')?.innerText ||
    article.querySelector('a[href*="/people/"]')?.innerText ||
    article.querySelector('[class*="AuthorInfo"] a')?.innerText ||
    ""
  );
  const publishTime = clean(article.querySelector(".ContentItem-time")?.innerText || "");

  function inline(node) {
    if (node.nodeType === Node.TEXT_NODE) return node.textContent || "";
    if (node.nodeType !== Node.ELEMENT_NODE) return "";

    const el = node;
    const tag = el.tagName.toLowerCase();

    if (tag === "img") {
      const src =
        el.getAttribute("data-original") ||
        el.getAttribute("data-actualsrc") ||
        el.getAttribute("src") ||
        "";
      const alt = clean(el.getAttribute("alt") || "image");
      return src ? `![${alt}](${src})` : "";
    }

    if (tag === "br") return "\n";

    const body = Array.from(el.childNodes).map(inline).join("");
    const normalized = clean(body);

    if (!normalized && !body.includes("![")) return "";

    if (tag === "strong" || tag === "b") return normalized ? `**${normalized}**` : "";
    if (tag === "em" || tag === "i") return normalized ? `*${normalized}*` : "";
    if (tag === "code" && !el.closest("pre")) return normalized ? `\`${normalized}\`` : "";
    if (tag === "a") {
      const href = (el.getAttribute("href") || "").trim();
      const label = normalized || href;
      return href ? `[${label}](${href})` : label;
    }

    return body;
  }

  const blocks = [];
  const container = contentRoot.firstElementChild || contentRoot;

  for (const node of Array.from(container.children)) {
    const tag = node.tagName.toLowerCase();
    const body = Array.from(node.childNodes).map(inline).join("").trim();
    if (!body) continue;

    if (/^h[1-6]$/.test(tag)) {
      blocks.push(`${"#".repeat(Number(tag[1]))} ${clean(body)}`);
      continue;
    }

    if (tag === "blockquote") {
      blocks.push(
        body
          .split("\n")
          .map((line) => line.trim() ? `> ${clean(line)}` : "")
          .filter(Boolean)
          .join("\n")
      );
      continue;
    }

    if (tag === "figure") {
      blocks.push(body);
      continue;
    }

    if (tag === "pre") {
      blocks.push("```\n" + (node.innerText || "").trimEnd() + "\n```");
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
      blocks.push(items.length ? items.join("\n") : clean(body));
      continue;
    }

    blocks.push(body.includes("\n") ? body : clean(body));
  }

  return {
    title,
    author,
    publish_time: publishTime,
    content: blocks.join("\n\n"),
    url: location.href
  };
}
"""


def yaml_quote(value: str) -> str:
    return json.dumps(value or "", ensure_ascii=False)


def available_browser_candidates() -> list[str]:
    candidates = [path for path in PREFERRED_CHROMIUM_EXECUTABLES if Path(path).exists()]
    candidates.append("")
    return candidates


async def fetch_zhihu_article(url: str) -> dict:
    try:
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        from playwright.async_api import async_playwright
    except ImportError:
        return {"error": "playwright not installed. Run: pip install playwright && playwright install chromium"}

    last_error = None

    async with async_playwright() as playwright:
        for executable in available_browser_candidates():
            launch_kwargs = {"headless": True}
            if executable:
                launch_kwargs["executable_path"] = executable

            browser = None
            try:
                browser = await playwright.chromium.launch(**launch_kwargs)
                page = await browser.new_page(
                    viewport={"width": 1440, "height": 2200},
                    locale="zh-CN",
                )
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(2500)
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except PlaywrightTimeoutError:
                    pass

                result = await page.evaluate(EXTRACT_ARTICLE_JS)
                if isinstance(result, dict) and not result.get("error"):
                    result.setdefault("url", url)
                    if executable:
                        result["browser"] = executable
                    else:
                        result["browser"] = "playwright-chromium"
                    return result

                last_error = result.get("error") if isinstance(result, dict) else "Unexpected extraction result"
            except Exception as exc:
                last_error = str(exc)
            finally:
                if browser:
                    await browser.close()

    return {"error": last_error or "Failed to fetch Zhihu article", "url": url}


def format_as_markdown(result: dict) -> str:
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
    parts.append('source: "zhihu"')
    parts.append("---")
    parts.append("")
    if result.get("title"):
        parts.append(f"# {result['title']}")
        parts.append("")
    parts.append(result.get("content", ""))
    return "\n".join(parts)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: fetch_zhihu.py <zhihu_url> [--json]", file=sys.stderr)
        sys.exit(1)

    target_url = sys.argv[1]
    use_json = "--json" in sys.argv

    article = asyncio.run(fetch_zhihu_article(target_url))

    if use_json:
        print(json.dumps(article, ensure_ascii=False, indent=2))
    else:
        print(format_as_markdown(article))
