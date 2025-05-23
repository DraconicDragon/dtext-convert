# DText Parser TODOs

## Tag lists

- [ ] (e6) make work
  - [ ] reminder: page 12159 doesnt work with current implementation
  - [ ] maybe make different implementation than this

## General

- [x] Fix that headers (and maybe more) are part of a `li` if header comes after it
  - [ ] Find out if this is going to be an issue for inner `li`/`ul` tags
- [ ] change css for better mobile support (tables mainly)
- [x] Handle links that refer to IDs (they should link to an anchor on the active page, not Danbooru)
  - [x] ID Links not scrolling to the id thingy
- [ ] Handle `!post #1234` links (and `* !post #1234`)
- [x] Handle HTML tags (e.g. `<tn>`, `<table>`, `<tr>`, `<td>`, etc.)
- [x] ID Link eg topic #1234/p2 not linking with page 2
- [x] Link transformations within list items (verify with [wiki page #5655](https://danbooru.donmai.us/wiki_pages/5655) external links section) note: for some reason this was the only link like that, in the code its being given an extra link emoji to signalize its an external link but other link rules are being used for external links too, also this one from 5655 is undocumented :/

## Low Priority

- [ ] Find out whats causing the enormous amount of ul and li (originates in dtext to ast looks like)
- [ ] Handle carriage returns with asterisks and headers (see `c.txt`)
- [ ] Handle paragraphs similarly to above
- [x] Handle user links enclosed in `< >` (see wiki page #43047, second table; note: it doesnt seem like `< >` is used, but it shows up like that in the wiki page, so my solution iirc is to just include those in the regex as an OR but do not have the content include those characters, i hope this wont cause issues lol, theres a similar thing with above mentioned external links)
- [ ] Make headers visually larger in CSS (or rather opposite: make overall text smaller?)
- [ ] Style links based on what they refer to (tag category colors, color-code tag types, etc.)
- [ ] However this happened: `<code>[co</code><code>de][u]code[/u][/co</code><code>de]</code>`
- [ ] Add external link icon to any external link, not just the special #5655 one
- [ ] Implement tag implications
- [ ] Implement example posts at the bottom of pages

---

## e621-Specific TODOs

- [ ] dtext id links dont work if its a masked/hyper link like in 12159 section 2, shows up as `dtext-:` (see faceless, that works)
- [ ] e6 has separate `[#id-here]` tags for tag/id hyperlinking instead of supplying with header
- [ ] Handle different header rules
- [ ] Handle backtick code blocks
- [ ] Handle inline code like `` `inline code` ``
- [ ] Handle HTML tags
- [ ] Support `[sup]` and `[sub]` tags
- [ ] Support `[color]` tags (HTML color names, tag category names, 3-6 digit hex codes)
  - [ ] Support the HTML tag version because i guess that is a thing too yay; Related to the above issue of supporting other HTML tags
- [ ] Use a separate ID-based link parser for e621 mode
- [ ] Update `post #1234` format handling to match e621
- [ ] Handle `thumb #12345` instead of `!post #1234`
- [ ] In e621, `[code]` always creates a block (use backticks for inline)
- [ ] Use `[section]` instead of `[expand]`
  - [ ] Support `[section,expanded=Title]` for always-open sections
  - [ ] Default titles are not used in e621 sections
