#!/usr/bin/env python3
"""Copie locale du backlog GitHub (issues ouvertes) dans BACKLOG.md.

Les US à faire vivent dans les issues GitHub du dépôt (labels ``us`` / ``epic:E*``,
jalon = épic, Project « Comic Collection »). Ce script les recopie dans ``BACKLOG.md``
(non versionné) pour une lecture rapide, hors ligne, en début de session.

Usage :
    python3 tools/sync_backlog.py            # issues ouvertes
    python3 tools/sync_backlog.py --closed 10  # + les 10 dernières fermées

Prérequis : GitHub CLI (``gh``) authentifié sur le dépôt.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "BACKLOG.md"
FIELDS = "number,title,labels,milestone,body,url,updatedAt,closedAt,state"


def _gh_issues(state, limit):
    cmd = ["gh", "issue", "list", "--state", state, "--limit", str(limit), "--json", FIELDS]
    try:
        out = subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        sys.exit(f"gh issue list a échoué : {getattr(exc, 'stderr', exc)}")
    return json.loads(out)


def _labels(issue):
    return [label["name"] for label in issue.get("labels", [])]


def _group(issue):
    milestone = issue.get("milestone") or {}
    if milestone.get("title"):
        return milestone["title"]
    return "Bugs" if "bug" in _labels(issue) else "Sans épic"


def _render(open_issues, closed_issues):
    lines = [
        "# Backlog (copie locale des issues GitHub)",
        "",
        f"> Généré le {datetime.now():%Y-%m-%d %H:%M} par `tools/sync_backlog.py` — ne pas éditer :",
        "> la source est GitHub (issues + Project). Relancer le script après chaque changement.",
        "",
    ]
    groups = {}
    for issue in sorted(open_issues, key=lambda i: i["number"]):
        groups.setdefault(_group(issue), []).append(issue)
    lines.append("## Sommaire")
    lines.append("")
    for group, issues in sorted(groups.items()):
        lines.append(f"- **{group}** : " + ", ".join(f"#{i['number']} {i['title']}" for i in issues))
    lines.append("")
    for group, issues in sorted(groups.items()):
        lines += [f"## {group}", ""]
        for issue in issues:
            labels = ", ".join(_labels(issue))
            lines += [
                f"### #{issue['number']} — {issue['title']}",
                "",
                f"{issue['url']} · labels : {labels or '—'} · màj {issue['updatedAt'][:10]}",
                "",
                (issue.get("body") or "_(pas de description)_").strip(),
                "",
            ]
    if closed_issues:
        lines += ["## Fermées récemment", ""]
        for issue in closed_issues:
            lines.append(f"- #{issue['number']} {issue['title']} (fermée le {(issue.get('closedAt') or '')[:10]})")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--closed", type=int, default=0, help="nombre d'issues fermées à lister")
    args = parser.parse_args()
    open_issues = _gh_issues("open", 200)
    closed_issues = _gh_issues("closed", args.closed) if args.closed else []
    OUTPUT.write_text(_render(open_issues, closed_issues), encoding="utf-8")
    print(f"{OUTPUT.name} : {len(open_issues)} issue(s) ouverte(s).")


if __name__ == "__main__":
    main()
