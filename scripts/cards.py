"""Gera os cards de stats e linguagens do perfil em SVG, no estilo terminal.

Roda no GitHub Actions (workflow perfil.yml) e usa o GITHUB_TOKEN do próprio repositório.
Uso: GH_USER=Tibin05 GH_TOKEN=... python3 scripts/cards.py dist
"""
import json
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

USER = os.environ["GH_USER"]
TOKEN = os.environ["GH_TOKEN"]
OUT = sys.argv[1] if len(sys.argv) > 1 else "dist"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar { totalContributions }
    }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10) { edges { size node { name } } }
      }
    }
  }
}
"""

BG, BAR, LINE, EMPTY = "#0d1117", "#161b22", "#30363d", "#21262d"
GREEN, TEXT, MUTED = "#39d353", "#c9d1d9", "#8b949e"
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
W, H = 420, 236
ROW_Y = [94 + i * 24 for i in range(6)]


def fetch():
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    if "errors" in data:
        sys.exit(f"Erro na API do GitHub: {data['errors']}")
    return data["data"]["user"]


def window(path, command, rows):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">
  <rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="10" fill="{BG}" stroke="{LINE}" stroke-width="2"/>
  <path d="M1 11a10 10 0 0 1 10-10h{W - 22}a10 10 0 0 1 10 10v23H1z" fill="{BAR}"/>
  <line x1="1" y1="34" x2="{W - 1}" y2="34" stroke="{LINE}" stroke-width="2"/>
  <circle cx="20" cy="18" r="5" fill="{LINE}"/><circle cx="36" cy="18" r="5" fill="{LINE}"/><circle cx="52" cy="18" r="5" fill="{GREEN}"/>
  <text x="{W / 2}" y="22" text-anchor="middle" font-size="12" fill="{MUTED}">{escape(USER.lower())}@github: {path}</text>
  <text x="24" y="64" font-size="13" fill="{TEXT}"><tspan fill="{GREEN}">$</tspan> {escape(command)}</text>
{rows}
</svg>
"""


def stats_card(user):
    c = user["contributionsCollection"]
    repos = user["repositories"]
    rows = [
        ("contribuições no último ano", c["contributionCalendar"]["totalContributions"]),
        ("commits no último ano", c["totalCommitContributions"]),
        ("pull requests no último ano", c["totalPullRequestContributions"]),
        ("issues no último ano", c["totalIssueContributions"]),
        ("repositórios públicos", repos["totalCount"]),
        ("estrelas recebidas", sum(r["stargazerCount"] for r in repos["nodes"])),
    ]
    svg = "\n".join(
        f'  <text x="24" y="{y}" font-size="13" fill="{MUTED}">{escape(label)}</text>'
        f'<text x="{W - 24}" y="{y}" text-anchor="end" font-size="13" font-weight="700" fill="{GREEN}">{value}</text>'
        for (label, value), y in zip(rows, ROW_Y)
    )
    return window("~/stats", "stats --resumo", svg)


def langs_card(user):
    totals = {}
    for repo in user["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            totals[name] = totals.get(name, 0) + edge["size"]
    grand = sum(totals.values()) or 1
    top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:6]

    parts = []
    for (name, size), y in zip(top, ROW_Y):
        pct = 100 * size / grand
        filled = max(1, round(pct / 100 * 16))
        blocks = "".join(
            f'<rect x="{150 + i * 11}" y="{y - 10}" width="9" height="11" rx="1" fill="{GREEN if i < filled else EMPTY}"/>'
            for i in range(16)
        )
        parts.append(
            f'  <text x="24" y="{y}" font-size="13" fill="{TEXT}">{escape(name)}</text>{blocks}'
            f'<text x="{W - 24}" y="{y}" text-anchor="end" font-size="13" fill="{MUTED}">{pct:.1f}%</text>'
        )
    return window("~/linguagens", "linguagens --top 6", "\n".join(parts))


os.makedirs(OUT, exist_ok=True)
user = fetch()
for filename, svg in (("stats.svg", stats_card(user)), ("linguagens.svg", langs_card(user))):
    with open(os.path.join(OUT, filename), "w", encoding="utf-8") as f:
        f.write(svg)
print(f"Cards gerados em {OUT}/")
