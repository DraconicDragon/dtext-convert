import json
import os

import pandas as pd

from tag_id_linker import get_tag_info

MARKERS = {
    "*": "incomplete",  # a tag_group is incomplete or hasn't been updated in over 3 months
    "[!]": "rare",  # used on <10 posts as of date above
    "[?]": "uncertain",  # ***possibly not valid***, but have >10 post count
}

# todo: doesnt handle subsections yet
# NOTE: well maybe i can do this in ast already, but need to find a way to have it inside the li maybe
# or some other way

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the full path to the CSV file
csv_path = os.path.join(script_dir, "e6tags.csv")

e6_tags_df = pd.read_csv(csv_path)


def extract_text(nodes):
    """Concatenate all text content from a list of AST nodes."""
    parts = []
    for n in nodes:
        if n.get("type") == "text":
            parts.append(n.get("content", ""))
        elif "children" in n:
            parts.append(extract_text(n["children"]))
    return "".join(parts)


def parse_li(li_node):
    """
    Parse an <li> node into a tag entry:
    - name, link (from <a>)
    - optional note (formerly description)
    - optional subgroup
    - marker flags
    """
    entry = {}
    children = li_node.get("children", [])

    # 1) Find the <a> tag (should be first child)
    a = next((c for c in children if c.get("type") == "a"), None)
    if not a:
        print("No <a> tag found in li_node")
        return None
    name = extract_text(a["children"]).strip()

    # possibly leads to false positives but idk
    # actually its probably easier to give this IDs of -1
    # and then look over them to see if they are really invalid
    # if "🔗" in name:
    #     return None

    # Detect markers in the name itself
    for marker, field in MARKERS.items():
        if marker in name:
            entry[field] = True
            name = name.replace(marker, "")

    name = name.replace(" ", "_").lower()

    entry["name"] = name

    try:
        tag_info = get_tag_info(e6_tags_df, name)  # 0: id; 1: category_id
        entry["id"] = int(tag_info[0])
        entry["cat_id"] = int(tag_info[1])
    except (TypeError, ValueError):
        print(f"\033[1m\033[91mTag '\033[94m{name}\033[91m' not found or invalid in e6tags.csv\033[0m")
        entry["id"] = -1  # default value to set if none so key exists but easier to see that its invalid
        entry["cat_id"] = -1

    # 2) Note: any text nodes after the <a>, with markers stripped
    note_nodes = []
    found_a = False
    for c in children:
        if c is a:
            found_a = True
            continue
        if found_a and c.get("type") == "text":
            raw = c.get("content", "")
            # detect markers in raw
            for marker, field in MARKERS.items():
                if marker in raw:
                    entry[field] = True
            # strip markers from raw for note
            cleaned = raw
            for m in MARKERS.keys():
                cleaned = cleaned.replace(m, "")
            note_nodes.append(cleaned)
    if note_nodes:
        note = "".join(note_nodes).strip()
        if note:
            if note.startswith("- "):
                note = note[2:]
            entry["note"] = note

    # 3) Subgroup: a nested <ul> inside this <li>
    sub_ul = next((c for c in children if c.get("type") == "ul"), None)
    if sub_ul:
        subgroup = {}
        index = 0  # Initialize counter for numeric keys
        for sub_li in sub_ul.get("children", []):
            if sub_li.get("type") != "li":
                continue
            sub_entry = parse_li(sub_li)
            if sub_entry:
                # Use index as key instead of entry name
                subgroup[str(index)] = sub_entry
                index += 1
        if subgroup:
            entry["subgroup"] = subgroup

    print("Parsed li entry:", entry)
    return entry


def ast_to_tag_groups(ast):
    """
    Walk the top-level AST:
    - on header: start new group
    - on ul: parse all li under current group
    """
    groups = []
    current = None

    for node in ast:
        ntype = node.get("type", "")
        # headers h1–h6
        if ntype.startswith("h") and ntype[1:].isdigit():
            title = extract_text(node.get("children", [])).strip()
            current = {"title": title, "tags": {}}
            groups.append(current)
            print("Found header:", title)
        elif ntype == "ul" and current is not None:
            # parse each <li> into an entry
            index = 0  # Initialize counter for numeric keys
            for li in node.get("children", []):
                if li.get("type") != "li":
                    continue
                entry = parse_li(li)
                if entry:
                    # Use index as key instead of entry name
                    current["tags"][str(index)] = entry
                    index += 1

    # Convert list of {title,tags} into a dict-of-dicts
    output = {g["title"]: g["tags"] for g in groups}
    return output


def main():
    ast = load_json("ast_output.json")
    tag_groups = ast_to_tag_groups(ast)

    new_tag_groups = {}
    for group_title, group_tags in tag_groups.items():
        if group_tags:
            new_tag_groups[group_title] = group_tags

    tag_groups = new_tag_groups

    save_json(tag_groups, "tag_groups.json")
    print(f"Wrote {len(tag_groups)} groups to tag_groups.json")


def load_json(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
