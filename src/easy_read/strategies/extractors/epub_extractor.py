import re
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from bs4 import BeautifulSoup, NavigableString, Tag
from ebooklib import ITEM_DOCUMENT, ITEM_IMAGE, epub

from easy_read.strategies.extractors.base import (
    BookExtractor,
    ExtractedImageItem,
    ExtractedMarkdownItem,
    ExtractedSourceItem,
    ExtractResult,
)
from easy_read.utils.names import safe_filename_part


def normalize_text(text: str) -> str:
    """规整文本中的空白字符。

    Args:
        text: 原始文本。

    Returns:
        str: 规整后的文本。
    """
    return re.sub(r"\s+", " ", text).strip()


def get_item_text(item: Any) -> str:
    """读取 EPUB 条目文本。

    Args:
        item: EPUB 条目对象。

    Returns:
        str: UTF-8 文本。
    """
    content = item.get_content()
    return content.decode("utf-8", errors="ignore")


def get_item_bytes(item: Any) -> bytes:
    """读取 EPUB 条目字节内容。

    Args:
        item: EPUB 条目对象。

    Returns:
        bytes: 条目字节内容。
    """
    return bytes(item.get_content())


def extract_document_title(html_text: str) -> str:
    """从 XHTML 文本中提取标题。

    优先使用 h1、h2、h3，其次使用 title，最后使用正文第一行。

    Args:
        html_text: XHTML 文本。

    Returns:
        str: 文档标题。
    """
    soup = BeautifulSoup(html_text, "html.parser")

    for selector in ["h1", "h2", "h3", "title"]:
        node = soup.find(selector)
        if node:
            text = normalize_text(node.get_text(" ", strip=True))
            if text:
                return text

    body_text = normalize_text(soup.get_text(" ", strip=True))
    return body_text[:80] if body_text else "Untitled"


def get_node_attribute_text(node: Tag) -> str:
    """提取标签中可用于判断语义的属性文本。

    Args:
        node: BeautifulSoup 标签节点。

    Returns:
        str: class、id、role、epub:type 等属性拼接后的小写文本。
    """
    values: list[str] = []

    for attr_name in ["class", "id", "role", "epub:type", "type", "aria-label"]:
        attr_value = node.get(attr_name)

        if attr_value is None:
            continue

        if isinstance(attr_value, list):
            values.extend(str(item) for item in attr_value)
        else:
            values.append(str(attr_value))

    return " ".join(values).lower()


def is_note_container_node(node: Tag) -> bool:
    """判断标签是否像脚注或尾注容器。

    容器通常包住整组 Notes / Endnotes，不应该被渲染成单条脚注。

    Args:
        node: BeautifulSoup 标签节点。

    Returns:
        bool: 像脚注或尾注容器时返回 True。
    """
    attribute_text = get_node_attribute_text(node)

    if not attribute_text:
        return False

    container_keywords = [
        "endnotes",
        "footnotes",
        "backnotes",
        "chapter-notes",
        "rearnotes",
        "notes-list",
        "note-list",
    ]

    return any(keyword in attribute_text for keyword in container_keywords)


def is_note_entry_node(node: Tag) -> bool:
    """判断标签是否像单条脚注或尾注。

    判断依据尽量使用 EPUB 常见语义和通用命名，不绑定某一本书的特定 class。

    Args:
        node: BeautifulSoup 标签节点。

    Returns:
        bool: 像单条脚注或尾注时返回 True。
    """
    tag_name = node.name.lower()

    if tag_name not in {"div", "p", "li", "aside"}:
        return False

    if is_note_container_node(node):
        return False

    attribute_text = get_node_attribute_text(node)

    if not attribute_text:
        return False

    note_keywords = [
        "doc-footnote",
        "doc-endnote",
        "footnote",
        "endnote",
        "backnote",
        "rearnote",
    ]

    if any(keyword in attribute_text for keyword in note_keywords):
        return True

    # 一些 EPUB 使用 fn、fn1、fn_01、note-1 等简短命名。
    return bool(re.search(r"(^|[^a-z])(fn|note)[-_]?\d+($|[^a-z0-9])", attribute_text))


def is_label_node(node: Tag) -> bool:
    """判断标签是否像脚注编号标签。

    Args:
        node: BeautifulSoup 标签节点。

    Returns:
        bool: 像脚注编号标签时返回 True。
    """
    attribute_text = get_node_attribute_text(node)

    if "label" in attribute_text:
        return True

    if node.name.lower() == "sup":
        return True

    return False


def is_linked_note_marker(node: Tag) -> bool:
    """判断标签是否像正文中的脚注跳转标记。

    Args:
        node: BeautifulSoup 标签节点。

    Returns:
        bool: 像脚注跳转标记时返回 True。
    """
    if node.name.lower() != "a":
        return False

    href = str(node.get("href", "")).lower()
    attribute_text = get_node_attribute_text(node)
    text = normalize_text(node.get_text(" ", strip=True))

    if not text:
        return False

    has_note_target = any(keyword in href for keyword in ["footnote", "endnote", "note", "_en", "#en", "#fn"])
    has_note_attr = any(keyword in attribute_text for keyword in ["footnote", "endnote", "noteref", "doc-noteref"])

    return has_note_target or has_note_attr


def normalize_note_text(text: str) -> str:
    """规整脚注文本。

    Args:
        text: 原始脚注文本。

    Returns:
        str: 适合 Markdown 列表展示的脚注文本。
    """
    normalized = normalize_text(text)

    # 把开头的纯数字编号统一成 “1. 内容”。
    match = re.match(r"^(\d{1,4})\s+(.+)$", normalized)
    if match:
        return f"{match.group(1)}. {match.group(2)}"

    return normalized


def build_epub_image_map(book: epub.EpubBook, project_dir: Path) -> tuple[dict[str, str], list[ExtractedImageItem]]:
    """提取 EPUB 图片并建立图片引用映射。

    Args:
        book: EPUB 书籍对象。
        project_dir: 书籍项目目录。

    Returns:
        tuple[dict[str, str], list[ExtractedImageItem]]: EPUB 内部图片名到项目图片路径的映射，以及图片记录。
    """
    image_dir = project_dir / "images" / "original"
    image_dir.mkdir(parents=True, exist_ok=True)

    image_map: dict[str, str] = {}
    image_items: list[ExtractedImageItem] = []

    image_index = 1

    for item in book.get_items():
        if item.get_type() != ITEM_IMAGE:
            continue

        source_name = item.get_name()
        source_path = Path(unquote(source_name))
        suffix = source_path.suffix or ".img"
        image_filename = f"image_{image_index:04d}{suffix.lower()}"
        target_file = image_dir / image_filename

        target_file.write_bytes(get_item_bytes(item))

        project_relative_file = target_file.relative_to(project_dir).as_posix()

        image_items.append(
            ExtractedImageItem(
                image_id=f"image_{image_index:04d}",
                source_name=source_name,
                file=project_relative_file,
            )
        )

        # EPUB 内部图片引用可能使用完整路径，也可能只使用文件名。
        image_map[source_name] = project_relative_file
        image_map[source_name.lstrip("./")] = project_relative_file
        image_map[source_path.name] = project_relative_file

        image_index += 1

    return image_map, image_items


def resolve_image_reference(src: str, image_map: dict[str, str]) -> str:
    """解析 Markdown 图片引用路径。

    Args:
        src: XHTML 中的图片 src。
        image_map: EPUB 图片名到项目图片路径的映射。

    Returns:
        str: Markdown 中使用的图片路径。
    """
    cleaned_src = unquote(src).split("#", 1)[0].split("?", 1)[0]
    cleaned_src = cleaned_src.lstrip("./")
    filename = Path(cleaned_src).name

    if cleaned_src in image_map:
        return image_map[cleaned_src]

    if filename in image_map:
        return image_map[filename]

    return cleaned_src


def render_inline_node(node: Tag | NavigableString, image_map: dict[str, str]) -> str:
    """渲染行内节点为 Markdown 文本。

    Args:
        node: BeautifulSoup 节点。
        image_map: 图片路径映射。

    Returns:
        str: Markdown 文本。
    """
    if isinstance(node, NavigableString):
        return str(node)

    if not isinstance(node, Tag):
        return ""

    tag_name = node.name.lower()

    if tag_name in {"script", "style", "head", "meta", "link"}:
        return ""

    if tag_name == "br":
        return "\n"

    if tag_name == "img":
        alt_text = normalize_text(node.get("alt", ""))
        src = node.get("src", "")
        image_path = resolve_image_reference(src, image_map) if src else ""
        return f"![{alt_text}]({image_path})" if image_path else ""

    children_text = "".join(render_inline_node(child, image_map) for child in node.children)

    if tag_name in {"strong", "b"}:
        text = normalize_text(children_text)
        return f"**{text}**" if text else ""

    if tag_name in {"em", "i"}:
        text = normalize_text(children_text)
        return f"*{text}*" if text else ""

    if tag_name == "a":
        text = normalize_text(children_text)
        href = str(node.get("href", "")).strip()

        if not text:
            return ""

        # 正文脚注跳转标记通常只显示一个数字，保留文本即可，避免 Markdown 中塞入大量内部锚点。
        if is_linked_note_marker(node):
            return text

        if href and not href.startswith("#"):
            return f"[{text}]({href})"

        return text

    return children_text


def render_children_as_plain_markdown(node: Tag, image_map: dict[str, str]) -> str:
    """把标签子节点渲染为一段 Markdown 文本。

    Args:
        node: BeautifulSoup 标签节点。
        image_map: 图片路径映射。

    Returns:
        str: 合并后的 Markdown 文本。
    """
    parts: list[str] = []

    for child in node.children:
        text = render_inline_node(child, image_map)
        if text.strip():
            parts.append(text.strip())

    return normalize_text(" ".join(parts))


def render_note_entry_node(node: Tag, image_map: dict[str, str]) -> str:
    """渲染脚注或尾注条目。

    Args:
        node: BeautifulSoup 标签节点。
        image_map: 图片路径映射。

    Returns:
        str: Markdown 列表项。
    """
    parts: list[str] = []

    for child in node.children:
        if isinstance(child, Tag) and is_label_node(child):
            label_text = normalize_text(child.get_text(" ", strip=True))
            if label_text:
                parts.append(label_text)
            continue

        text = render_inline_node(child, image_map)
        if text.strip():
            parts.append(text.strip())

    text = normalize_note_text(" ".join(parts))

    if not text:
        return ""

    return f"- {text}"


def render_list_node(node: Tag, image_map: dict[str, str]) -> list[str]:
    """渲染列表节点。

    Args:
        node: BeautifulSoup 标签节点。
        image_map: 图片路径映射。

    Returns:
        list[str]: Markdown 列表项。
    """
    blocks: list[str] = []
    ordered = node.name.lower() == "ol"

    for index, child in enumerate(node.find_all("li", recursive=False), start=1):
        child_text = render_children_as_plain_markdown(child, image_map)

        if not child_text:
            continue

        if ordered:
            blocks.append(f"{index}. {child_text}")
        else:
            blocks.append(f"- {child_text}")

    return blocks


def render_table_node(node: Tag, image_map: dict[str, str]) -> list[str]:
    """渲染表格节点。

    Args:
        node: BeautifulSoup 标签节点。
        image_map: 图片路径映射。

    Returns:
        list[str]: Markdown 表格文本列表。
    """
    rows: list[list[str]] = []

    for row in node.find_all("tr"):
        cells = row.find_all(["th", "td"], recursive=False)
        cell_texts = [normalize_text(render_children_as_plain_markdown(cell, image_map)) for cell in cells]

        if cell_texts:
            rows.append(cell_texts)

    if not rows:
        return []

    max_columns = max(len(row) for row in rows)
    normalized_rows = [row + [""] * (max_columns - len(row)) for row in rows]

    header = normalized_rows[0]
    separator = ["---"] * max_columns
    body_rows = normalized_rows[1:]

    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |",
    ]

    for row in body_rows:
        lines.append("| " + " | ".join(row) + " |")

    return ["\n".join(lines)]


def flush_direct_text(blocks: list[str], direct_text_parts: list[str]) -> list[str]:
    """把直接文本缓存写入段落列表。

    Args:
        blocks: Markdown 段落列表。
        direct_text_parts: 直接文本片段列表。

    Returns:
        list[str]: 清空后的直接文本片段列表。
    """
    if direct_text_parts:
        direct_text = normalize_text(" ".join(direct_text_parts))
        if direct_text:
            blocks.append(direct_text)

    return []


def render_generic_container_node(node: Tag, image_map: dict[str, str]) -> list[str]:
    """渲染普通容器节点。

    Args:
        node: BeautifulSoup 标签节点。
        image_map: 图片路径映射。

    Returns:
        list[str]: Markdown 段落列表。
    """
    blocks: list[str] = []
    direct_text_parts: list[str] = []

    for child in node.children:
        if isinstance(child, Tag):
            direct_text_parts = flush_direct_text(blocks, direct_text_parts)
            blocks.extend(render_block_node(child, image_map))
        elif isinstance(child, NavigableString):
            text = normalize_text(str(child))
            if text:
                direct_text_parts.append(text)

    flush_direct_text(blocks, direct_text_parts)
    return blocks


def render_block_node(node: Tag, image_map: dict[str, str]) -> list[str]:
    """渲染块级节点为 Markdown 段落列表。

    Args:
        node: BeautifulSoup 标签节点。
        image_map: 图片路径映射。

    Returns:
        list[str]: Markdown 段落列表。
    """
    tag_name = node.name.lower()

    if tag_name in {"script", "style", "head", "meta", "link"}:
        return []

    if is_note_entry_node(node):
        text = render_note_entry_node(node, image_map)
        return [text] if text else []

    if tag_name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        level = int(tag_name[1])
        text = normalize_text(render_inline_node(node, image_map))
        return [f"{'#' * level} {text}"] if text else []

    if tag_name == "p":
        text = normalize_text(render_inline_node(node, image_map))
        return [text] if text else []

    if tag_name == "blockquote":
        child_blocks = render_generic_container_node(node, image_map)
        return [f"> {block}" for block in child_blocks if block]

    if tag_name in {"ul", "ol"}:
        return render_list_node(node, image_map)

    if tag_name == "li":
        text = render_children_as_plain_markdown(node, image_map)
        return [f"- {text}"] if text else []

    if tag_name == "table":
        return render_table_node(node, image_map)

    if tag_name == "img":
        text = render_inline_node(node, image_map)
        return [text] if text else []

    if tag_name in {"section", "article", "main", "body", "div", "aside", "figure", "figcaption"}:
        return render_generic_container_node(node, image_map)

    return render_generic_container_node(node, image_map)


def html_to_markdown(html_text: str, image_map: dict[str, str]) -> str:
    """将 XHTML 文本转换成基础 Markdown。

    Args:
        html_text: XHTML 文本。
        image_map: 图片路径映射。

    Returns:
        str: Markdown 文本。
    """
    soup = BeautifulSoup(html_text, "html.parser")
    root = soup.body or soup

    blocks: list[str] = []

    for child in root.children:
        if isinstance(child, Tag):
            blocks.extend(render_block_node(child, image_map))
        elif isinstance(child, NavigableString):
            text = normalize_text(str(child))
            if text:
                blocks.append(text)

    cleaned_blocks = [block.strip() for block in blocks if block.strip()]
    return "\n\n".join(cleaned_blocks) + "\n"


class EpubExtractor(BookExtractor):
    """EPUB 书籍提取器。"""

    def extract(self, book_file: Path, project_dir: Path, stage_dir: Path, config: dict) -> ExtractResult:
        """提取 EPUB 内容。

        Args:
            book_file: 项目内的 EPUB 文件路径。
            project_dir: 书籍项目目录。
            stage_dir: 提取阶段目录。
            config: 提取阶段配置。

        Returns:
            ExtractResult: EPUB 提取结果。
        """
        source_dir = stage_dir / "source"
        raw_md_dir = stage_dir / "raw_md"

        if stage_dir.exists():
            shutil.rmtree(stage_dir)

        source_dir.mkdir(parents=True, exist_ok=True)
        raw_md_dir.mkdir(parents=True, exist_ok=True)

        filename_max_chars = int(config.get("filename_max_chars", 30))

        book = epub.read_epub(str(book_file))
        image_map, image_items = build_epub_image_map(book=book, project_dir=project_dir)

        source_items: list[ExtractedSourceItem] = []
        raw_md_items: list[ExtractedMarkdownItem] = []

        document_items = self.get_ordered_document_items(book)

        for index, item in enumerate(document_items, start=1):
            doc_id = f"doc_{index:04d}"
            html_text = get_item_text(item)

            source_filename = f"source_{index:04d}.xhtml"
            source_file = source_dir / source_filename
            source_file.write_text(html_text, encoding="utf-8", newline="\n")

            title = extract_document_title(html_text)
            readable_name = safe_filename_part(title, max_chars=filename_max_chars)
            raw_md_filename = f"{index:03d} {readable_name}.md"
            raw_md_file = raw_md_dir / raw_md_filename

            markdown_text = html_to_markdown(html_text=html_text, image_map=image_map)
            raw_md_file.write_text(markdown_text, encoding="utf-8", newline="\n")

            source_items.append(
                ExtractedSourceItem(
                    doc_id=doc_id,
                    file=source_file.relative_to(stage_dir).as_posix(),
                )
            )

            raw_md_items.append(
                ExtractedMarkdownItem(
                    doc_id=doc_id,
                    file=raw_md_file.relative_to(stage_dir).as_posix(),
                )
            )

        return ExtractResult(
            source_items=source_items,
            raw_md_items=raw_md_items,
            image_items=image_items,
        )

    def get_ordered_document_items(self, book: epub.EpubBook) -> list[Any]:
        """按 EPUB spine 顺序获取文档条目。

        Args:
            book: EPUB 书籍对象。

        Returns:
            list[Any]: 文档条目列表。
        """
        ordered_items: list[Any] = []

        for spine_item in book.spine:
            item_id = spine_item[0] if isinstance(spine_item, tuple) else spine_item
            item = book.get_item_with_id(item_id)

            if item is None:
                continue

            if item.get_type() == ITEM_DOCUMENT:
                ordered_items.append(item)

        if ordered_items:
            return ordered_items

        return [item for item in book.get_items() if item.get_type() == ITEM_DOCUMENT]
