"""Generate the aggregated "whats-new" page from each tool repo's GitCode Releases.

Runs as part of readthedocs/scripts/build_docs.py (pre_build on Read the Docs),
and can also be run standalone to refresh the page and the fallback cache:

    python3 readthedocs/scripts/fetch_release_notes.py

Data source: https://gitcode.com/api/v5/repos/Ascend/{repo}/releases
If the API is unreachable, the last successfully fetched data (committed as
release_notes_cache.json) is used instead, so builds keep working offline.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = ROOT / "readthedocs" / "docs"
OUTPUT_PAGE = DOCS_ROOT / "whats-new" / "index.md"
CACHE_FILE = Path(__file__).with_name("release_notes_cache.json")
FEATURE_DOCS_FILE = Path(__file__).with_name("release_feature_docs.json")

API_URL = "https://gitcode.com/api/v5/repos/Ascend/{slug}/releases?per_page=20"
REPO_WEB_URL = "https://gitcode.com/Ascend/{slug}"
REQUEST_TIMEOUT = 20

TOOLS = [
    {"slug": "msprof", "title": "msProf", "max_releases": 2},
    {"slug": "mspti", "title": "MSPTI", "max_releases": 2},
    {"slug": "msmonitor", "title": "msMonitor", "max_releases": 2},
    {"slug": "msprof-analyze", "title": "msprof-analyze", "max_releases": 2},
    {"slug": "msinsight", "title": "MindStudio Insight", "max_releases": 2},
    {"slug": "msagent", "title": "msAgent", "max_releases": 1, "note": "msAgent 按周发布，此处仅展示最近一期。"},
]

ADDITIONS_START = re.compile(r"^#*\s*一[、\s　]*新增说明\s*$", re.MULTILINE)
ADDITIONS_END = re.compile(r"^#*\s*二[、\s　]*删除说明", re.MULTILINE)
ITEM_LINE = re.compile(r"^\s*(?:\d+\s*[.、．)]|[-*•])\s*(.+?)\s*$")
HIGHLIGHT_PREFIX = re.compile(r"^亮点\s*\d*\s*[：:.、]?\s*")
VERSION_RE = re.compile(r"(\d+\.\d+\.\d+(?:[.-]?(?:alpha|beta|rc)\.?\d+)*)")
EMPTY_MARKS = {"", "无", "无。", "NONE", "None", "none", "N/A"}


def fetch_releases(slug: str) -> list[dict]:
    request = urllib.request.Request(
        API_URL.format(slug=slug),
        headers={"User-Agent": "mindstudio-profiler-docs whats-new generator"},
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        payload = json.load(response)
    if not isinstance(payload, list):
        raise ValueError(f"unexpected API payload type: {type(payload).__name__}")
    return [
        {
            "tag_name": item.get("tag_name") or "",
            "name": item.get("name") or "",
            "created_at": item.get("created_at") or "",
            "body": item.get("body") or "",
        }
        for item in payload
    ]


def extract_items(text: str) -> list[str]:
    """Collect numbered/bulleted lines; stop at the first non-item line once started."""
    items: list[str] = []
    for line in text.splitlines():
        match = ITEM_LINE.match(line)
        if match:
            value = HIGHLIGHT_PREFIX.sub("", match.group(1).strip())
            if value not in EMPTY_MARKS:
                items.append(value)
        elif line.strip() and items:
            break
    return items


def extract_section_items(section: str) -> list[str]:
    """Items inside a 新增说明 section: numbered/bulleted lines, or plain lines as fallback."""
    items = extract_items(section)
    if items:
        return items
    plain: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped or stripped in EMPTY_MARKS:
            if plain:
                break
            continue
        if stripped.startswith("#"):
            break
        plain.append(stripped.lstrip("#").strip())
    return plain


def parse_additions(body: str) -> list[str]:
    """Extract new-feature items from a release body.

    Supports the two formats used across the tool repos:
    - "核心亮点如下：" followed by bullets (recent stable releases, msAgent weekly)
    - six-section template with a "一 新增说明" section (older releases)
    """
    lines = body.splitlines()
    for index, line in enumerate(lines):
        if "核心亮点" in line:
            items = extract_items("\n".join(lines[index + 1:]))
            if items:
                return items
    match = ADDITIONS_START.search(body)
    if match:
        section = body[match.end():]
        end = ADDITIONS_END.search(section)
        if end:
            section = section[: end.start()]
        return extract_section_items(section)
    return []


def release_date(release: dict) -> datetime:
    try:
        return datetime.fromisoformat(release["created_at"])
    except ValueError:
        return datetime.min


def release_title(release: dict) -> str:
    name = release["name"].strip()
    if name and name != release["tag_name"]:
        return name
    # Tag-only title, e.g. tag_MindStudio_26.1.3_Weekly_20260916 -> 26.1.3 Weekly 20260916
    tag = release["tag_name"]
    tag = re.sub(r"^tag_MindStudio[_-]?", "", tag)
    return tag.replace("_", " ").strip() or release["tag_name"]


def release_version(release: dict) -> str:
    """Short version extracted from the tag, e.g. tag_MindStudio_26.1.0.B100_002 -> 26.1.0."""
    match = VERSION_RE.search(release["tag_name"])
    if match:
        return match.group(1)
    return release_title(release)


def release_url(slug: str, release: dict) -> str:
    return f"{REPO_WEB_URL.format(slug=slug)}/releases/{release['tag_name']}"


def tool_anchor(title: str) -> str:
    """Anchor generated by the MkDocs TOC for a tool section heading."""
    return title.lower().replace(" ", "-")


def select_releases(tool: dict, releases: list[dict]) -> list[tuple[dict, list[str]]]:
    ordered = sorted(releases, key=release_date, reverse=True)
    picked: list[tuple[dict, list[str]]] = []
    for release in ordered:
        additions = parse_additions(release["body"])
        if additions:
            picked.append((release, additions))
        if len(picked) >= tool["max_releases"]:
            break
    if not picked and ordered:
        picked.append((ordered[0], []))
    return picked


def load_feature_docs() -> dict[str, list[dict]]:
    """Load the feature → in-site doc mapping; missing/broken config degrades to no links."""
    if not FEATURE_DOCS_FILE.exists():
        return {}
    try:
        payload = json.loads(FEATURE_DOCS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[whats-new] WARNING: feature docs config unusable ({exc}); links disabled", file=sys.stderr)
        return {}
    return {
        slug: [rule for rule in rules if isinstance(rule, dict) and rule.get("match") and rule.get("doc")]
        for slug, rules in payload.items()
        if isinstance(rules, list)
    }


def keyword_pattern(keyword: str) -> re.Pattern[str]:
    """把映射表里的关键字编译成匹配式。

    ASCII 关键字按「词边界」匹配：`rank_id`、`ranking` 这类标识符/单词不会被 `rank` 命中，
    但仍能命中 `--rank-list` 这类命令行选项，避免给无关条目挂上错误的用法说明；
    宁可漏挂提示，也不误导。中文等非 ASCII 关键字没有词边界概念，仍按子串匹配。
    """
    if keyword.isascii():
        return re.compile(
            rf"(?<![0-9A-Za-z_]){re.escape(keyword)}(?![0-9A-Za-z_])", re.IGNORECASE
        )
    return re.compile(re.escape(keyword), re.IGNORECASE)


def render_feature_item(slug: str, version: str, item: str, feature_docs: dict[str, list[dict]]) -> str:
    rule = None
    for candidate in feature_docs.get(slug, []):
        rule_version = candidate.get("version")
        if rule_version and rule_version != version:
            continue
        if keyword_pattern(candidate["match"]).search(item):
            rule = candidate
            break
    if rule is None:
        return f"- {item}"

    doc_url = None
    if rule.get("doc"):
        doc = DOCS_ROOT / rule["doc"]
        if doc.is_file():
            doc_url = f"../{rule['doc']}"
        else:
            print(
                f"[whats-new] WARNING: feature doc missing for {slug}: {rule['doc']} "
                f"(matched by '{rule['match']}'); rendering item without link",
                file=sys.stderr,
            )

    usage = rule.get("usage", "").strip()
    if usage:
        lines = [f"- {item}", f"    - 使用：{usage}"]
        if doc_url:
            lines[1] += f"（[详见文档]({doc_url})）"
        return "\n".join(lines)
    if doc_url:
        return f"- {item}（[使用说明]({doc_url})）"
    return f"- {item}"


def render_summary_table(repos_data: dict[str, list[dict]]) -> list[str]:
    lines = [
        "| 工具 | 最新版本 | 发布日期 |",
        "| --- | --- | --- |",
    ]
    for tool in TOOLS:
        picked = select_releases(tool, repos_data.get(tool["slug"], []))
        if picked:
            release, _ = picked[0]
            version_cell = f"[{release_version(release)}]({release_url(tool['slug'], release)})"
            date_cell = release["created_at"][:10]
        else:
            version_cell, date_cell = "—", "—"
        lines.append(f"| [{tool['title']}](#{tool_anchor(tool['title'])}) | {version_cell} | {date_cell} |")
    lines.append("")
    return lines


def render_tool_section(
    tool: dict, releases: list[dict], feature_docs: dict[str, list[dict]]
) -> list[str]:
    lines = [f"## {tool['title']}", ""]
    if tool.get("note"):
        lines += [f"*{tool['note']}*", ""]
    if not releases:
        lines += [
            f"版本信息暂未收录，请前往[完整发布历史]({REPO_WEB_URL.format(slug=tool['slug'])}/releases)查看。",
            "",
        ]
        return lines

    for release, additions in select_releases(tool, releases):
        date_text = release["created_at"][:10]
        version = release_version(release)
        lines += [
            f"### [{version}]({release_url(tool['slug'], release)}) · {date_text}",
            "",
        ]
        if additions:
            lines += [
                render_feature_item(tool["slug"], version, item, feature_docs)
                for item in additions
            ]
        else:
            lines += [f"本版本以变更与缺陷修复为主，详见[完整发布说明]({release_url(tool['slug'], release)})。"]
        lines.append("")

    lines += [
        f"[完整发布历史 →]({REPO_WEB_URL.format(slug=tool['slug'])}/releases)",
        "",
    ]
    return lines


def render_page(repos_data: dict[str, list[dict]], feature_docs: dict[str, list[dict]]) -> str:
    lines = [
        "---",
        "title: 新特性",
        "hide:",
        "  - navigation",
        "---",
        "",
        "# 新特性",
        "",
        "本页汇总各工具最新版本的新增特性。已收录的特性在条目下附有「使用」说明（含命令参数、接口调用或操作路径），"
        "点击「详见文档」可查看完整使用文档；点击版本号可查看对应版本的完整发布说明。",
        "",
    ]
    lines += render_summary_table(repos_data)
    for tool in TOOLS:
        lines += render_tool_section(tool, repos_data.get(tool["slug"], []), feature_docs)
    return "\n".join(lines)


def load_cache() -> dict[str, list[dict]]:
    if not CACHE_FILE.exists():
        return {}
    try:
        payload = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload.get("repos", {})


def save_cache(repos_data: dict[str, list[dict]]) -> None:
    payload = {
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "repos": repos_data,
    }
    CACHE_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    cache = load_cache()
    repos_data: dict[str, list[dict]] = {}
    fetched_any = False
    for tool in TOOLS:
        slug = tool["slug"]
        try:
            repos_data[slug] = fetch_releases(slug)
            fetched_any = True
            print(f"[whats-new] fetched {slug}: {len(repos_data[slug])} releases")
        except Exception as exc:  # noqa: BLE001 - any failure falls back to cache
            if slug in cache:
                print(f"[whats-new] WARNING: {slug} fetch failed ({exc}); using cached data", file=sys.stderr)
                repos_data[slug] = cache[slug]
            else:
                print(f"[whats-new] ERROR: {slug} fetch failed ({exc}); no cached data", file=sys.stderr)
                repos_data[slug] = []

    OUTPUT_PAGE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PAGE.write_text(render_page(repos_data, load_feature_docs()), encoding="utf-8")
    print(f"[whats-new] wrote {OUTPUT_PAGE.relative_to(ROOT)}")

    if fetched_any:
        save_cache(repos_data)
        print(f"[whats-new] updated cache {CACHE_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
