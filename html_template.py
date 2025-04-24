CSS_CONTENT = """/* Dark mode base */
body {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: sans-serif;
    line-height: 1.5;
    padding: 1em;
    margin: 0;
    transform: scale(0.9); /* Scale everything to 90% */
    transform-origin: top left; /* Keeps the scaling from shifting */
}

/* Headers */
h1, h2, h3, h4, h5, h6 {
    color: #f2f2f2;
    margin-top: 1em;
    margin-bottom: 0.4em;
    font-weight: 500; /* Slightly less bold */
    line-height: 1.3;
}

h1 {
    font-size: 2.2em;
}
h2 {
    font-size: 1.9em;
}
h3 {
    font-size: 1.6em;
}
h4 {
    font-size: 1.4em;
}
h5 {
    font-size: 1.2em;
}
h6 {
    font-size: 1em;
}


/* Highlight the target element, for header ID linking */
:target { 
    background-color: rgba(173, 216, 230, 0.3);  /* soft yellow highlight */
    transition: background-color 0.5s ease;
}

/* Links */
a {
    color: #89b4fa;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

/* Inline code */
code {
    background-color: #313244;
    color: #fab387;
    padding: 0.15em 0.3em;
    border-radius: 3px;
    font-family: monospace;
}

/* Spoiler tag */
span.spoiler {
    background: black;
    color: black;
    padding: 0.1em 0.2em;
    border-radius: 3px;
    transition: color 0.05s;
}

span.spoiler:hover {
    color: white;
}

/* Emphasis */
em {
    font-style: italic;
}

strong {
    font-weight: bold;
}

u {
    text-decoration: underline;
}

s {
    text-decoration: line-through;
}

small {
    font-size: 0.85em;
    color: #a6adc8;
}

/* Table styling */
table {
    width: auto;
    /* Adjusts the table width to content */
    border-collapse: collapse;
    margin-top: 0.25em;
    margin-bottom: 0.25em;
}

thead {
    background-color: #313244;
    /*dont word wrap*/
    white-space: nowrap;
}

thead th {
    color: #f2f2f2;
    text-align: left;
    padding: 0.25em;
    border-bottom: 2px solid #89b4fa;
}

tbody tr {
    background-color: #1e1e2e;
    transition: background-color 0.075s;
}

tbody tr:nth-child(even) {
    background-color: #2b2d41;
}

tbody tr:hover {
    background-color: #3a3c5a;
}

tbody td {
    padding: 0.25em;
    vertical-align: top;
    border: none;
}


/* support alignment of tr, th, and td elements */
th,
td {
    padding: 4px 8px;
    text-align: left;
    /* Default alignment */
}

th[align="center"],
td[align="center"],
tr[align="center"]>th,
tr[align="center"]>td {
    text-align: center;
}

th[align="right"],
td[align="right"],
tr[align="right"]>th,
tr[align="right"]>td {
    text-align: right;
}

th[align="justify"],
td[align="justify"],
tr[align="justify"]>th,
tr[align="justify"]>td {
    text-align: justify;
}


/* Horizon rule styling */
hr {
    border: none;
    border-top: 2px solid #585b70;
    margin: 0.5em 0;
    opacity: 0.7;
}

/* DETAILS and SUMMARY styling */
/* When closed, details don't have extra padding */
details {
    margin: 0.5em 0;
    padding: 0;
    border-radius: 3px;
    background-color: #2b2d41;
    /* Restored background color */

}

/* Styling the summary (button) stays the same */
details > summary {
    cursor: pointer;
    font-weight: bold;
    color: #cdd6f4;
    background-color: #3a3c5a;
    padding: 0.25em 0.75em;
    border-radius: 3px;
    transition: background-color 0.05s;
    line-height: 1.75em;
}

details > summary:hover {
    background-color: #4b4d6b;
}

details[open] > summary {
    border-bottom-right-radius: 0;
    border-bottom-left-radius: 0;
}

/* Using a dedicated class for the expander content so that the summary remains untouched */
.expander-content {
    margin-top: 0.5em;
    /* Space between the summary and the content */
    padding: 1em;
    /* Added more padding to make it fit inside */
    border-radius: 3px;
    /* Same rounding as before */
}


/* Base blockquote style - SLIMMER */
blockquote {
    margin: 0.2em 0;
    padding: 0.25em 0.5em;
    background-color: #2b2d41;
    border-left: 3px solid #89b4fa;
    color: #cdd6f4;
    font-style: italic;
}

/* Second level */
blockquote blockquote {
    background-color: #313244;
    border-left-color: #74c7ec;
}

/* Third level */
blockquote blockquote blockquote {
    background-color: #444a60;
    border-left-color: #a6e3a1;
}

/* Fourth and deeper */
blockquote blockquote blockquote blockquote {
    background-color: #555a6f;
    border-left-color: #f38ba8;
}

/* Multiline code blocks - SLIMMER */
pre {
    display: block;
    background-color: #181825;
    color: #cdd6f4;
    padding: 0.4em 0.65em;
    border-radius: 0;
    /* Remove rounded corners for a minimal look */
    font-family: 'Fira Code', Consolas, Monaco, 'Courier New', monospace;
    font-size: 0.85em;
    line-height: 1.3;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-word;
}

/* Base list style */
ul {
    padding-left: 1.25em;
    margin: 0;
}

/* List items */
li {
    margin: 0em 0;
    line-height: 1.25em;
}

"""


def generate_full_html(inner_html, embed_css=True, css_filename="styles.css", css_content=""):
    """Wrap inner_html with a complete HTML template.
    If embed_css is True, embeds css_content inside a <style> block.
    Otherwise, it links an external CSS file with the given css_filename."""

    if embed_css:
        head_css = f"<style>\n{css_content.strip()}\n</style>"
    else:
        head_css = f'<link rel="stylesheet" type="text/css" href="{css_filename}">'

    template = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <title>DText Output</title>
    {head_css}
  </head>
  <body>
    <div class="main-body">
      {inner_html} 
        <div class="example-posts">
      </div>
    </div>
  </body>
</html>
"""
    # todo: example posts, implications
    return template
