# DText Parser TODOs

## General
- [ ] Handle links that refer to IDs (they should link to an anchor on the active page, not Danbooru)
- [ ] Handle `!post #1234` links
- [x] Handle HTML tags (e.g. `<tn>`, `<table>`, `<tr>`, `<td>`, etc.)
- [ ] Handle tag implications
- [ ] Handle example posts at the bottom of pages
- [ ] ID Link eg topic #1234/p2 not linking with page 2
- [ ] Link transformations within list items (verify with [wiki page #5655](https://danbooru.donmai.us/wiki_pages/5655) external links section)


## Low Priority
- [ ] Handle carriage returns with asterisks and headers (see `c.txt`)
- [ ] Handle paragraphs similarly to above
- [ ] Handle user links enclosed in `< >` (see wiki page #43047, second table)
- [ ] Make headers visually larger in CSS (or rather opposite: make overall text smaller?)
- [ ] Style links based on what they refer to (tag category colors, color-code tag types, etc.)
- [ ] However this happened: `<code>[co</code><code>de][u]code[/u][/co</code><code>de]</code>`

---

## e621-Specific TODOs

- [ ] Handle backtick code blocks
- [ ] Handle inline code like `` `inline code` ``
- [ ] Support `[sup]` and `[sub]` tags
- [ ] Support `[color]` tags (HTML color names, tag category names, 3-6 digit hex codes)
- [ ] Use a separate ID-based link parser for e621 mode
- [ ] Update `post #1234` format handling to match e621
- [ ] Handle `thumb #12345` instead of `!post #1234`
- [ ] In e621, `[code]` always creates a block (use backticks for inline)
- [ ] Use `[section]` instead of `[expand]`
  - [ ] Support `[section,expanded=Title]` for always-open sections
  - [ ] Default titles are not used in e621 sections
