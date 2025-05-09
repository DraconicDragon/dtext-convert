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
            is_header_node = node["type"] in {"h1", "h2", "h3", "h4", "h5", "h6"}

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
      - Basic link:  https://danbooru.donmai.us
      - Delimited basic link: <https://danbooru.donmai.us>
      - Masked link: "Danbooru":[https://danbooru.donmai.us]  or  "ToS":[/terms_of_service]  or  "Here":[#dtext-basic-formatting]
      - Markdown style: [Danbooru](https://danbooru.donmai.us)
      - Reverse Markdown: [https://danbooru.donmai.us](Danbooru)
      - BBCode style: [url]https://danbooru.donmai.us[/url] and [url=https://danbooru.donmai.us]Danbooru[/url]
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
            return (
                "https://danbooru.donmai.us" + url
            )  # todo: change this to local page for wiki when everything is local
        elif url.startswith("#"):
            # Keep hash links relative to the current page
            return url
        else:
            return url

    # List of patterns, ordered from most specific to general.
    patterns = [
        # 1. SPECIAL External link with custom text and indicator (e.g., Wikipedia: Hatsune Miku)
        # NOTE: SPECIAL because: it's for wiki page #5655 External links section, and likely more.
        # NOTE:2 its undocumented, but external links can just be set with other masked link methods
        ### ...which is seen on page 46211 (kancolle)
        # NOTE: NEEDS TO BE AT THE TOP/RUN FIRST!
        # clashes with normal/plain link detection otherwise
        (
            re.compile(r'"([^"]+)":(https?://[^\s]+)'),  # Match "Text":http(s)://URL
            lambda m: {
                "type": "a",
                "attrs": {
                    "href": m.group(2),
                    "class": "external-link",  # Add a class to indicate it's an external link
                },
                # todo: add this icon to other external (non base-URL) links, eg: 46211 (kancolle)
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
        # 4. Markdown style link: [Text](https://danbooru.donmai.us)
        (
            re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)"),
            lambda m: {
                "type": "a",
                "attrs": {"href": m.group(2)},
                "children": [text_node(m.group(1))],
            },
        ),
        # 5. Reverse Markdown style link: [https://danbooru.donmai.us](Text)
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
        # 7. BBCode style with custom text: [url=https://danbooru.donmai.us]Text[/url]
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
        # 9. Basic link: https://danbooru.donmai.us (will be caught if not already transformed)
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
                        "href": "https://danbooru.donmai.us/wiki_pages/"
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
                "attrs": {"href": "https://danbooru.donmai.us/posts?tags=" + m.group(1).strip().replace(" ", "%20")},
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
                "attrs": {"href": "https://danbooru.donmai.us/users?name=" + m.group(1)},
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

    # Replace [code]...[/code] and [nodtext]...[/nodtext] with placeholders.
    dtext = re.sub(r"(\[(code|nodtext)(?:=[^\]]+)?\].*?\[/\2\])", placeholder_replacer, dtext, flags=re.DOTALL)

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

    header_pattern = re.compile(r"^(h[123456])(#[\w-]+)?\.\s+(.*?)(?=\s*$|\n|$)", re.MULTILINE)
    tag_pattern = re.compile(r"\[(/?)(b|i|u|s|tn|spoilers|code|nodtext|expand|quote)(?:=([^\]]+))?\]")
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
                    if tag == "expand":
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


def load_dtext_input(source="txt", txt_path="dtextH.txt", json_path="wiki_pages.json", target_id=43047):
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
    else:
        raise ValueError("Invalid source option. Use 'txt' or 'json'.")


# "txt" or "json"
#  project voltage 172159 # 11229 for ewiki
dtext_input = load_dtext_input(source="json", target_id=43047)
# id 43047 for help:dtext 5655 for hatsune_miku; 46211 kancolle
# 5883 tag groups
# 29067 tag_group:backgrounds
ast = parse_dtext_to_ast(dtext_input)


# Save as JSON
save_json(ast, "ast_output.json")

runa()

#'[See [[Tag Groups]].]\r\n\r\n[expand=Table of Contents]\r\n* 1. "About":#dtext-about\r\n* 2. "Colors":#dtext-colors\r\n* 3. "Multiple Colors":#dtext-multiple\r\n* 4. "Patterns":#dtext-patterns\r\n* 5. "Descriptive":#dtext-descriptive\r\n* 6. "Objects and Nouns":#dtext-objects\r\n* 7. "Mediums":#dtext-mediums\r\n* 8. "Background Related":#dtext-related\r\n[/expand]\r\n\r\nh4#about. About\r\n\r\nTags which describe the background of posts. Most, but not all, have "background" in their name.\r\n\r\nh4#colors. Colors\r\n\r\n* [[aqua background]]\r\n* [[beige background]] (deprecated)\r\n* [[black background]]\r\n* [[blue background]]\r\n* [[brown background]]\r\n* [[green background]]\r\n* [[grey background]]\r\n* [[orange background]]\r\n* [[pink background]]\r\n* [[purple background]]\r\n* [[red background]]\r\n* [[simple background]]\r\n** [[transparent background]]\r\n* [[white background]]\r\n* [[yellow background]]\r\n\r\nh4#multiple. Multiple Colors\r\n\r\n* [b][[colorful background]][/b]\r\n* [[gradient background]]\r\n* [[greyscale with colored background]]\r\n* [[halftone background]]\r\n* [[monochrome background]]\r\n* [[multicolored background]] (deprecated)\r\n* [[rainbow background]]\r\n** [[heaven condition]]\r\n* [[three-toned background]]\r\n* [[two-tone background]]\r\n\r\nh4#patterns. Patterns\r\n\r\n* [[argyle background]]\r\n* [[checkered background]]\r\n* [[cross background]]\r\n* [[dithered background]]\r\n* [[dotted background]]\r\n* [[grid background]]\r\n* [[honeycomb background]]\r\n* [[lace background]]\r\n* [[marble background]]\r\n* [[mosaic background]]\r\n* [b][[patterned background]][/b]\r\n* [[plaid background]]\r\n* [[polka dot background]]\r\n* [[spiral background]]\r\n* [[splatter background]]\r\n* [[striped background]]\r\n** [[diagonal-striped background]]\r\n* [[sunburst background]]\r\n* [[triangle background]]\r\n\r\nh4#descriptive. Descriptive\r\n* [[abstract background]]\r\n* [[blurry background]]\r\n* [[bright background]]\r\n* [[dark background]]\r\n* [[drama layer]]\r\n\r\nh4#objects. Objects and Nouns\r\n\r\n* [[animal background]] ([[animal]])\r\n* [[bubble background]] ([[bubble]])\r\n* [[butterfly background]] ([[butterfly]])\r\n* [[card background]] ([[playing_card]])\r\n* [[cloud background]] ([[cloud]])\r\n* [[fiery background]] ([[fire]])\r\n* [[flag background]] ([[flag]])\r\n* [[floral background]] ([[flower]])\r\n** [[rose background]] ([[rose]])\r\n* [[food-themed background]] ([[food]])\r\n* [[fruit background]] ([[fruit]])\r\n** [[strawberry background]] ([[strawberry]])\r\n* [[heart background]] ([[heart]])\r\n* [[leaf background]] ([[leaf]])\r\n* [[lightning background]] ([[lightning]])\r\n* [[paw print background]] ([[paw print]])\r\n* [[rabbit background]] ([[rabbit]])\r\n* [[snowflake background]] ([[snowflakes]])\r\n* [[sofmap background]] ([[sofmap]])\r\n* [[sparkle background]] ([[sparkle]])\r\n* [[spider web background]] ([[spider web]])\r\n* [[star symbol background]] ([[star_(symbol)]])\r\n* [[starry background]] (deprecated)\r\n* [[text background]] ([[text focus]])\r\n* [[weapon background]] ([[weapon]])\r\n\r\nh4#mediums. Mediums\r\n* [[3d_background]]\r\n* [[AI-generated background]]\r\n* [[collage background]]\r\n* [[paneled background]]\r\n* [[photo background]]\r\n* [[game screenshot background]]\r\n* [[paper background]]\r\n* [[screenshot background]]\r\n* [[sketch background]]\r\n* [[watercolor background]]\r\n\r\nh4#related. Background Related\r\n* [[backlighting]]\r\n* [[blending]]\r\n* [[chibi inset]]\r\n* [[imageboard colors]]\r\n* [[projected inset]]\r\n* [[zoom layer]]'
