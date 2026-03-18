import os
from fastmcp import FastMCP
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, ProxyConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

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
    format: str = "markdown",  # "html" | "markdown" | "fit"
    max_length: int = 5000,
    start_index: int = 0,
    bypass_cache: bool = False,
) -> dict:
    """从互联网上抓取一个 URL 并将其内容提取。

    Args:
        url: 要抓取的 URL
        format: 返回格式 - "html"(原始 HTML) | "markdown"(完整 markdown) | "fit"(过滤后的精简 markdown)
        max_length: 返回的最大字符数 (默认：5000)
        start_index: 从此字符索引开始提取内容 (默认：0)
        bypass_cache: 绕过缓存强制重新抓取 (默认：false)
    """
    # 配置 markdown 生成器
    if format == "fit":
        markdown_generator = DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(threshold=0.48, threshold_type="fixed")
        )
    else:
        markdown_generator = None

    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS if bypass_cache else CacheMode.ENABLED,
        remove_overlay_elements=True,
        verbose=False,
        markdown_generator=markdown_generator,
    )
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=url, config=run_config)
    if not result.success:
        raise RuntimeError(f"Crawl failed: {result.error_message}")

    # 根据 format 选择内容
    if format == "html":
        content = result.html
    elif format == "fit":
        content = result.markdown.fit_markdown or result.markdown.raw_markdown
    else:  # markdown
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
