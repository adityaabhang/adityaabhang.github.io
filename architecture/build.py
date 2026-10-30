#!/usr/bin/env python3
"""Render specs/*.json with Archify and inject the SVGs into the project pages.

    python3 make_specs.py     # (re)write specs/*.json
    python3 build.py          # validate + render + inject into projects/*.html
    python3 build.py drone-navigation   # one project only

Needs Node >= 18 and the Archify skill (default ~/.claude/skills/archify).
Each figure sits between <!-- arch:start --> and <!-- arch:end --> markers, so
re-running replaces it in place. Styling lives in assets/architecture.css.
"""
import glob, html, json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
ARCHIFY = os.environ.get("ARCHIFY_DIR", os.path.expanduser("~/.claude/skills/archify"))
NODE_FALLBACK = os.path.expanduser("~/conda_envs/envs/node22/bin")

# slug -> (heading the figure goes before, one-line intro, caption)
PAGES = {
    "low-light-slam": (
        r"Tech Stack",
        "How a dark frame becomes a trajectory on the Jetson, and how the noise sweep and metric harness measure it.",
        "<b>Solid</b> arrows are the live pipeline on the Jetson AGX Orin carried by Spot. "
        "<b>Dashed</b> arrows are the offline noise-sweep path and the CPU fallback for the pose solve."),
    "drone-navigation": (
        r"Tech Stack",
        "Perception and planning stay separate. One bridge node turns where the person is going into a goal for the planner.",
        "The bridge never plans a path: SUPER keeps full authority over obstacle avoidance."),
    "ie574-warehouse-kitting": (
        r"Control Architecture",
        "One coordinator sequences five robotic subsystems, and no robot talks directly to another.",
        "<b>Solid</b> arrows are coordinator signals (request, busy, done). <b>Dashed</b> arrows are the physical material flow. "
        "An order counts as complete only at final tray unloading."),
    "medicine-dispenser": (
        r"Tech Stack",
        "The Raspberry Pi schedules doses, drives the singulation drum, and reads two sensors.",
        "Jam detection comes from monitoring the motor current; the hopper sensor reports fill level."),
    "multi-robot-transport": (
        r"Tech Stack",
        "One shared environment, three solvers, one benchmark.",
        "Any joint action that would break the fixed inter-agent distance is masked out before the solvers see it."),
    "tds-plasma-monitoring": (
        r"Tech Stack",
        "Two sensor signals become a live thickness check on Grafana.",
        "Developed and validated on Google Colab, then shipped to run on the client's Raspberry Pi 4, installed on site. "
        "The <b>dashed</b> ML model is the backup for noisy edge cases."),
    "terrain-path-planning": (
        r"Tech Stack",
        "Semantic terrain classes become traversal costs, so the planners prefer smooth ground over merely passable ground.",
        "<b>Dashed</b>: the binary-occupancy baseline that both planners are benchmarked against."),
}

START, END = "<!-- arch:start -->", "<!-- arch:end -->"


def node_env():
    env = dict(os.environ, ARCHIFY_UPDATE_CHECK_DISABLED="1")
    if not shutil.which("node") and os.path.isdir(NODE_FALLBACK):
        env["PATH"] = NODE_FALLBACK + os.pathsep + env["PATH"]
    return env


def render_svg(slug, tmp):
    spec = os.path.join(HERE, "specs", slug + ".json")
    out = os.path.join(tmp, slug + ".html")
    r = subprocess.run(["node", "bin/archify.mjs", "deliver", "architecture", spec, out,
                        "--quality", "showcase", "--json"],
                       cwd=ARCHIFY, capture_output=True, text=True, env=node_env())
    try:
        res = json.loads(r.stdout)
    except ValueError:
        raise SystemExit(f"{slug}: archify gave no JSON\n{r.stdout[:400]}\n{r.stderr[:400]}")
    if r.returncode != 0 or not res.get("ok"):
        raise SystemExit(f"{slug}: archify deliver failed\n{json.dumps(res, indent=1)[:1500]}")
    page = open(out, encoding="utf-8").read()
    svgs = re.findall(r"<svg\b.*?</svg>", page, re.S)
    if not svgs:
        raise SystemExit(f"{slug}: no <svg> in the rendered artifact")
    return max(svgs, key=len)


def tidy(svg, slug, title):
    """Static-embedding cleanup: drop viewer-only hooks, namespace ids, add a11y text."""
    svg = re.sub(r"<!--.*?-->", "", svg, flags=re.S)
    # interactive-viewer attributes do nothing on a static page and add empty tab stops
    svg = re.sub(r'\s(tabindex|aria-pressed|data-detail-anchor|data-composition-points)="[^"]*"', "", svg)
    svg = re.sub(r'\srole="button"', "", svg)
    svg = re.sub(r'\saria-label="Focus [^"]*"', "", svg)
    # namespace ids so several figures could share a page
    for old in set(re.findall(r'\sid="((?:arrowhead[\w-]*)|grid|archify-diagram-\w+)"', svg)):
        new = f"{slug}-{old}"
        svg = svg.replace(f'id="{old}"', f'id="{new}"').replace(f"url(#{old})", f"url(#{new})")
        svg = svg.replace(f'"{old} ', f'"{new} ').replace(f' {old}"', f' {new}"')
    svg = svg.replace('aria-labelledby="archify-diagram-title archify-diagram-description"',
                      f'aria-labelledby="{slug}-archify-diagram-title {slug}-archify-diagram-description"')
    svg = re.sub(r'<desc id="[^"]*">.*?</desc>',
                 f'<desc id="{slug}-archify-diagram-description">{html.escape(title)}. Boxes are components and arrows show what flows between them.</desc>',
                 svg, flags=re.S)
    svg = re.sub(r"\n\s*\n+", "\n", svg)
    return svg.strip()


def block(slug, svg, intro, caption):
    return (f'{START}\n<div class="arch-wrap" data-reveal role="group" aria-labelledby="{slug}-arch-cap">\n'
            f'  <div class="arch-cap" id="{slug}-arch-cap">System architecture</div>\n'
            f'  <p class="arch-sub">{intro}</p>\n'
            f'  <figure class="arch-fig">\n    <p class="arch-hint">Swipe sideways to see the whole diagram.</p>\n    <div class="arch-scroll" tabindex="0" role="region" aria-label="Architecture diagram, scrolls sideways on small screens">\n'
            f'{svg}\n    </div>\n    <figcaption>{caption}</figcaption>\n  </figure>\n</div>\n{END}\n')


def inject(slug, blk, before):
    path = os.path.join(SITE, "projects", slug + ".html")
    s = open(path, encoding="utf-8").read()
    if START in s:
        s = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", lambda m: blk, s, flags=re.S)
    else:
        pat = re.compile(r"(\s*)(<h2[^>]*>\s*" + re.escape(before) + r"\s*</h2>)")
        m = pat.search(s)
        if not m:
            raise SystemExit(f"{slug}: could not find <h2>{before}</h2> to place the figure before")
        s = s[:m.start()] + "\n" + blk + m.group(1) + m.group(2) + s[m.end():]
    link = '<link rel="stylesheet" href="../assets/architecture.css" />'
    fonts = ('<link rel="preconnect" href="https://fonts.googleapis.com" />\n  '
             '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />\n  '
             '<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet" />')
    add = []
    if "fonts.googleapis.com" not in s:
        add.append(fonts)                       # older standalone pages don't load the site fonts
    if link not in s:
        add.append(link)
    if add:
        s = s.replace("</head>", "  " + "\n  ".join(add) + "\n</head>", 1)
    open(path, "w", encoding="utf-8").write(s)


def main(names):
    todo = names or list(PAGES)
    with tempfile.TemporaryDirectory() as tmp:
        for slug in todo:
            before, intro, caption = PAGES[slug]
            title = json.load(open(os.path.join(HERE, "specs", slug + ".json")))["meta"]["title"]
            svg = tidy(render_svg(slug, tmp), slug, title)
            inject(slug, block(slug, svg, intro, caption), before)
            print(f"{slug}: ok ({len(svg) // 1024} KB svg)")


if __name__ == "__main__":
    main(sys.argv[1:])
