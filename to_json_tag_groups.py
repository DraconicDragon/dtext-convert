import json
import os

import pandas as pd

from file_operations import load_json, save_json

MARKERS = {
    # currently the markers are for e621 unless noted otherwise (e.g.: "deprecated")
    "*": "incomplete",  # a tag_group is incomplete or hasn't been updated in over 3 months
    "[!]": "rare",  # used on <10 posts as of date above
    "[?]": "uncertain",  # ***possibly not valid***, but have >10 post count
    "(deprecated)": "deprecated",  # tag is deprecated (for danbooru)
}

# todo: doesnt handle subsections yet
# NOTE: well maybe i can do this in ast already, but need to find a way to have it inside the li maybe
# or some other way

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the full path to the CSV file
csv_path = os.path.join(script_dir, "e6tags.csv")

# Load CSV into DataFrame
e6_tags_df = pd.read_csv(csv_path)

# Create dictionary for faster lookups - maps tag names to (id, category) tuples
# Time complexity of O(1) for lookups while pandas DF or list is O(n) where n = num. of rows
tag_dict = dict(zip(e6_tags_df["name"], zip(e6_tags_df["id"], e6_tags_df["category"])))


def extract_text(nodes):
    """Concatenate all text content from a list of AST nodes."""
    parts = []
    for n in nodes:
        if n.get("type") == "text":
            parts.append(n.get("content", ""))
        elif "children" in n:
            parts.append(extract_text(n["children"]))
    return "".join(parts)


def parse_li(li_node, is_index_tg=False):
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
        # print("No <a> tag found in li_node")
        return None
    name = extract_text(a["children"]).strip()

    # possibly leads to false positives but idk
    # actually its probably easier to give this IDs of -1
    # and then look over them to see if they are really invalid
    # if "🔗" in name:
    #     return None

    # Detect markers in the name itself
    # for marker, field in MARKERS.items():
    #     if marker in name:
    #         entry[field] = True
    #         name = name.replace(marker, "")

    if not is_index_tg:
        name = name.replace(" ", "_").lower()

        try:
            tag_info = tag_dict.get(name, (None, None))  # 0: id; 1: category_id
            entry["id"] = int(tag_info[0])
            entry["cat_id"] = int(tag_info[1])  # todo: maybe drop category id? not sure if useful
        except (TypeError, ValueError):
            print(f"- \033[1m\033[91mTag '\033[94m{name}\033[91m' not found or invalid in e6tags.csv\033[0m")
            entry["id"] = -1  # default value to set if none so key exists but easier to see that its invalid
            entry["cat_id"] = -1

    entry["name"] = name

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
            sub_entry = parse_li(sub_li, is_index_tg=is_index_tg)
            if sub_entry:
                # Use index as key instead of entry name
                subgroup[str(index)] = sub_entry
                index += 1
        if subgroup:
            entry["subgroup"] = subgroup

    # print("Parsed li entry:", entry)
    return entry


def ast_to_tag_groups(ast, dtext_title):
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
            current = {"group_name": title, "tags": {}}  # Use "group_name" for group name
            groups.append(current)
            # print("Found header:", title)
        elif ntype == "ul" and current is not None:
            # parse each <li> into an entry
            index = 0  # Initialize counter for numeric keys
            for li in node.get("children", []):
                if li.get("type") != "li":
                    continue

                entry = parse_li(li, is_index_tg=(dtext_title in ("tag_group:index", "tag_groups")))

                if entry:
                    # Use index as key instead of entry name
                    current["tags"][str(index)] = entry
                    index += 1

    # Convert list of groups into a dict with numerical indices
    if dtext_title in ("tag_group:index", "tag_groups"):
        output = {
            "title": f"{dtext_title}",
            "categories": {
                str(index): {"category_name": group["group_name"], "groups": group["tags"]}
                for index, group in enumerate(groups)
            },
        }  # index tag group gets special key names to differentiate it more

    else:
        output = {
            "title": f"{dtext_title}",
            "groups": {
                str(index): {"group_name": group["group_name"], "tags": group["tags"]}
                for index, group in enumerate(groups)
            },
        }

    return output


def main_tag_groups(dtext_title):
    ast = load_json("ast_output.json")
    tag_groups = ast_to_tag_groups(ast, dtext_title)

    new_tag_groups = {}
    for group_title, group_tags in tag_groups.items():
        if group_tags:
            new_tag_groups[group_title] = group_tags

    tag_groups = new_tag_groups
    save_json(group_tags, f"tag_groups/{dtext_title.replace("tag_group:", "")}.json")
    print(f"- Wrote {group_title} tag group to tag_groups/{dtext_title.replace("tag_group:", "")}.json\n")


if __name__ == "__main__":
    main_tag_groups("thingies")
