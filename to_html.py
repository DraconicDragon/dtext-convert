import html
import json
import os

from html_template import CSS_CONTENT, generate_full_html


def render_with_attrs(tag, node):
    attrs = node.get("attrs", {})
    attr_html = " ".join(f'{k}="{html.escape(v)}"' for k, v in attrs.items())
    inner_html = ast_to_html(node.get("children", []))
    if attr_html:
        return f"<{tag} {attr_html}>{inner_html}</{tag}>"
    else:
        return f"<{tag}>{inner_html}</{tag}>"


def ast_to_html(ast):
    html_parts = []

    tag_map = {
        "b": "strong",
        "i": "em",
        "u": "u",
        "s": "s",
        "tn": "small",
        "spoilers": "span class='spoiler'",
        "h1": "h1",
        "h2": "h2",
        "h3": "h3",
        "h4": "h4",
        "h5": "h5",
        "h6": "h6",
        # "code" and "nodtext" are handled separately below.
    }

    for node in ast:
        node_type = node.get("type")
        if node_type == "text":
            # Split by newlines and insert <br>
            # html_parts.append(node["content"])
            # todo: not done
            lines = node["content"].split("\n")
            for i, line in enumerate(lines):
                if i > 0:
                    html_parts.append("<br>")
                html_parts.append(line)

        elif node_type == "code":
            inner = node.get("content") or ast_to_html(node.get("children", []))
            cleaned = inner.strip()  # stripping leading/trailing whitespace/newlines, could be done in dtext2ast but eh

            if "\n" in cleaned:  # Make codeblock if node_type code content has newlines
                html_parts.append(f"<pre>{html.escape(cleaned)}</pre>")
            else:
                html_parts.append(f"<code>{html.escape(cleaned)}</code>")

        elif node_type == "linebreak":
            html_parts.append("<br>")
        elif node_type == "horizon":
            html_parts.append("<hr>")

        elif node_type in tag_map:
            tag = tag_map[node_type]
            inner_html = ast_to_html(node.get("children", []))

            if node_type.startswith("h") and node_type[1:].isdigit():  # h1–h6
                # Extract heading text to use as ID
                text_content = "".join(
                    child["content"] for child in node.get("children", []) if child["type"] == "text"
                )
                header_id = "dtext-" + text_content.strip().replace(" ", "-").lower()
                html_parts.append(f'<{tag} id="{html.escape(header_id)}">{inner_html}</{tag}>')

            elif " " in tag:
                tag_name, attrs = tag.split(" ", 1)
                html_parts.append(f"<{tag_name} {attrs}>{inner_html}</{tag_name}>")

            else:
                html_parts.append(f"<{tag}>{inner_html}</{tag}>")

        elif node_type == "nodtext":
            inner = node.get("content") or ast_to_html(node.get("children", []))
            html_parts.append(f"<span>{html.escape(inner)}</span>")

        elif node_type == "a":
            # For a link node, we expect an "attrs" dictionary with a "href" attribute and text children.
            attrs = node.get("attrs", {})
            href = attrs.get("href", "#")
            inner_html = ast_to_html(node.get("children", []))
            html_parts.append(f'<a href="{href}">{inner_html}</a>')
        elif node_type == "expand":
            title = html.escape(node.get("title", "Show"))
            inner_html = ast_to_html(node.get("children", []))
            html_parts.append(
                f'<details><summary>{title}</summary><div class="expander-content">{inner_html}</div></details>'
            )
        elif node_type == "ul":
            inner_html = ast_to_html(node.get("children", []))
            html_parts.append(f"<ul>{inner_html}</ul>")
        elif node_type == "li":
            inner_html = ast_to_html(node.get("children", []))
            html_parts.append(f"<li>{inner_html}</li>")
        elif node_type == "quote":
            inner_html = ast_to_html(node.get("children", []))
            html_parts.append(f"<blockquote>{inner_html}</blockquote>")

        elif node_type in {"table", "thead", "tbody", "tr", "colgroup", "td", "th", "col"}:
            html_parts.append(render_with_attrs(node_type, node))

        else:
            # Unknown node type; fallback to rendering its children
            inner_html = ast_to_html(node.get("children", []))
            html_parts.append(inner_html)

    return "".join(html_parts)


def save_html(content, filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def save_json(data, filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_css(content, filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


# Set embed_css to True to embed CSS, or False to output an external CSS file.
embed_css = False
css_filename = "styles.css"


def runa():

    ast = load_json("ast_output.json")

    # Convert AST to HTML content (this is the inner HTML, e.g. content inside <body>)
    inner_html = ast_to_html(ast)

    # Build a full HTML document using our template
    full_html = generate_full_html(inner_html, embed_css, css_filename, css_content=CSS_CONTENT)

    save_html(full_html, "output.html")

    if not embed_css:
        save_css(CSS_CONTENT, css_filename)

    print("HTML output saved as 'output.html'")
    if not embed_css:
        print(f"CSS output saved as '{css_filename}'")


if __name__ == "__main__":
    runa()
