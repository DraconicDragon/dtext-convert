import csv
import json
import os


def load_json(filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)
    dir_path = os.path.dirname(file_path)

    # Ensure the directory exists
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_dtext_input(
    source="txt",
    txt_path="dtextH.txt",
    json_path="wiki_pages.json",
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
                return (page.get("title", ""), page.get("body", ""))
        raise ValueError(f"No entry found with id={target_id}")

    elif source == "csv":
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if int(row.get("id", -1)) == target_id:
                    return (row.get("title", ""), row.get("body", ""))
        raise ValueError(f"No entry found with id={target_id}")

    else:
        raise ValueError("Invalid source option. Use 'txt', 'json', or 'csv'.")
