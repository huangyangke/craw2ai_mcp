import os
from fastmcp import FastMCP
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, ProxyConfig
from crawl4ai.async_logger import AsyncLogger

mcp = FastMCP("craw2ai", instructions="Web scraping server powered by crawl4ai")

# Get proxy from environment variables
proxy_url = os.getenv("https_proxy") or os.getenv("http_proxy")
proxy_config = None
if proxy_url:
    # ProxyConfig expects full URL like "http://127.0.0.1:7890"
    proxy_config = ProxyConfig(
        server=proxy_url,
        username=os.getenv("PROXY_USERNAME"),
        password=os.getenv("PROXY_PASSWORD"),
    )

browser_config = BrowserConfig(
    headless=True,
    java_script_enabled=True,
    verbose=False,
    proxy_config=proxy_config,
)


@mcp.tool
async def fetch(
    url: str,
    max_length: int = 5000,
    start_index: int = 0,
    raw: bool = False,
    bypass_cache: bool = False,
) -> dict:
    """从互联网上抓取一个 URL 并将其内容作为 markdown 提取。"""
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS if bypass_cache else CacheMode.ENABLED,
        remove_overlay_elements=True,
        verbose=False,
    )
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=url, config=run_config)
    if not result.success:
        raise RuntimeError(f"Crawl failed: {result.error_message}")

    if raw:
        content = result.html
    else:
        content = result.markdown.raw_markdown

    # Apply length limiting
    content = content[start_index:start_index + max_length]

    return {
        "title": result.metadata.get("title", ""),
        "content": content,
    }


@mcp.tool
async def fetch_links(url: str) -> dict:
    """抓取 URL 并返回内部和外部链接。"""
    run_config = CrawlerRunConfig(cache_mode=CacheMode.ENABLED, verbose=False)
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=url, config=run_config)
    if not result.success:
        raise RuntimeError(f"Crawl failed: {result.error_message}")
    return {
        "internal": [l["href"] for l in result.links.get("internal", [])],
        "external": [l["href"] for l in result.links.get("external", [])],
    }


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8143)
