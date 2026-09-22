"""MkDocs 钩子：修正上游 README 自带的中英文切换行的链接与英文页相对资源路径。

1. 语言切换行修正：上游 README/README_EN 在仓库内互链（如中文页
   "简体中文 | [English](./README_EN.md)"），这些链接指向仓库内文件，在站点内会被
   mkdocs-static-i18n 解析成当前页自身形成死链。本钩子把其链接改写为站点内对应语言
   页面（URL 取自 page.file.alternates，自动适配语言路由与站点前缀），实现原地切换。

2. 英文页相对资源修正：mkdocs-static-i18n 对英文构建中的静态资源仍写到站点根路径
   （不带 en/ 前缀），MkDocs 又不会重写 HTML 原生 <img>/<a> 的相对路径，导致英文页
   （URL 位于 en/ 之下）上这些资源 404。本钩子把"按英文 URL 解析后不存在、但按对应
   中文页 URL 解析后存在"的相对路径改写为指向站点根资源的相对路径。已由 MkDocs
   正确重写过的 Markdown 链接不受影响（其按英文 URL 解析后已存在）。
"""

import os
import posixpath
import re
from urllib.parse import unquote, urlsplit

from mkdocs.utils import get_relative_url

# 工具首页：docs/<slug>/index.md 与 index.en.md
TOOL_INDEX_PATTERN = re.compile(r"([^/]+)/index(\.en)?\.md$")

# 上游切换行渲染后的两种形式（链接目标在站点内已失效，由本钩子改写 href）
ZH_LINE = re.compile(r'(<p>\s*English\s*\|\s*<a href=")[^"]*("[^>]*>\s*简体中文\s*</a>)')
EN_LINE = re.compile(r'(<p>\s*简体中文\s*\|\s*<a href=")[^"]*("[^>]*>\s*English\s*</a>)')

EN_PREFIX = "en/"

# 英文页中需要修正的 HTML 原生属性（MkDocs 不会重写它们）
HTML_ATTR_PATTERN = re.compile(
    r"(<(?:img|a|source|video|audio)\b[^>]*?\b(?:src|href)=(\"|'))([^\"']+)(\2)",
    flags=re.IGNORECASE,
)

NON_RELATIVE_PREFIXES = ("http://", "https://", "//", "/", "#", "data:", "mailto:", "javascript:")

# mkdocs-static-i18n 注入的 hreflang alternate 标签（仅这类同时含 rel="alternate" 与 hreflang；
# RSS 的 alternate 不带 hreflang，不受影响）
HREFLANG_ALTERNATE_PATTERN = re.compile(
    r'<link\b[^>]*\brel="alternate"[^>]*\bhreflang="[^"]*"[^>]*/?>',
    flags=re.IGNORECASE,
)


def _site_path_exists(site_dir: str, candidate: str) -> bool:
    full = os.path.join(site_dir, candidate)
    return os.path.isfile(full) or os.path.isdir(full)


def _asset_exists(config, candidate: str) -> bool:
    """资源是否可用：站点产物已生成，或 docs 源树中存在该文件。

    zh（默认语言）构建时资源尚未拷入 site_dir，必须回退检查 docs 源树；
    en 构建在 post_build 阶段执行，此时产物已齐备。
    """
    if _site_path_exists(str(config.site_dir), candidate):
        return True
    docs_candidate = os.path.join(str(config.docs_dir), candidate)
    return os.path.isfile(docs_candidate)


def _page_source_base(page) -> str:
    """页面内容的编写基准目录（相对 docs 根，即源 md 文件所在目录）。"""
    src_uri = (getattr(page.file, "src_uri", "") or getattr(page.file, "src_path", "")).replace("\\", "/")
    # 本地化首页（index.en.md 等）内容与默认语言文件同目录，去掉语言后缀再取目录。
    src_uri = re.sub(r"\.en\.md$", ".md", src_uri)
    return posixpath.dirname(src_uri)


def _fix_english_relative_resource(target: str, page, page_url: str, config) -> str | None:
    """返回改写后的目标；无需或无法修正时返回 None。"""
    if not target or target.startswith(NON_RELATIVE_PREFIXES):
        return None
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        return None
    clean = unquote(parsed.path)
    if not clean:
        return None

    # 按页面 URL 解析已存在，说明已被 MkDocs 正确重写或本来可用，保持原样。
    url_candidate = posixpath.normpath(posixpath.join(page_url, clean)).lstrip("/")
    if not url_candidate or _site_path_exists(str(config.site_dir), url_candidate):
        return None

    # 内容按源 md 文件所在目录编写；浏览器却按页面 URL（use_directory_urls 下多一层
    # 文件名目录）解析，导致相对资源 404。改按编写基准目录解析。
    # 另兜底尝试剥离路径中误写的 en/ 段（上游英文 README 引用不存在的英文资产目录）。
    en_free = re.sub(r"(^|/)en/", r"\1", clean, count=1)
    bases = [_page_source_base(page), page_url[len(EN_PREFIX):] if page_url.startswith(EN_PREFIX) else page_url]
    for base in bases:
        for candidate_path in dict.fromkeys([clean, en_free]):
            candidate = posixpath.normpath(posixpath.join(base, candidate_path)).lstrip("/")
            if candidate and _asset_exists(config, candidate):
                suffix = f"?{parsed.query}" if parsed.query else ""
                if parsed.fragment:
                    suffix += f"#{parsed.fragment}"
                return get_relative_url(candidate, page_url) + suffix
    return None


def fix_english_relative_resources(html: str, page, config: dict) -> str:
    page_url = page.url or ""

    def rewrite(match: re.Match) -> str:
        fixed = _fix_english_relative_resource(match.group(3), page, page_url, config)
        if fixed is None:
            return match.group(0)
        return f"{match.group(1)}{fixed}{match.group(4)}"

    return HTML_ATTR_PATTERN.sub(rewrite, html)


def on_page_content(html: str, page, config: dict, **kwargs) -> str:
    src_uri = (getattr(page.file, "src_uri", "") or getattr(page.file, "src_path", "")).replace("\\", "/")
    match = TOOL_INDEX_PATTERN.fullmatch(src_uri)
    if match:
        alternates = getattr(page.file, "alternates", None) or {}
        zh_file, en_file = alternates.get("zh"), alternates.get("en")
        # 无独立英文版（英文文件与当前为同一文件）时无需修正。
        if zh_file is not None and en_file is not None and en_file.src_uri != zh_file.src_uri:
            if match.group(2):  # 英文页：修正 "English | [简体中文](...)" 行
                zh_link = get_relative_url(zh_file.url, page.url)
                html, count = ZH_LINE.subn(rf"\g<1>{zh_link}\g<2>", html, count=1)
            else:  # 中文页：修正 "简体中文 | [English](...)" 行
                en_link = get_relative_url(en_file.url, page.url)
                html, count = EN_LINE.subn(rf"\g<1>{en_link}\g<2>", html, count=1)
            if count == 0:
                print(f"[warn] {src_uri}: 未匹配到上游语言切换行，跳过链接修正")

    html = fix_english_relative_resources(html, page, config)
    return html


def on_post_page(output: str, *, page, config: dict, **kwargs) -> str:
    """移除 <head> 里的 hreflang alternate 标签，修复语言切换跳首页的 bug。

    mkdocs-static-i18n 会按页面注入 <link rel="alternate" hreflang="...">，而
    Material 主题的脚本把它们误解为"多站点部署"：为每个语言前缀抓取
    sitemap.xml（MkDocs 不生成按语言的 sitemap，全部 404 → 空映射），并在点击
    落入其它语言前缀的链接时接管导航——映射为空即回退到该语言首页，表现为
    "切换语言后跳到首页"。移除后 Material 不再接管，instant 导航按页面内已
    改写正确的切换链接原地切换。
    """
    return HREFLANG_ALTERNATE_PATTERN.sub("", output)
