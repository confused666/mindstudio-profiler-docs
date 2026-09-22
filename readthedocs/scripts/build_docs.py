from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = ROOT / "readthedocs" / "docs"
SHARED_ASSET_ROOT = DOCS_ROOT / "assets" / "community"


TOOLS = [
    {
        "slug": "msinsight",
        "title": "MindStudio Insight",
        "branch": "master",
        "summary": "可视化性能分析工具，覆盖安装、快速上手、基础操作、调优指引与开发者文档。",
        "repo": ROOT / "msinsight",
        "source_subdir": "docs/zh",
        "repo_readme": "README.md",
        "entry_points": [
            ("总体概览", "source/user_guide/overview.md"),
            ("安装指南", "source/user_guide/mindstudio_insight_install_guide.md"),
            ("快速上手", "source/user_guide/quick_start/system_tuning_quick_start.md"),
            ("基本操作", "source/user_guide/basic_operations.md"),
            ("开发者指南", "source/developer_guide/development_guide.md"),
        ],
    },
    {
        "slug": "msagent",
        "title": "msAgent",
        "branch": "master",
        "summary": "面向 Ascend NPU 场景的性能问题定位 Agent，提供性能分析与归因辅助能力。",
        "repo": ROOT / "msagent",
        "source_subdir": "docs/zh",
        "repo_readme": "README.md",
        "entry_points": [
            ("Profiler", "source/agent_guide/profiler.md"),
            ("Minos", "source/agent_guide/minos.md"),
            ("快速上手", "source/quick_start/msagent_quick_start.md"),
            ("安装指南", "source/install_guide/msagent_install_guide.md"),
            ("配置与扩展", "source/user_guide/configuration-and-extension.md"),
        ],
        "display_dir_whitelist": {
            "agent_guide",
            "development_guide",
            "install_guide",
            "quick_start",
            "example",
            "support",
        },
    },
    {
        "slug": "msprof",
        "title": "msprof",
        "branch": "master",
        "summary": "性能数据采集与解析工具，覆盖安装、数据文件、解析能力和附录说明。",
        "repo": ROOT / "msprof",
        "source_subdir": "docs/zh",
        "repo_readme": "README.md",
        "entry_points": [
            ("解析工具说明", "source/user_guide/msprof_parsing_instruct.md"),
            ("性能数据文件参考", "source/user_guide/profile_data_file_references.md"),
            ("扩展功能", "source/user_guide/extended_functions.md"),
        ],
    },
    {
        "slug": "mspti",
        "title": "mspti",
        "branch": "master",
        "summary": "Profiling API 工具，包含总体介绍、安装指南、C API 和 Python API 文档。",
        "repo": ROOT / "mspti",
        "source_subdir": "docs/zh",
        "repo_readme": "README.md",
        "entry_points": [
            ("用户指南", "source/user_guide/mspti_user_guide.md"),
            ("样例指南", "source/user_guide/samples_guide.md"),
            ("Python API", "source/user_guide/python_api.md"),
        ],
    },
    {
        "slug": "msmonitor",
        "title": "msmonitor",
        "branch": "master",
        "summary": "在线监控与采集工具，覆盖安装、NPU 监控、Trace、Dyno 与 FAQ。",
        "repo": ROOT / "msmonitor",
        "source_subdir": "docs/zh",
        "repo_readme": "README.md",
        "entry_points": [
            ("NPU 监控", "source/user_guide/npumonitor_instruct.md"),
            ("NPUTrace", "source/user_guide/nputrace_instruct.md"),
            ("Dyno", "source/user_guide/dyno_instruct.md"),
            ("MindSpore 适配", "source/user_guide/mindspore_adapter_instruct.md"),
        ],
    },
    {
        "slug": "msprof-analyze",
        "title": "msprof-analyze",
        "branch": "master",
        "summary": "性能分析工具，覆盖快速上手、安装、专家建议、性能对比与集群分析能力。",
        "repo": ROOT / "msprof-analyze",
        "source_subdir": "docs/zh",
        "repo_readme": "README.md",
        "entry_points": [
            ("快速上手", "source/getting_started/quick_start.md"),
            ("安装指南", "source/getting_started/install_guide.md"),
            ("专家建议", "source/user_guide/advisor_instruct.md"),
            ("性能对比", "source/user_guide/compare_tool_instruct.md"),
            ("集群分析", "source/user_guide/cluster_analyse_instruct.md"),
            ("高级特性", "source/advanced_features/index.md"),
        ],
    },
]

EXCLUDED_NAMES = {
    "legal",
    "contributing",
    "contributed",
    "contributed.md",
    "contributing.md",
    "security_statement.md",
}

NON_NAV_NAMES = {
    "figures",
    "public_sys-resources",
    "public_sys_resources",
}

NAV_ORDER = [
    "index.md",
    "quick_start.md",
    "getting_started",
    "install_guide.md",
    "user_guide",
    "user-guide",
    "c_api",
    "python_api",
    "advanced_features",
    "advanced-features",
    "design",
    "desgin",
    "release_notes.md",
    "dir_structure.md",
]

DEFAULT_DISPLAY_DIR_WHITELIST = {
    "getting_started",
    "user_guide",
    "advanced_features",
    "best_practices",
    "c_api",
    "python_api",
    "figures"
}

DEFAULT_DISPLAY_FILE_WHITELIST = {
    "release_notes.md",
    "faq.md",
}

SHARED_ASSET_EXPORTS = {
    "officialAccount.jpg": {
        "repo": ROOT / "msinsight",
        "branch": "master",
        "repo_path": "docs/zh/user_guide/figures/readme/officialAccount.jpg",
    },
}

BROKEN_SHARED_ASSET_PATTERNS = {
    re.compile(r"https://raw\.gitcode\.com/[^\"'\s)]+/officialAccount\.(?:png|jpg)", re.IGNORECASE): "officialAccount.jpg",
}

GITHUB_BLOB_IMAGE_PATTERN = re.compile(
    r"^https://github\.com/([^/\s]+)/([^/\s]+)/blob/([^/\s]+)/(.+\.(?:png|jpg|jpeg|gif|svg|webp))$",
    re.IGNORECASE,
)


def run_git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True)


def relative_asset_path(from_page: Path, asset_name: str) -> str:
    asset_path = SHARED_ASSET_ROOT / asset_name
    return Path(os.path.relpath(asset_path, from_page.parent)).as_posix()


def rewrite_shared_asset_links(content: str, page_path: Path) -> str:
    rewritten = content
    for pattern, asset_name in BROKEN_SHARED_ASSET_PATTERNS.items():
        rewritten = pattern.sub(relative_asset_path(page_path, asset_name), rewritten)
    return rewritten


def normalize_external_image_url(target: str) -> str:
    match = re.match(r"^(.*?)([?#].*)?$", target)
    if not match:
        return target

    base_target = match.group(1)
    suffix = match.group(2) or ""
    github_match = GITHUB_BLOB_IMAGE_PATTERN.match(base_target)
    if not github_match:
        return target

    owner, repo, branch, asset_path = github_match.groups()
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{asset_path}{suffix}"


def rewrite_external_image_links(content: str) -> str:
    rewritten = re.sub(
        r"(<img\b[^>]*\bsrc=[\"'])([^\"']+)([\"'])",
        lambda match: f"{match.group(1)}{normalize_external_image_url(match.group(2))}{match.group(3)}",
        content,
        flags=re.IGNORECASE,
    )
    rewritten = re.sub(
        r"(!\[[^\]]*]\()([^)]+)(\))",
        lambda match: f"{match.group(1)}{normalize_external_image_url(match.group(2))}{match.group(3)}",
        rewritten,
    )
    return rewritten


def upstream_file_exists(repo: Path, branch: str, path: str) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"origin/{branch}:{path}"],
        check=False,
        capture_output=True,
    )
    return completed.returncode == 0


@lru_cache(maxsize=None)
def upstream_path_exists(repo: Path, branch: str, repo_path: str) -> bool:
    """判断路径在上游分支中是否存在。

    必须基于 origin/{branch} 判断：子模块工作区可能停留在旧提交，而导出内容取自
    origin/{branch}，只看工作区会把「上游其实存在」的链接误判为死链（进而留成 404）。
    """
    if upstream_file_exists(repo, branch, repo_path):
        return True
    return (repo / repo_path).exists()


def export_shared_assets() -> None:
    for asset_name, asset in SHARED_ASSET_EXPORTS.items():
        try:
            export_binary_file(
                asset["repo"],
                asset["branch"],
                asset["repo_path"],
                SHARED_ASSET_ROOT / asset_name,
            )
        except Exception as error:
            print(f"[warn] 共享资源 {asset_name} 导出失败，跳过: {error}")


def export_latest_branch(repo: Path, branch: str, source_subdir: str, destination: Path) -> None:
    run_git(repo, "fetch", "origin", branch)

    with tempfile.TemporaryDirectory() as temp_dir:
        archive_path = Path(temp_dir) / "source.tar"
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "archive",
                "--format=tar",
                "--output",
                str(archive_path),
                f"origin/{branch}",
                source_subdir,
            ],
            check=True,
        )

        extracted_root = Path(temp_dir) / "exported"
        extracted_root.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive_path) as archive:
            # Python 3.14 changes the default extraction filter; prefer a safe mode now.
            try:
                archive.extractall(extracted_root, filter="data")
            except TypeError:
                archive.extractall(extracted_root)

        exported_source = extracted_root / source_subdir
        staging = Path(temp_dir) / "staging"
        shutil.copytree(exported_source, staging)
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(staging, destination)


def export_text_file(repo: Path, branch: str, repo_path: str) -> str:
    candidates = [f"origin/{branch}:{repo_path}", f"HEAD:{repo_path}"]
    for candidate in candidates:
        completed = subprocess.run(
            ["git", "-C", str(repo), "show", candidate],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if completed.returncode == 0:
            return completed.stdout

    file_path = repo / repo_path
    if file_path.exists():
        return file_path.read_text(encoding="utf-8", errors="replace")

    raise subprocess.CalledProcessError(
        128,
        ["git", "-C", str(repo), "show", f"origin/{branch}:{repo_path}"],
    )


def export_binary_file(repo: Path, branch: str, repo_path: str, destination: Path) -> None:
    candidates = [f"origin/{branch}:{repo_path}", f"HEAD:{repo_path}"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    for candidate in candidates:
        with destination.open("wb") as handle:
            completed = subprocess.run(
                ["git", "-C", str(repo), "show", candidate],
                check=False,
                stdout=handle,
                stderr=subprocess.PIPE,
            )
        if completed.returncode == 0:
            return

    file_path = repo / repo_path
    if file_path.exists():
        shutil.copy2(file_path, destination)
        return

    raise subprocess.CalledProcessError(
        128,
        ["git", "-C", str(repo), "show", f"origin/{branch}:{repo_path}"],
    )


def resolve_branch_sha(repo: Path, branch: str) -> str:
    """返回上游分支当前指向的提交号，用于在生成物中记录本次同步到的版本。"""
    for ref in (f"origin/{branch}", "HEAD"):
        completed = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", ref],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode == 0 and completed.stdout.strip():
            return completed.stdout.strip()
    return "unknown"


def reset_generated_targets() -> None:
    legacy_reference_root = DOCS_ROOT / "reference"
    if legacy_reference_root.exists():
        shutil.rmtree(legacy_reference_root)

    for legacy_dir in ("collection", "analysis"):
        legacy_path = DOCS_ROOT / legacy_dir
        if legacy_path.exists():
            shutil.rmtree(legacy_path)


def clean_heading(value: str) -> str:
    value = re.sub(r"<a\s+name=.*?</a>", "", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", "", value)
    return value.strip()


def should_exclude(path: Path) -> bool:
    return path.name.lower() in EXCLUDED_NAMES


def should_hide_from_nav(path: Path) -> bool:
    return path.name.lower() in NON_NAV_NAMES


def display_dir_whitelist(tool: dict) -> set[str]:
    return DEFAULT_DISPLAY_DIR_WHITELIST | set(tool.get("display_dir_whitelist", set()))


def display_file_whitelist(tool: dict) -> set[str]:
    return DEFAULT_DISPLAY_FILE_WHITELIST | set(tool.get("display_file_whitelist", set()))


def should_keep_display_path(path: Path, tool: dict) -> bool:
    relative_parts = [part.lower() for part in path.parts]
    if not relative_parts:
        return True

    top_level = relative_parts[0]
    if top_level in display_dir_whitelist(tool):
        return True
    if len(relative_parts) == 1 and top_level in display_file_whitelist(tool):
        return True
    return False


def filter_display_tree(root: Path, tool: dict) -> None:
    for path in sorted(root.iterdir(), key=lambda item: len(item.parts), reverse=True):
        if path.name in {".nav.yml", "index.md", "README.md"}:
            continue
        if should_exclude(path):
            continue
        if should_keep_display_path(path.relative_to(root), tool):
            continue
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def repo_web_base(repo: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "config", "--file", ".gitmodules", f"submodule.{repo.name}.url"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    url = completed.stdout.strip()
    if url.endswith(".git"):
        url = url[:-4]
    return url


def repo_blob_url(tool: dict, repo_path: str) -> str:
    return f"{tool['repo_web_base']}/blob/{tool['branch']}/{repo_path}"


def repo_tree_url(tool: dict, repo_path: str) -> str:
    return f"{tool['repo_web_base']}/tree/{tool['branch']}/{repo_path}"


def normalize_repo_path(path: Path) -> Path:
    normalized = Path(".")
    for part in path.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            normalized = normalized.parent
            continue
        normalized /= part
    return normalized


def rewrite_repo_readme_assets(content: str, tool: dict) -> tuple[str, list[tuple[Path, Path]]]:
    readme_dir = Path(tool["repo_readme"]).parent
    copied_assets: dict[Path, Path] = {}

    def rewrite_target(target: str) -> str:
        if "://" in target or target.startswith(("#", "mailto:", "javascript:", "data:")):
            return target

        clean_target = target.split("#", 1)[0].split("?", 1)[0]
        if not clean_target:
            return target

        repo_candidate = normalize_repo_path(readme_dir / clean_target)
        source_path = tool["repo"] / repo_candidate
        if not source_path.is_file():
            return target

        generated_target = Path("assets") / "repo" / repo_candidate
        copied_assets[repo_candidate] = generated_target
        suffix = target[len(clean_target):]
        return f"./{generated_target.as_posix()}{suffix}"

    rewritten = re.sub(
        r"(<img\b[^>]*\bsrc=[\"'])([^\"']+)([\"'])",
        lambda match: f"{match.group(1)}{rewrite_target(match.group(2))}{match.group(3)}",
        content,
        flags=re.IGNORECASE,
    )
    rewritten = re.sub(
        r"(!\[[^\]]*]\()([^)]+)(\))",
        lambda match: f"{match.group(1)}{rewrite_target(match.group(2))}{match.group(3)}",
        rewritten,
    )
    return rewritten, [(source, destination) for source, destination in copied_assets.items()]


def rewrite_missing_local_links(path: Path, root: Path, tool: dict, current_repo_path: Path | None = None) -> None:
    original_content = path.read_text(encoding="utf-8")
    content = original_content
    content = rewrite_shared_asset_links(content, path)
    content = rewrite_external_image_links(content)
    content = content.replace("](.//README.md", "](index.md")
    content = content.replace("](./README.md", "](index.md")
    content = content.replace("](../advanced_features/README.md", "](../advanced_features/index.md")
    content = content.replace("](./source/advanced_features/README.md", "](./source/advanced_features/index.md")
    content = content.replace("](./source/c_api/README.md", "](./source/c_api/index.md")
    content = content.replace("](./source/python_api/README.md", "](./source/python_api/index.md")
    content = content.replace("../../msprof-analyze/", "../../msprof-analyze/index.md")
    if current_repo_path is None:
        current_repo_path = Path(tool["source_subdir"]) / path.relative_to(root)

    def resolve_target(raw_target: str) -> str | None:
        """把本地链接解析为新目标；无法/无需改写时返回 None（调用方保持原样）。"""
        target = raw_target.strip()
        if "://" in target or target.startswith(("#", "mailto:", "javascript:")):
            return None

        clean_target = target.split("#", 1)[0].split("?", 1)[0]
        if not clean_target:
            return None
        suffix = target[len(clean_target):]  # 保留 #锚点 / ?参数

        root_resolved = root.resolve()
        candidate = (path.parent / clean_target).resolve()
        try:
            candidate_relative = candidate.relative_to(root_resolved)
            if candidate.name.lower() == "readme.md":
                index_candidate = candidate.with_name("index.md")
                if index_candidate.exists():
                    rewritten_target = Path(index_candidate.relative_to(path.parent.resolve())).as_posix()
                    return f"{rewritten_target}{suffix}"

            if candidate.exists():
                return None

            repo_relative = Path(tool["source_subdir"]) / candidate_relative
            if upstream_path_exists(tool["repo"], tool["branch"], repo_relative.as_posix()):
                remote = repo_tree_url(tool, repo_relative.as_posix()) if target.endswith("/") else repo_blob_url(tool, repo_relative.as_posix())
                return f"{remote}{suffix}"
            return None
        except ValueError:
            # README 位于仓库根部，其链接已由 rewrite_repo_readme_links 把 docs/zh/ 改写为 source/，
            # 因此除了按生成后的路径判断，还要还原成上游真实路径（docs/zh/...）再判断一次，
            # 否则 README 里指向「未在导航展示的目录」的链接无法转成源码仓链接，只能留成死链。
            repo_candidate = normalize_repo_path(current_repo_path.parent / clean_target)
            repo_candidates = [repo_candidate]
            source_subdir = tool.get("source_subdir")
            if source_subdir:
                for prefix in ("./source/", "source/"):
                    if repo_candidate.as_posix().startswith(prefix):
                        repo_candidates.append(
                            Path(source_subdir) / repo_candidate.as_posix()[len(prefix):]
                        )
                        break
            for upstream_candidate in repo_candidates:
                if upstream_path_exists(tool["repo"], tool["branch"], upstream_candidate.as_posix()):
                    remote = repo_tree_url(tool, upstream_candidate.as_posix()) if target.endswith("/") else repo_blob_url(tool, upstream_candidate.as_posix())
                    return f"{remote}{suffix}"
            if repo_candidate.name.lower() == "readme.md" and upstream_path_exists(tool["repo"], tool["branch"], "README.md"):
                return f"{repo_blob_url(tool, 'README.md')}{suffix}"
            return None

    def replace_markdown_link(match: re.Match[str]) -> str:
        new_target = resolve_target(f"{match.group(2)}{match.group(3) or ''}")
        if new_target is None:
            return match.group(0)
        return f"[{match.group(1)}]({new_target})"

    def replace_badge_link(match: re.Match[str]) -> str:
        new_target = resolve_target(match.group(2))
        if new_target is None:
            return match.group(0)
        return f"{match.group(1)}{new_target}{match.group(3)}"

    rewritten = re.sub(r"\[([^\]]+)\]\(([^)]+?)(#[^)]+)?\)", replace_markdown_link, content)
    # [![徽章](图片)](目标) 这类「图片作链接文字」的写法，外层链接不会被上面的正则匹配到，单独解析一次。
    rewritten = re.sub(r"(\[!\[[^\]]*\]\([^)]*\)\]\()([^)]+)(\))", replace_badge_link, rewritten)
    if rewritten != original_content:
        path.write_text(rewritten, encoding="utf-8")


def prune_tree(root: Path) -> None:
    for path in sorted(root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if should_exclude(path):
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()


CN_DIR_TITLES = {
    "getting_started": "快速入门",
    "quick_start": "快速上手",
    "install_guide": "安装指南",
    "user_guide": "用户指南",
    "best_practices": "最佳实践",
    "advanced_features": "高级特性",
    "c_api": "C API",
    "python_api": "Python API",
    "developer_guide": "开发者指南",
    "development_guide": "开发者指南",
    "agent_guide": "Agent 指南",
    "reference": "参考",
    "design": "设计说明",
    "example": "使用示例",
    "support": "支持与反馈",
    "release_notes": "版本发布说明",
}


def strip_numbering(label: str) -> str:
    return re.sub(
        r"^(?:"
        r"\d{1,2}(?:\.\d{1,2}){0,2}[.、)]?\s+(?=[A-Za-z\u4e00-\u9fff])"
        r"|\d{1,2}[.、](?=[A-Za-z\u4e00-\u9fff])"
        r"|[（(][\d一二三四五六七八九十]{1,3}[)）]\s*(?=[A-Za-z\u4e00-\u9fff])"
        r"|[一二三四五六七八九十]{1,3}[、.]\s*(?=[A-Za-z\u4e00-\u9fff])"
        r")",
        "",
        label,
    ).strip()


def nav_title(path: Path) -> str:
    if path.is_dir():
        return CN_DIR_TITLES.get(path.name.lower(), path.name)
    label = re.sub(r"[*`]+", "", first_heading(path)).strip()
    label = strip_numbering(label)
    return label or path.name


def single_page_child(directory: Path) -> Path | None:
    subdirectories = [
        child
        for child in directory.iterdir()
        if child.is_dir() and child.name not in NON_NAV_NAMES
    ]
    if subdirectories:
        return None
    content = [
        child
        for child in directory.glob("*.md")
        if child.name.lower() not in ("index.md", "readme.md") and not should_exclude(child)
    ]
    return content[0] if len(content) == 1 else None


def yaml_value(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9\u4e00-\u9fff _./\-]+", value):
        return value
    return json.dumps(value, ensure_ascii=False)


def sort_nav_items(paths: list[Path]) -> list[Path]:
    def sort_key(path: Path) -> tuple[int, str]:
        name = path.name
        lowered = name.lower()
        for index, preferred in enumerate(NAV_ORDER):
            if lowered == preferred:
                return (index, lowered)
        return (len(NAV_ORDER), lowered)

    return sorted(paths, key=sort_key)


def first_heading(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return clean_heading(stripped.lstrip("#").strip())
    except UnicodeDecodeError:
        pass
    return path.stem.replace("_", " ")


def duplicate_readme_as_index(directory: Path) -> None:
    readme = directory / "README.md"
    if not readme.exists():
        return
    index = directory / "index.md"
    if not index.exists():
        shutil.copy2(readme, index)
    # README 与 index 共存会让 MkDocs 报冲突告警，并让同一内容重复进入搜索索引。
    readme.unlink()


def write_directory_nav(directory: Path) -> None:
    subdirectories = sort_nav_items(
        [
            child
            for child in directory.iterdir()
            if child.is_dir()
            and any(child.iterdir())
            and not should_exclude(child)
            and not should_hide_from_nav(child)
        ]
    )
    markdown_children = sort_nav_items(
        [
            child
            for child in directory.glob("*.md")
            if child.name.lower() != "readme.md" and not should_exclude(child)
        ]
    )

    nav_items: list[str] = []
    if (directory / "index.md").exists():
        nav_items.append("index.md")

    for child in subdirectories:
        single = single_page_child(child)
        if single is not None:
            nav_items.append(f"{yaml_value(nav_title(single))}: {child.name}/{single.name}")
            continue
        title = CN_DIR_TITLES.get(child.name.lower())
        nav_items.append(f"{yaml_value(title)}: {child.name}" if title else child.name)

    for child in markdown_children:
        if child.name.lower() == "index.md":
            continue
        nav_items.append(f"{yaml_value(nav_title(child))}: {child.name}")

    lines = ["collapse_single_pages: true"]
    if nav_items:
        lines.append("nav:")
        for item in nav_items:
            lines.append(f"  - {item}")
    lines.append("")
    (directory / ".nav.yml").write_text("\n".join(lines), encoding="utf-8")


def build_directory_indexes(root: Path, title_prefix: str) -> None:
    prune_tree(root)
    duplicate_readme_as_index(root)
    directories = sorted(
        [path for path in root.rglob("*") if path.is_dir()],
        key=lambda item: len(item.parts),
    )
    for directory in directories:
        duplicate_readme_as_index(directory)
        if (directory / "index.md").exists():
            continue

        markdown_children = sort_nav_items(
            child
            for child in directory.glob("*.md")
            if child.name.lower() != "index.md"
            and not (child.name == "README.md" and (directory / "index.md").exists())
            and not should_exclude(child)
        )
        subdirectories = sort_nav_items(
            child
            for child in directory.iterdir()
            if child.is_dir() and any(child.iterdir()) and not should_exclude(child)
        )
        if not markdown_children and not subdirectories:
            continue
        if single_page_child(directory) and not (directory / "index.md").exists():
            continue

        relative = directory.relative_to(root)
        heading = (
            title_prefix
            if relative == Path(".")
            else CN_DIR_TITLES.get(relative.name.lower(), relative.name.replace("-", " ").replace("_", " "))
        )
        lines = [f"# {heading}", "", "该目录下的内容索引如下。", ""]

        if subdirectories:
            lines.extend(["## 子目录", ""])
            for child in subdirectories:
                base = child.relative_to(directory).as_posix()
                single = single_page_child(child)
                if single is not None:
                    lines.append(f"- [{nav_title(single)}]({base}/{single.name})")
                else:
                    title = CN_DIR_TITLES.get(child.name.lower(), child.name.replace("-", " ").replace("_", " "))
                    lines.append(f"- [{title}]({base}/)")
            lines.append("")

        if markdown_children:
            lines.extend(["## 页面", ""])
            for child in markdown_children:
                target = child.relative_to(directory).as_posix()
                lines.append(f"- [{nav_title(child)}]({target})")
            lines.append("")

        (directory / "index.md").write_text("\n".join(lines), encoding="utf-8")

    write_directory_nav(root)
    for directory in sorted([path for path in root.rglob("*") if path.is_dir()]):
        if any(directory.iterdir()):
            write_directory_nav(directory)


def write_tool_nav(path: Path, tool: dict) -> None:
    lines = [f"title: {tool['title']}", "nav:", f"  - {tool['title']}: index.md"]
    featured_entries = [
        (label, relative)
        for label, relative in tool["entry_points"]
        if relative.startswith("source/") and (path.parent / relative).exists()
    ]
    if not featured_entries:
        fallback = "source/user_guide/index.md"
        if (path.parent / fallback).exists():
            featured_entries = [("用户指南", fallback)]
    if featured_entries:
        lines.append("  - 推荐阅读:")
        for label, relative in featured_entries:
            lines.append(f"    - {yaml_value(label)}: {relative}")
    if tool.get("source_subdir") and (path.parent / "source").exists():
        lines.append("  - 文档目录: source")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def rewrite_repo_readme_links(
    content: str | None,
    tool: dict,
    source_root: Path,
    readme_path: str | None = None,
) -> tuple[str, list[tuple[Path, Path]]]:
    if not content:
        return content or "", []

    replacements = {
        "./docs/zh/": "./source/",
        "docs/zh/": "source/",
        # 英文 README 引用 docs/en/ 下的文档与图片，但上游通常只有中文资产，同样映射到 source/。
        "./docs/en/": "./source/",
        "docs/en/": "source/",
        "./docs/": "./source/",
        "./docs/zh": "./source",
        "docs/zh": "source",
        "./docs": "./source",
    }
    for old, new in replacements.items():
        content = content.replace(old, new)
    content = content.replace("](docs/", "](source/")
    content = content.replace('src="docs/', 'src="source/')
    content = content.replace("src='docs/", "src='source/")

    # Allow Markdown links inside aligned HTML wrappers from repo READMEs.
    content = content.replace('<div align="center">', '<div align="center" markdown="1">')
    content = content.replace("<div align='center'>", '<div align="center" markdown="1">')

    filtered_lines = []
    for line in content.splitlines():
        lowered = line.lower()
        if "/source/legal/" in lowered:
            continue
        if "contributing.md" in lowered or "contributed" in lowered:
            continue
        filtered_lines.append(line)

    rewritten = "\n".join(filtered_lines) + "\n"
    rewritten = rewritten.replace("./source/LICENSE", repo_blob_url(tool, "docs/LICENSE"))
    rewritten, asset_exports = rewrite_repo_readme_assets(rewritten, tool)
    temp_readme = source_root.parent / "_repo_readme_rewrite.md"
    temp_readme.write_text(rewritten, encoding="utf-8")
    rewrite_missing_local_links(
        temp_readme, source_root, tool, current_repo_path=Path(readme_path or tool["repo_readme"])
    )
    final_text = temp_readme.read_text(encoding="utf-8")
    temp_readme.unlink(missing_ok=True)
    return final_text, asset_exports


def generate_tool_page(tool: dict) -> tuple[str, list[str]]:
    """生成单个工具的文档与首页，返回 (同步到的上游提交号, 未成功项说明)。"""
    tool = {**tool, "repo_web_base": repo_web_base(tool["repo"])}
    tool_root = DOCS_ROOT / tool["slug"]
    source_root = tool_root / "source"
    tool_root.mkdir(parents=True, exist_ok=True)
    source_subdir = tool.get("source_subdir")
    sha = resolve_branch_sha(tool["repo"], tool["branch"])
    issues: list[str] = []

    if source_subdir:
        try:
            export_latest_branch(tool["repo"], tool["branch"], source_subdir, source_root)
            filter_display_tree(source_root, tool)
            build_directory_indexes(source_root, tool["title"])
            for markdown_path in source_root.rglob("*.md"):
                rewrite_missing_local_links(markdown_path, source_root, tool)
        except Exception as error:
            # 上游不可达或目录结构调整时，保留现有文档继续构建其余工具。
            print(f"[warn] {tool['slug']} 上游导出失败，保留现有文档: {error}")
            issues.append(f"上游文档导出失败（{error}）")
    write_tool_nav(tool_root / ".nav.yml", tool)
    try:
        readme_text = export_text_file(tool["repo"], tool["branch"], tool["repo_readme"])
    except Exception as error:
        # README 缺失或改名时保留现有首页，不覆盖。
        print(f"[warn] {tool['slug']} README 获取失败，保留现有首页: {error}")
        issues.append(f"README 获取失败（{error}）")
        return sha, issues
    readme_assets: list[tuple[Path, Path]] = []
    if source_subdir:
        readme_text, readme_assets = rewrite_repo_readme_links(readme_text, tool, source_root)
    for repo_asset, destination in readme_assets:
        try:
            export_binary_file(tool["repo"], tool["branch"], repo_asset.as_posix(), tool_root / destination)
        except Exception as error:
            print(f"[warn] {tool['slug']} README 图片 {repo_asset} 导出失败，跳过: {error}")
            issues.append(f"README 图片导出失败（{repo_asset}）")
    notice_lines = [
        "!!! info",
        f"    更多信息，欢迎查看源码仓: [{tool['title']}]({tool['repo_web_base']})",
    ]
    repo_notice = "\n".join([*notice_lines, ""])
    front_matter = "\n".join(
        [
            "---",
            f"title: {tool['title']}",
            "---",
            "",
        ]
    )
    # 记录本次同步到的上游提交号，便于事后确认线上内容对应的版本（页面源码可见，不影响阅读）。
    build_comment = f"<!-- build-info: {tool['slug']} origin/{tool['branch']} @ {sha} -->"
    # 上游 README 自带的中英文切换行保留原样，其死链由 hooks.on_page_content 修正。
    has_en_readme = upstream_file_exists(tool["repo"], tool["branch"], "README_EN.md")
    (tool_root / "index.md").write_text(
        f"{front_matter}{build_comment}\n\n{repo_notice}{readme_text}", encoding="utf-8"
    )

    # 英文首页：由上游 README_EN.md 生成，供语言切换即时使用。
    if has_en_readme:
        try:
            readme_en = export_text_file(tool["repo"], tool["branch"], "README_EN.md")
            readme_en, assets_en = rewrite_repo_readme_links(
                readme_en, tool, source_root, readme_path="README_EN.md"
            )
            for repo_asset, destination in assets_en:
                try:
                    export_binary_file(tool["repo"], tool["branch"], repo_asset.as_posix(), tool_root / destination)
                except Exception as error:
                    print(f"[warn] {tool['slug']} 英文 README 图片 {repo_asset} 导出失败，跳过: {error}")
                    issues.append(f"英文 README 图片导出失败（{repo_asset}）")
            en_notice = "\n".join(
                [
                    "!!! info",
                    f"    For more information, visit the source repository: [{tool['title']}]({tool['repo_web_base']})",
                    "",
                ]
            )
            (tool_root / "index.en.md").write_text(
                f"{front_matter}{build_comment}\n\n{en_notice}{readme_en}", encoding="utf-8"
            )
        except Exception as error:
            print(f"[warn] {tool['slug']} 英文首页生成失败，跳过: {error}")
            issues.append(f"英文首页生成失败（{error}）")

    return sha, issues


def main() -> None:
    reset_generated_targets()
    export_shared_assets()
    sync_records: list[tuple[str, str, list[str]]] = []
    for tool in TOOLS:
        sha, issues = generate_tool_page(tool)
        sync_records.append((tool["slug"], sha, issues))
    from fetch_release_notes import main as generate_whats_new_page

    generate_whats_new_page()

    # 构建策略：任一工具同步失败都不阻断构建，站点按当前可用内容发布。这里只做汇总，便于事后排查。
    print("[summary] 上游同步记录（页面源码中可通过 build-info 注释核对）:")
    for slug, sha, issues in sync_records:
        print(f"[summary]   {slug}: {sha} ({'OK' if not issues else '部分失败'})")
        for issue in issues:
            print(f"[summary]     - {issue}")
    failed = [slug for slug, _, issues in sync_records if issues]
    if failed:
        print(
            f"[summary] 注意：{len(failed)}/{len(TOOLS)} 个工具未完整同步"
            f"（{', '.join(failed)}），站点已按可用内容发布。"
        )


if __name__ == "__main__":
    main()
