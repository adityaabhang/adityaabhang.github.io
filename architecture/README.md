# Project architecture diagrams

Each project page has a "System architecture" figure. The source of truth is one JSON spec per project in `specs/`; the figure on the page is rendered from it and styled with the site's own palette and fonts.

```
python3 make_specs.py      # write specs/*.json (edit nodes and connections here)
python3 build.py           # validate + render with Archify, inject into projects/*.html
python3 build.py drone-navigation   # one project only
```

- **Renderer:** [Archify](https://github.com/tt-a1i/archify), installed as a Claude Code skill at `~/.claude/skills/archify` (override with `ARCHIFY_DIR`). Needs Node 18 or newer. `build.py` runs Archify's own delivery check at `showcase` quality and stops on any failure.
- **Styling:** `../assets/architecture.css`. It is self-contained (its own tokens) so it also works on the older standalone IE 574 page.
- **Re-running is safe:** each figure sits between `<!-- arch:start -->` and `<!-- arch:end -->` and is replaced in place.
- **Content rule:** every label comes from that project's own page text. The low-light SLAM diagram deliberately leaves out distillation, phone captures, the personal dataset and Noctifi3r.
