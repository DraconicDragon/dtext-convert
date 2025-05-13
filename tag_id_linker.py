import os

import pandas as pd


def get_tag_info(df, tag):
    """
    Searches for a tag in the "tag" column of e6tags.csv and returns the "id" and "category" from that row.
    Expects a dataframe and the tag to search for.
    Returns:
        tuple: A tuple containing the "id" and "category" values, or (None, None) if the tag is not found.
    """
    try:

        # Find the row where the tag matches
        row = df[df["name"] == tag]

        # If the tag is found, return the id and category
        if not row.empty:
            return row["id"].iloc[0], row["category"].iloc[0]
        else:
            return None, None

    except FileNotFoundError:
        print("Error: e6tags.csv not found in the same directory as the script.")
        return None, None

    except Exception as e:
        print(f"An error occurred: {e}")
        return None, None


if __name__ == "__main__":
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    csv_path = os.path.join(script_dir, "e6tags.csv")

    e6_tags_df = pd.read_csv(csv_path)

    tag_to_search = "dutch_angle"

    tag_id, tag_category = get_tag_info(e6_tags_df, tag_to_search)

    if tag_id is not None and tag_category is not None:
        print(f"Tag: {tag_to_search}, ID: {tag_id}, Category: {tag_category}")
    else:
        print(f"Tag '{tag_to_search}' not found in e6tags.csv")
