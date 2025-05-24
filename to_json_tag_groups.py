import os
import re

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

# Construct the full path to the CSV files
csv_path = os.path.join(script_dir, "tags-2025-05-13.csv")
wiki_csv_path = os.path.join(script_dir, "wiki_pages-2025-05-01.csv")

# Load CSVs into DataFrames
e6_tags_df = pd.read_csv(csv_path)
wiki_pages_df = pd.read_csv(wiki_csv_path)

# Create dictionary for faster lookups - maps tag names to (id, category, post_count) tuples
tag_dict = dict(zip(e6_tags_df["name"], zip(e6_tags_df["id"], e6_tags_df["category"], e6_tags_df["post_count"])))

# Create a wiki_dict mapping title to id for fast lookup
wiki_dict = dict(zip(wiki_pages_df["title"], wiki_pages_df["id"]))


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
    - name (from href endpoint), dname (display name from <a> text)
    - optional note (formerly description)
    - optional subtags
    - marker flags
    """
    entry = {}
    children = li_node.get("children", [])

    # 1) Find the <a> tag (should be first child)
    a = next((c for c in children if c.get("type") == "a"), None)
    if not a:
        # print("No <a> tag found in li_node")
        return None

    href = a.get("attrs", {}).get("href")
    if href:
        # Extract the last part after /wiki_pages/
        match = re.search(r"/wiki_pages/([^/?#]+)", href)
        if match:
            name = match.group(1)
        else:
            name = extract_text(a["children"]).strip().replace(" ", "_").lower()
    else:
        name = extract_text(a["children"]).strip().replace(" ", "_").lower()

    entry["name"] = name

    # Optionally add display name as dname key
    # if True:
    #     dname = extract_text(a["children"]).strip()
    #     entry["dname"] = dname

    if not is_index_tg:
        try:
            tag_info = tag_dict.get(name, (None, None, None))  # 0: id; 1: category_id; 2: post_count

            if tag_info[2] == 0:  # ignore tags with 0 posts
                # Check if this tag has a wiki page
                wiki_id = wiki_dict.get(name)
                if wiki_id is not None:
                    entry["id"] = -1
                    entry["has_wiki"] = int(wiki_id)
                    entry["invalid_reason"] = "no_posts,has_wiki"
                    print(f"- \033[1m\033[93mTag '\033[94m{name}\033[93m' has 0 posts but has wiki page (id={wiki_id}), marking as junction\033[0m")
                else:
                    print(f"- \033[1m\033[93mTag '\033[94m{name}\033[93m' has 0 posts, marking invalid\033[0m")
                    entry["id"] = -1
                    entry["invalid_reason"] = "no_posts"  # NOTE: probably temporary thing
            else:
                entry["id"] = int(tag_info[0])
        except (TypeError, ValueError):
            print(f"- \033[1m\033[91mTag '\033[94m{name}\033[91m' not found or invalid in e6tags.csv\033[0m")
            entry["id"] = -1  # default value to set if none so key exists but easier to see that its invalid
            entry["invalid_reason"] = "not found/invalid tag"
    else:
        if href:
            endpoint = re.sub(r".*?/wiki_pages", "", href)
            entry["endpoint"] = endpoint

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
            elif note in ("-", "---"):
                pass
            else:
                entry["note"] = note

    # 3) Subtags: a nested <ul> inside this <li>
    sub_ul = next((c for c in children if c.get("type") == "ul"), None)
    if sub_ul:
        subtags = {}
        index = 0  # Initialize counter for numeric keys
        for sub_li in sub_ul.get("children", []):
            if sub_li.get("type") != "li":
                continue
            sub_entry = parse_li(sub_li, is_index_tg=is_index_tg)
            if sub_entry:
                # Use index as key instead of entry name
                subtags[str(index)] = sub_entry
                index += 1
        if subtags:
            entry["subtags"] = subtags

    # print("Parsed li entry:", entry)
    return entry


def ast_to_tag_groups(ast, dtext_title, page_id):
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
            "id": page_id,
            "categories": {
                str(index): {"category_name": group["group_name"], "groups": group["tags"]}
                for index, group in enumerate(groups)
            },
        }  # index tag group gets special key names to differentiate it more

    else:
        output = {
            "title": f"{dtext_title}",
            "id": page_id,
            "groups": {
                str(index): {"group_name": group["group_name"], "tags": group["tags"]}
                for index, group in enumerate(groups)
            },
        }

    return output


def main_tag_groups(dtext_title, page_id=-1):
    ast = load_json("ast_output.json")
    tag_groups = ast_to_tag_groups(ast, dtext_title, page_id=page_id)
    dtext_title = dtext_title.replace("tag_group:", "")

    new_tag_groups = {}
    for group_title, group_tags in tag_groups.items():
        if group_tags:
            new_tag_groups[group_title] = group_tags

    tag_groups = new_tag_groups
    if "groups" not in tag_groups:
        print(f"- No 'groups' key in {dtext_title} found, skipping.")
        return  # Abort the function if there's no "groups"

    save_json(tag_groups, f"tag_groups/{dtext_title}.json")
    print(f"- Wrote {dtext_title} tag group to tag_groups/{dtext_title}.json\n")


if __name__ == "__main__":
    main_tag_groups("thingies")
