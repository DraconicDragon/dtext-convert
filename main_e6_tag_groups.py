import csv
import json
import os
import re

from id_link_map import ID_LINK_MAP
from to_html import runa


def wrap_list_items(ast):
    """
    Converts '* Item', '** Subitem', etc. into nested lists.
    Also handles link transformations within list items properly,
    and preserves all other inline transformations inside list items.
    """
    result = []
    list_stack = []  # Stores tuples of (level, ul_node_reference)

    def push_li_to_stack(level, content_nodes):
        nonlocal result, list_stack

        li_node = {"type": "li", "children": content_nodes}

        # 1. Pop lists from stack that are strictly deeper than the current item's level.
        while list_stack and list_stack[-1][0] > level:
            list_stack.pop()

        # 2. Determine where to add the new li_node.
        if not list_stack or list_stack[-1][0] < level:
            # This item starts a new list (either top-level or nested).
            new_ul_node = {"type": "ul", "children": [li_node]}

            if not list_stack:
                # Case A: New top-level list.
                result.append(new_ul_node)
            else:
                # Case B: New nested list. list_stack[-1][0] < level.
                # It should be a child of the last 'li' in the parent 'ul'.
                _parent_level, parent_ul = list_stack[-1]
                # Ensure parent_ul has children (li items) before accessing [-1]
                if parent_ul["children"]:
                    parent_li = parent_ul["children"][-1]
                    parent_li.setdefault("children", []).append(new_ul_node)
                else:
                    # This case implies a ul was created without an li, which shouldn't happen
                    # with standard list input. Or, the parent_li itself is what we are creating
                    # the sublist for. For robustness, if parent_ul has no children,
                    # this might indicate an issue or a very specific structure.
                    # However, typical list nesting implies parent_li exists.
                    # If this path is hit, it might be worth logging or re-evaluating.
                    # For now, we'll assume parent_li should exist from previous pushes.
                    # If parent_ul["children"] is empty, this new_ul_node might be orphaned
                    # from an li if not handled carefully.
                    # A robust way: the new_ul_node is always added to the children of the parent_li.
                    # This means an li must have been added to parent_ul for this to be a sub-list.
                    # This is generally true if levels increment one by one.
                    # If parent_ul["children"] is empty, it means this is the first child of parent_ul,
                    # which contradicts list_stack[-1][0] < level logic unless structure is unusual.
                    # The most direct parent li is list_stack[-1][1]["children"][-1]
                    parent_li = parent_ul["children"][-1]  # Relies on parent_ul having at least one li
                    parent_li.setdefault("children", []).append(new_ul_node)

            list_stack.append((level, new_ul_node))

        elif list_stack[-1][0] == level:
            # Case C: Item belongs to the existing list at the current level.
            _current_level, current_ul = list_stack[-1]
            current_ul["children"].append(li_node)
        # else: list_stack[-1][0] > level -- this case is eliminated by the while loop.

    # Accumulate "pending" inline nodes when you're inside a list item
    def append_to_current_li(node):
        _, current_ul = list_stack[-1]
        current_li = current_ul["children"][-1]
        current_li.setdefault("children", []).append(node)

    for node in ast:
        if node["type"] == "text":
            lines = node["content"].split("\n")
            for line in lines:
                stripped = line.strip()
                if stripped == "":
                    # Handling of blank lines within text nodes during list processing.
                    # This might need further refinement based on exact DText rules
                    # for how blank lines interact with list item continuation.
                    # If a blank line is encountered while a list is active,
                    # it could signify the end of the current item's text or the list itself
                    # if not followed by another list item or indented content.
                    # For now, if list_stack is active, we might pass to see if subsequent lines
                    # continue the list or if this blank line should be outside.
                    # If not in a list, append it if it's a meaningful part of the text.
                    if not list_stack:  # If not in a list, append the blank line as text.
                        result.append({"type": "text", "content": line})
                    # If in a list, blank lines are tricky. They might be part of an item or separate items.
                    # The original code skipped them if stripped == "".
                    # Let's refine to append if it's part of list item's multiline content or separate.
                    # This part of logic is complex and depends on precise DText rules.
                    # A simple approach for now: if it's not a list item, and we are in a list,
                    # it could be a text continuation or a separator.
                    # The original code's `continue` for blank lines is preserved here for minimal change
                    # to that specific aspect, focusing on the header issue.
                    if stripped == "":  # Re-check stripped for the original continue logic
                        continue

                match = re.match(r"^(\*+)\s+(.*)", line)
                if match:
                    level = len(match.group(1))
                    raw_content = match.group(2)
                    # The content of the list item needs to be parsed.
                    # Calling full parse_dtext_to_ast here can lead to problematic recursion
                    # if parse_dtext_to_ast itself calls wrap_list_items.
                    # Assuming parse_dtext_to_ast is designed to handle sub-parsing or
                    # this is a known part of the existing design.
                    content_nodes = parse_dtext_to_ast(raw_content)
                    push_li_to_stack(level, content_nodes)
                else:  # Not a list item line
                    if list_stack:
                        # This line is part of the current list item's content
                        # It should be parsed for inline DText.
                        parsed_line_nodes = parse_dtext_to_ast(line)  # Similar concern as above
                        for pl_node in parsed_line_nodes:
                            append_to_current_li(pl_node)
                    else:
                        result.append({"type": "text", "content": line})
        else:  # Non-text node (e.g. header, quote, table element)
            is_header_node = node["type"] in {"h1", "h2", "h3", "h4", "h5", "h6", "section", "expand"}

            if is_header_node:
                # If the current node is a header, it signifies the end of any preceding list.
                # Clear the list_stack to ensure the header is not appended to a list item.
                list_stack.clear()

            # Recursively call wrap_list_items for the children of the current node.
            # This is to correctly handle lists that might be nested within this node's content
            # (e.g., a list inside a blockquote).
            if "children" in node:
                node["children"] = wrap_list_items(node["children"])

            # After processing children and potentially clearing list_stack (if it was a header):
            if list_stack and not is_header_node:
                # If list_stack is still active (meaning we are in a list context initiated by a prior text node)
                # AND the current node is NOT a header, then this node is part of the current list item.
                append_to_current_li(node)
            else:
                # If list_stack is empty (either never started, or cleared by a header)
                # OR if the current node IS a header,
                # then append this node to the main result list.
                result.append(node)
    return result


def transform_text_links(text):
    """
    Given a string of text, scan it for link syntaxes and return a list of nodes.
    Supported link formats include:
      - Basic link:  https:/e621.net
      - Delimited basic link: <https:/e621.net>
      - Masked link: "Danbooru":[https:/e621.net]  or  "ToS":[/terms_of_service]  or  "Here":[#dtext-basic-formatting]
      - Markdown style: [Danbooru](https:/e621.net)
      - Reverse Markdown: [https:/e621.net](Danbooru)
      - BBCode style: [url]https:/e621.net[/url] and [url=https:/e621.net]Danbooru[/url]
      - Wiki link: [[Kantai Collection]] and [[Kantai Collection|Kancolle]]
      - Tag search: {{kantai_collection comic}} and {{kantai_collection comic|Kancolle Comics}}
      - User link: @evazion
    """

    # Helper: wrap plain text into a text node.
    def text_node(content):
        return {"type": "text", "content": content}

    # Helper: if a URL starts with "/" or "#", prepend the base URL.
    def resolve_url(url):
        if url.startswith("/"):
            return "https:/e621.net" + url  # todo: change this to local page for wiki when everything is local
        elif url.startswith("#"):
            # Keep hash links relative to the current page
            return url
        else:
            return url

    # List of patterns, ordered from most specific to general.
    patterns = [
        # 1. External link with custom text and indicator (e.g., Wikipedia: Hatsune Miku)
        # NOTE: for wiki page #5655 External links section
        # NEEDS TO BE AT THE TOP/RUN FIRST!
        # clashes with normal/plain link detection otherwise
        (
            re.compile(r'"([^"]+)":(https?://[^\s]+)'),  # Match "Text":http(s)://URL
            lambda m: {
                "type": "a",
                "attrs": {
                    "href": m.group(2),
                    "class": "external-link",  # Add a class to indicate it's an external link
                },
                "children": [
                    text_node(m.group(1)),
                    {
                        "type": "span",
                        "attrs": {"class": "external-link-icon"},
                        "children": [text_node("🔗")],
                    },  # Add external link icon (can be styled with CSS)
                ],
            },
        ),
        # 2. Masked link: "Text":[URL] where URL can begin with http://, https://, /, or #
        (
            re.compile(r'"([^"]+)":\[((?:https?://|\/|#)[^\]]+)\]'),
            lambda m: {
                "type": "a",
                "attrs": {"href": resolve_url(m.group(2))},
                "children": [text_node(m.group(1))],
            },
        ),
        # 3. ID-based link for header: "Link Text":#dtext-id-links
        (
            re.compile(r'"([^"]+)":#([a-zA-Z0-9-_]+)'),
            lambda m: {
                "type": "a",
                "attrs": {"href": f"#{m.group(2)}"},
                "children": [text_node(m.group(1))],
            },
        ),
        # 4. Markdown style link: [Text](https:/e621.net)
        (
            re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)"),
            lambda m: {
                "type": "a",
                "attrs": {"href": m.group(2)},
                "children": [text_node(m.group(1))],
            },
        ),
        # 5. Reverse Markdown style link: [https:/e621.net](Text)
        (
            re.compile(r"\[(https?://[^\]]+)\]\(([^)]+)\)"),
            lambda m: {
                "type": "a",
                "attrs": {"href": m.group(1)},
                "children": [text_node(m.group(2))],
            },
        ),
        # 6. BBCode style without custom text: [url]https?://danbooru.donmai.us[/url]
        (
            re.compile(r"\[url\](https?://[^\[]+?)\[/url\]"),
            lambda m: {
                "type": "a",
                "attrs": {"href": m.group(1).strip()},
                "children": [text_node(m.group(1).strip())],
            },
        ),
        # 7. BBCode style with custom text: [url=https:/e621.net]Text[/url]
        (
            re.compile(r"\[url=(https?://[^\]]+)\](.*?)\[/url\]"),
            lambda m: {
                "type": "a",
                "attrs": {"href": m.group(1)},
                "children": [text_node(m.group(2))],
            },
        ),
        # 8. Delimited basic link: <https?://danbooru.donmai.us>
        (
            re.compile(r"<(https?://[^>]+)>"),
            lambda m: {
                "type": "a",
                "attrs": {"href": m.group(1)},
                "children": [text_node(m.group(1))],
            },
        ),
        # 9. Basic link: https:/e621.net (will be caught if not already transformed)
        (
            re.compile(r'(?<![">])\b(https?://[^\s<]+)\b'),
            lambda m: {
                "type": "a",
                "attrs": {"href": m.group(1)},
                "children": [text_node(m.group(1))],
            },
        ),
        # 10. Wiki link: [[Page]] or [[Page|Custom Text]]
        (
            re.compile(r"\[\[([^|\]]+)(\|([^\]]*))?\]\]"),
            lambda m: (
                lambda page_section, display_text: {
                    "type": "a",
                    "attrs": {
                        "href": "https:/e621.net/wiki_pages/"
                        + page_section[0].replace(" ", "_").lower()
                        + (("#dtext-" + page_section[1].lower()) if page_section[1] else "")
                    },
                    "children": [text_node(display_text)],
                }
            )(
                # Split page#section if exists
                m.group(1).strip().split("#") + [None],
                (
                    re.sub(r"\s*\([^)]*\)", "", m.group(1).split("#")[0].strip()).strip()
                    if not (m.group(3) and m.group(3).strip())
                    else m.group(3).strip()
                ),
            ),
        ),
        # 11. Tag search link: {{tag}} or {{tag|Custom Text}}
        (
            re.compile(r"\{\{([^|\}]+)(\|([^}]*))?\}\}"),
            lambda m: {
                "type": "a",
                "attrs": {"href": "https:/e621.net/posts?tags=" + m.group(1).strip().replace(" ", "%20")},
                "children": [
                    text_node(m.group(3).strip() if m.group(3) and m.group(3).strip() else m.group(1).strip())
                ],
            },
        ),
        # 12. User link: @username
        (
            # < > only there cause the dtext:help wiki api resp has it despite wiki not mentioning it
            re.compile(r"(?:<)?@(\w+)>?"),
            lambda m: {
                "type": "a",
                "attrs": {"href": "https:/e621.net/users?name=" + m.group(1)},
                "children": [text_node("@" + m.group(1))],
            },
        ),
        # 13. ID-based shorthand links like post #1234 or comment #5678/p2
        (
            re.compile(r"\b(" + "|".join(map(re.escape, ID_LINK_MAP.keys())) + r")\s*#(\d+)(/p(\d+))?\b"),
            lambda m: {
                "type": "a",
                "attrs": {"href": ID_LINK_MAP[m.group(1)] + m.group(2) + (f"?page={m.group(4)}" if m.group(4) else "")},
                "children": [text_node(f"{m.group(1)} #{m.group(2)}" + (f"/p{m.group(4)}" if m.group(4) else ""))],
            },
        ),
    ]

    # Process the text sequentially through all patterns.
    nodes = [text_node(text)]
    for pattern, transform in patterns:
        new_nodes = []
        # Process each existing node only if it is plain text.
        for node in nodes:
            if node["type"] != "text":
                new_nodes.append(node)
                continue

            t = node["content"]
            pos = 0
            for match in pattern.finditer(t):
                start, end = match.span()
                if start > pos:
                    new_nodes.append(text_node(t[pos:start]))
                new_nodes.append(transform(match))
                pos = end
            if pos < len(t):
                new_nodes.append(text_node(t[pos:]))
        nodes = new_nodes
    return nodes


def process_ast_links(ast):
    """
    Recursively process all text nodes in the AST so that link syntaxes are transformed.
    """
    new_ast = []
    for node in ast:
        # If it's a text node, transform it.
        if node["type"] == "text":
            new_ast.extend(transform_text_links(node["content"]))
        # Otherwise, if it has children, process them recursively.
        elif "children" in node:
            node["children"] = process_ast_links(node["children"])
            new_ast.append(node)
        else:
            new_ast.append(node)
    return new_ast


def parse_dtext_to_ast(dtext):
    # Pre-scan: temporarily remove [code] and [nodtext] blocks to prevent normalization inside them.
    placeholder_map = {}

    def placeholder_replacer(match):
        key = f"__PLACEHOLDER_{len(placeholder_map)}__"
        placeholder_map[key] = match.group(0)  # Save the entire block unchanged.
        return key

    # Replace `code`, [code]…[/code] and [nodtext]…[/nodtext] with placeholders.
    dtext = re.sub(
        r"`([^`]*)`|\[(code|nodtext)(?:=[^\]]+)?\].*?\[/\2\]",
        lambda m: f"[code]{m.group(1)}[/code]" if m.group(1) else placeholder_replacer(m),
        dtext,
        flags=re.DOTALL,
    )

    html_tag_map = {
        "strong": "b",
        "b": "b",
        "em": "i",
        "i": "i",
        "u": "u",
        "s": "s",
        "spoiler": "spoilers",
        "tn": "tn",
        "nodtext": "nodtext",
        "code": "code",
        "br": "br",
        "hr": "hr",
        "quote": "quote",
        "expand": "expand",
        "table": "table",
        "thead": "thead",
        "tbody": "tbody",
        "tr": "tr",
        "td": "td",
        "th": "th",
        "col": "col",
        "colgroup": "colgroup",
    }

    # Normalize HTML-style tags to DText-style for the rest of the text.
    for html, dtext_equiv in html_tag_map.items():
        dtext = re.sub(rf"<{html}(\s[^>]*)?>", f"[{dtext_equiv}]", dtext, flags=re.IGNORECASE)
        dtext = re.sub(rf"</{html}>", f"[/{dtext_equiv}]", dtext, flags=re.IGNORECASE)

    # Restore the original code/nodtext blocks.
    for key, original in placeholder_map.items():
        dtext = dtext.replace(key, original)

    header_pattern = re.compile(r"^(h[123456])(#[\w-]+)?\.\s*(.*?)(?=\s*$|\n|$)", re.MULTILINE)
    # NOTE: hadnles e6 section,expanded=* stuff already as normal section expanded= is part of summary
    tag_pattern = re.compile(r"\[(/?)(b|i|u|s|tn|spoilers|code|nodtext|section|quote)(?:[=,]([^\]]+))?\]")
    br_pattern = re.compile(r"\[br\]")  # linebreak
    hr_pattern = re.compile(r"\[hr\]")  # Horizon
    table_tag_pattern = re.compile(r"\[(/?)(table|thead|tbody|tr|td|th|col|colgroup)(\s+[^\]]+)?\]")

    pos = 0
    stack = [[]]  # root node list

    def tagged_matches():
        for match in header_pattern.finditer(dtext):
            yield ("header", match)
        for match in tag_pattern.finditer(dtext):
            yield ("tag", match)
        for match in table_tag_pattern.finditer(dtext):
            yield ("table_tag", match)
        for match in br_pattern.finditer(dtext):
            yield ("br", match)
        for match in hr_pattern.finditer(dtext):
            yield ("hr", match)

    def parse_attributes(attr_string):
        if not attr_string:
            return {}
        return dict(re.findall(r'(\w+)="([^"]+)"', attr_string.strip()))

    tokens = list(tagged_matches())
    tokens.sort(key=lambda x: x[1].start())

    i = 0
    while i < len(tokens):
        kind, match = tokens[i]
        start, end = match.span()

        # Add text between previous pos and current match start
        if start > pos:
            stack[-1].append({"type": "text", "content": dtext[pos:start]})
            pos = start

        if kind == "header":
            header_level = match.group(1)
            header_id = match.group(2)[1:] if match.group(2) else None
            header_content = match.group(3).strip()

            # Recursively parse header content to handle nested DText
            header_children = parse_dtext_to_ast(header_content)
            header_node = {"type": header_level, "children": header_children}
            if header_id:
                header_node["id"] = header_id

            stack[-1].append(header_node)
            # Advance pos to end of the entire header line (including newline)
            line_end = dtext.find("\n", end)
            pos = len(dtext) if line_end == -1 else line_end + 1
            # Skip processing other tokens on this line
            while i < len(tokens) and tokens[i][1].start() < pos:
                i += 1
            continue

        elif kind == "br":
            stack[-1].append({"type": "linebreak"})
            pos = end
        elif kind == "hr":
            stack[-1].append({"type": "horizon"})
            pos = end

        elif kind in ("tag", "table_tag"):
            tag = match.group(2).lower()
            closing = match.group(1) == "/"
            attr = match.group(3)
            attrs = parse_attributes(match.group(3))

            if not closing:
                if tag in ("code", "nodtext"):
                    close_tag = f"[/{tag}]"
                    close_pos = dtext.find(close_tag, end)
                    if close_pos == -1:
                        close_pos = len(dtext)
                        inner_content = dtext[end:]
                    else:
                        inner_content = dtext[end:close_pos]

                    # Append the code/nodtext node without further normalization
                    if tag == "code":
                        stack[-1].append({"type": "code", "content": inner_content})
                    elif tag == "nodtext":
                        stack[-1].append({"type": "text", "content": inner_content})

                    # Update pos to the end of the closing tag
                    new_pos = close_pos + len(close_tag)
                    # Skip tokens within the processed range
                    while i + 1 < len(tokens) and tokens[i + 1][1].start() < new_pos:
                        i += 1
                    pos = new_pos
                else:
                    new_node = {"type": tag, "children": []}
                    if tag == "expand" or tag == "section":
                        new_node["title"] = attr if attr else "Show"
                    if kind == "table_tag" and attrs:
                        new_node["attrs"] = attrs
                    stack[-1].append(new_node)
                    stack.append(new_node["children"])
                    pos = end
            else:
                # Handle closing tags (e.g., [/b], [/i])
                if len(stack) > 1:
                    stack.pop()
                pos = end

        i += 1

    # Add any remaining text after the last token
    if pos < len(dtext):
        stack[-1].append({"type": "text", "content": dtext[pos:]})

    return process_ast_links(wrap_list_items(stack[0]))


def read_file(filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)

    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def save_json(data, filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_dtext_input(
    source="txt",
    txt_path="dtextH.txt",
    json_path="ewiki_pages.json",
    csv_path="wiki_pages-2025-05-01.csv",
    target_id=43047,
):
    if source == "txt":
        with open(txt_path, "r", encoding="utf-8") as f:
            return f.read()
    elif source == "json":
        with open(json_path, "r", encoding="utf-8") as f:
            pages = json.load(f)
        for page in pages:
            if page.get("id") == target_id:
                return page.get("body", "")
        raise ValueError(f"No entry found with id={target_id}")
    elif source == "csv":
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if int(row.get("id", -1)) == target_id:
                    return row.get("body", "")
        raise ValueError(f"No entry found with id={target_id}")
    else:
        raise ValueError("Invalid source option. Use 'txt', 'json', or 'csv'.")


# "txt", "json", or "csv"
# project voltage 172159 # 11229 for ewiki
dtext_input = load_dtext_input(source="csv", target_id=10866)
# id 43047 for help:dtext 5655 for hatsune_miku; 46211 kancolle
# 5883 tag groups
# 29067 tag_group:backgrounds
# e6: 10866 optics, 1671 tg index, 4 e621:index


def filter_sections(text, exclude_keywords=None):
    if exclude_keywords is None:
        exclude_keywords = [
            "to do",
            "to add",
            "contents",
            "forum discussions",
            "see also",
            "also see",
        ]

    # Find every “[section…]” or “[\/section]” tag in order
    tag_re = re.compile(r"\[(/?)section(?:[=,][^\]]*)?\]", re.IGNORECASE)
    removals = []
    stack = []

    for m in tag_re.finditer(text):
        is_close = m.group(1) == "/"
        if not is_close:
            # Opening tag — capture its lower-cased title
            # e.g. “[section=Foo:]” or “[section,expanded=Foo:]”
            title = re.search(r"\[section(?:[=,]expanded=|=)([^\]:]+)", m.group(0), re.IGNORECASE)
            t = title.group(1).strip().lower() if title else ""
            stack.append((m.start(), t))
        else:
            # Closing tag — match to last opening
            if not stack:
                continue
            start, t = stack.pop()
            end = m.end()
            # If that section’s title matches, mark this span for removal
            if any(kw in t for kw in exclude_keywords):
                removals.append((start, end))

    # Remove all marked spans (from end→start so offsets don’t shift)
    for a, b in sorted(removals, reverse=True):
        text = text[:a] + text[b:]

    return text


# Remove content between two [section=*] tags if there is no [/section] tag in between.
def remove_unclosed_section_content(text):
    pattern_unclosed = re.compile(
        r"(\[section[^\]]*\])((?:(?!\[section[^\]]*\]).)*((?=\[section[^\]]*\])|$))", flags=re.DOTALL
    )

    def repl(m):
        content = m.group(2)
        if "[/section]" not in content:
            return m.group(1)
        return m.group(0)

    return re.sub(pattern_unclosed, repl, text)


def remove_gap_between_sections(text):
    # 1: match one closing tag
    # 2: then any number of additional closing tags + surrounding whitespace
    # 3: then *any* intervening text up to the next opening tag
    # 4: finally capture the opening tag itself
    pattern = re.compile(
        r"(\[/section\])"  # group 1: first closing
        r"((?:\s*\[/section\]\s*)*)"  # group 2: further closings + whitespace
        r"([\s\S]*?)"  # group 3: any text (minimal) up to...
        r"(\[section[^\]]+\])",  # group 4: the next opening
        flags=re.DOTALL,
    )

    def _repl(m):
        # rebuild only groups 1 + 2 + 4 → dropping group 3
        return m.group(1) + m.group(2) + m.group(4)

    return re.sub(pattern, _repl, text)


dtext_input = filter_sections(dtext_input)
# dtext_input = remove_unclosed_section_content(dtext_input)
dtext_input = remove_gap_between_sections(dtext_input)

# print(dtext_input)

# everything from top to first occurace of opening section tag
dtext_input = re.sub(r"(?s)^.*?(?=\[section[^\]]+\])", "", dtext_input)

# everything from last [/section] to bottom
dtext_input = re.sub(r"(?s)(.*\[/section\]).*$", r"\1", dtext_input)


# if there is an opening section tag but no header in between that and the first ul/li item then turn the section's title/string into a "h4. header"
def add_missing_headers(text):
    pattern = re.compile(r"\[section(?:[=,]expanded=|=)([^\]:]+)\](.*?)((?=\[section[^\]]*\])|$)", flags=re.DOTALL)

    def repl(m):
        section_title = m.group(1).strip()
        section_content = m.group(2).strip()
        # Check if there is no header before the first ul/li
        if not re.search(r"^h[123456]\.", section_content, flags=re.MULTILINE) and re.search(
            r"^\*+", section_content, flags=re.MULTILINE
        ):
            # Add an h4 header with the section title
            return f"h4. {section_title}\n{section_content}"
        return m.group(0)

    text = re.sub(pattern, repl, text)

    # Ensure a newline between a closing section tag and a following h4 tag
    text = re.sub(r"(\[/section\])(h4\.)", r"\1\n\2", text)
    return text


dtext_input = add_missing_headers(dtext_input)


# remove all [section] tags
dtext_input = re.sub(r"\[section[^\]]*\]", "", dtext_input)

# remove some simple stuff
dtext_input = dtext_input.replace("`", "")
dtext_input = dtext_input.replace("\r", "")
dtext_input = dtext_input.replace("\u003ccolor\u003e", "")

# dtext_input = dtext_input.replace("\n", "")
# print(dtext_input)
# Parse the modified DText string into an Abstract Syntax Tree (AST)
ast = parse_dtext_to_ast(dtext_input)


# Save as JSON
save_json(ast, "ast_output.json")

runa()
