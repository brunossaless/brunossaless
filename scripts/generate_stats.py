#!/usr/bin/env python3
"""Gera assets/stats.svg e assets/langs.svg direto da API do GitHub.

Sem serviços de terceiros: os cards são arquivos do próprio repositório, então nunca quebram.
Uso: GH_TOKEN=... python3 scripts/generate_stats.py
"""
import json
import os
import sys
import urllib.request
from datetime import date
from html import escape
from pathlib import Path

USER = os.environ.get("GH_USER", "brunossaless")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
OUT = Path(__file__).resolve().parent.parent / "assets"
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
LANG_COLORS = {
    "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Python": "#3572A5", "Java": "#b07219",
    "Go": "#00ADD8", "C++": "#f34b7d", "HTML": "#e34c26", "CSS": "#563d7c", "Kotlin": "#A97BFF",
    "Swift": "#F05138", "Shell": "#89e051", "Dockerfile": "#384d54", "SCSS": "#c6538c", "C": "#555555",
}


def call(url, body=None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-stats"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    request = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def repos():
    page, found = 1, []
    while True:
        chunk = call(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&page={page}")
        found += chunk
        if len(chunk) < 100:
            return [r for r in found if not r["fork"]]
        page += 1


def contributions():
    query = "query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{totalContributions}}}}"
    body = json.dumps({"query": query, "variables": {"login": USER}}).encode()
    try:
        data = call("https://api.github.com/graphql", body)
        return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    except Exception as error:  # o token do Action pode não ter acesso ao GraphQL: o card segue sem esse número
        print(f"aviso: contribuições indisponíveis ({error})", file=sys.stderr)
        return None


def card(width, height, title, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">'
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="14" fill="#0d1117" stroke="#30363d"/>'
        f'<text x="24" y="38" font-family="{FONT}" font-size="17" font-weight="700" fill="#e6edf3">{escape(title)}</text>'
        f'<rect x="24" y="48" width="34" height="3" rx="1.5" fill="#a78bfa"/>{body}</svg>'
    )


def stats_card(user, mine, total):
    stars = sum(r["stargazers_count"] for r in mine)
    items = [
        ("Public repositories", len(mine), "#a78bfa"),
        ("Stars earned", stars, "#f1e05a"),
        ("Followers", user["followers"], "#22d3ee"),
        ("Contributions, last 12 months", total if total is not None else "-", "#3fb950"),
    ]
    body = ""
    for index, (label, value, color) in enumerate(items):
        x, y = 24 + (index % 2) * 200, 88 + (index // 2) * 56
        body += (
            f'<circle cx="{x + 5}" cy="{y - 6}" r="5" fill="{color}"/>'
            f'<text x="{x + 18}" y="{y}" font-family="{FONT}" font-size="26" font-weight="800" fill="#e6edf3">{escape(str(value))}</text>'
            f'<text x="{x + 18}" y="{y + 20}" font-family="{FONT}" font-size="12" fill="#8b949e">{escape(label)}</text>'
        )
    body += f'<text x="24" y="196" font-family="{FONT}" font-size="11" fill="#6e7681">Updated {date.today().isoformat()} · public data only</text>'
    return card(440, 210, "GitHub at a glance", body)


def langs_card(mine):
    totals = {}
    for repo in mine:
        for name, size in call(f"https://api.github.com/repos/{USER}/{repo['name']}/languages").items():
            totals[name] = totals.get(name, 0) + size
    for noise in ("HTML", "CSS", "SCSS", "Dockerfile", "Shell", "Objective-C", "Objective-C++", "Ruby", "Makefile", "CMake"):
        totals.pop(noise, None)
    top = sorted(totals.items(), key=lambda item: -item[1])[:6]
    whole = sum(size for _, size in top) or 1
    body, x = '<clipPath id="bar"><rect x="24" y="68" width="392" height="10" rx="5"/></clipPath><g clip-path="url(#bar)">', 24.0
    for name, size in top:
        width = 392 * size / whole
        body += f'<rect x="{x:.1f}" y="68" width="{width:.1f}" height="10" fill="{LANG_COLORS.get(name, "#8b949e")}"/>'
        x += width
    body += "</g>"
    for index, (name, size) in enumerate(top):
        cx, cy = 24 + (index % 2) * 200, 108 + (index // 2) * 26
        body += (
            f'<circle cx="{cx + 5}" cy="{cy - 4}" r="5" fill="{LANG_COLORS.get(name, "#8b949e")}"/>'
            f'<text x="{cx + 18}" y="{cy}" font-family="{FONT}" font-size="13" fill="#e6edf3">{escape(name)}'
            f'<tspan fill="#8b949e">  {100 * size / whole:.1f}%</tspan></text>'
        )
    body += f'<text x="24" y="196" font-family="{FONT}" font-size="11" fill="#6e7681">By code size across my public repositories</text>'
    return card(440, 210, "Top languages", body)


def main():
    user = call(f"https://api.github.com/users/{USER}")
    mine = repos()
    OUT.mkdir(exist_ok=True)
    (OUT / "stats.svg").write_text(stats_card(user, mine, contributions()), encoding="utf-8")
    (OUT / "langs.svg").write_text(langs_card(mine), encoding="utf-8")
    print(f"ok: {len(mine)} repositórios públicos próprios")


if __name__ == "__main__":
    main()
