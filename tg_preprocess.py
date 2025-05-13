import re

# order is important


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

# NOTE: this has like 0 actual testing on it and if it misses something/deletes too much then idk
# borked i guess?
def main_preprocess(dtext_input):
    # First apply basic filtering
    dtext_input = filter_sections(dtext_input)
    dtext_input = add_missing_headers(dtext_input)
    
    # Extract only the actual tag group sections (headers followed by bullet lists with wiki links)
    tag_sections = []
    
    # Find all h4 headers and content sections
    header_pattern = re.compile(r"(h4\..*?:)[\s\n]*(.*?)(?=h[1-6]\.|\Z)", re.DOTALL)
    
    for match in header_pattern.finditer(dtext_input):
        header = match.group(1).strip()
        content = match.group(2).strip()
        
        # Only keep headers that have actual bullet list content with wiki links
        if content and "*" in content and "[[" in content and "]]" in content:
            tag_sections.append(f"{header}\n\n{content}")
    
    # Rejoin the extracted sections
    if tag_sections:
        dtext_input = '\n\n'.join(tag_sections)
    
    # Remove ALL section tags properly
    dtext_input = re.sub(r"\[section[^\]]*\]", "", dtext_input)  # Opening tags
    dtext_input = re.sub(r"\[/section\]", "", dtext_input)       # Closing tags
    
    # Remove anchor tags with no content
    dtext_input = re.sub(r"\n\[#[^\]]*\]\s*\n", "\n\n", dtext_input)
    
    # Remove some simple stuff
    dtext_input = dtext_input.replace("`", "")
    dtext_input = dtext_input.replace("\r", "")
    dtext_input = dtext_input.replace("\u003ccolor\u003e", "")
    
    return dtext_input