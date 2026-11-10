#!/usr/bin/env python3
"""Publie une release d'un dépôt Comic Collection (public ou privé).

Organisation : le développement se fait sur ``19.0-dev`` ; ``19.0`` ne reçoit que des
versions publiées (lue par l'Odoo Apps Store et le staging). Une release :

1. vérifie : branche ``19.0-dev``, arbre propre, à jour avec ``origin`` ; ``19.0`` peut
   avancer en fast-forward ; la CI GitHub (tests + pre-commit) est verte sur le commit ;
   chaque module modifié depuis la dernière release a monté sa version ; ``CHANGE.md`` a
   de nouvelles entrées ;
2. pousse le commit sur ``19.0`` (fast-forward, sans changer de branche locale — les
   dossiers de modules montés dans Docker ne sont pas recréés) ;
3. pose le tag annoté ``v<version>`` (message = modules et versions + entrées de CHANGE.md
   depuis la release précédente) et le pousse : le workflow ``release.yml`` crée la
   GitHub Release.

Usage (depuis la racine du dépôt à publier) :
    python3 ../Comics-collections/tools/release.py 19.0.1.0.0            # dry-run
    python3 ../Comics-collections/tools/release.py 19.0.1.0.0 --apply    # publie

Options : ``--skip-ci`` (ne pas exiger la CI verte, déconseillé),
``--allow-same-versions`` (accepter un module modifié sans nouvelle version).
"""

import argparse
import ast
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

DEV = "19.0-dev"
STABLE = "19.0"
VERSION_RE = re.compile(r"^19\.0\.\d+\.\d+\.\d+$")


class ReleaseError(Exception):
    pass


def run(*cmd, check=True):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise ReleaseError(f"{' '.join(cmd)} : {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout.strip()


def git(*args, check=True):
    return run("git", *args, check=check)


def last_tag():
    out = git("describe", "--tags", "--abbrev=0", "--match", "v19.0.*", STABLE, check=False)
    return out or None


def modules():
    return sorted(p.parent.name for p in Path(".").glob("*/__manifest__.py"))


def manifest_version(module, ref=None):
    path = f"{module}/__manifest__.py"
    text = git("show", f"{ref}:{path}", check=False) if ref else Path(path).read_text()
    if not text:
        return None
    return ast.literal_eval(text).get("version")


def changed_modules(since):
    if not since:
        return modules()
    files = git("diff", "--name-only", f"{since}..HEAD").splitlines()
    return sorted({f.split("/")[0] for f in files} & set(modules()))


def change_notes(since):
    """Lignes ajoutées à CHANGE.md depuis ``since`` (tout le fichier pour la 1re release)."""
    if not since:
        # Première release : l'historique complet reste dans CHANGE.md (trop long pour une note)
        return "Première release publiée. Historique complet du développement : CHANGE.md."
    diff = git("diff", "--unified=0", f"{since}..HEAD", "--", "CHANGE.md")
    added = [line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
    return "\n".join(added).strip()


def ci_status(sha):
    """Conclusions des workflows tests / pre-commit pour ``sha`` (via gh)."""
    out = run("gh", "run", "list", "--commit", sha, "--json", "workflowName,status,conclusion", "--limit", "20")
    runs = json.loads(out or "[]")
    status = {}
    for r in runs:
        status.setdefault(r["workflowName"], (r["status"], r["conclusion"]))
    return status


def check(version, skip_ci, allow_same):
    problems = []
    if not VERSION_RE.match(version):
        problems.append(f"version « {version} » : format attendu 19.0.X.Y.Z")
    tag = f"v{version}"
    if git("tag", "--list", tag):
        problems.append(f"le tag {tag} existe déjà")
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if branch != DEV:
        problems.append(f"branche courante « {branch} » : la release se fait depuis {DEV}")
    if git("status", "--porcelain", "--untracked-files=no"):
        problems.append("arbre de travail non propre (fichiers modifiés non commités)")
    git("fetch", "--quiet", "origin", DEV, STABLE, "--tags")
    head = git("rev-parse", "HEAD")
    if head != git("rev-parse", f"origin/{DEV}"):
        problems.append(f"{DEV} local diffère de origin/{DEV} : pousser ou tirer d'abord")
    if subprocess.run(["git", "merge-base", "--is-ancestor", f"origin/{STABLE}", head]).returncode:
        problems.append(f"origin/{STABLE} n'est pas un ancêtre de {DEV} : fast-forward impossible")
    previous = last_tag()
    changed = changed_modules(previous)
    versions = {m: manifest_version(m) for m in modules()}
    if previous and not allow_same:
        for module in changed:
            if manifest_version(module, previous) == versions[module]:
                problems.append(f"{module} modifié depuis {previous} mais version inchangée ({versions[module]})")
    notes = change_notes(previous)
    if not notes:
        problems.append(f"aucune nouvelle entrée dans CHANGE.md depuis {previous}")
    if not skip_ci:
        status = ci_status(head)
        for workflow in ("tests", "pre-commit"):
            state = status.get(workflow)
            if not state:
                problems.append(f"CI « {workflow} » introuvable pour {head[:7]}")
            elif state != ("completed", "success"):
                problems.append(f"CI « {workflow} » non verte pour {head[:7]} : {state[0]} / {state[1]}")
    return problems, previous, changed, versions, notes, head


def tag_message(version, previous, changed, versions, notes):
    lines = [f"Release v{version} — {date.today():%Y-%m-%d}", ""]
    lines.append(f"Depuis {previous}." if previous else "Première release.")
    lines += ["", "Modules :"]
    for module, module_version in versions.items():
        marker = " (modifié)" if module in changed else ""
        lines.append(f"- {module} {module_version}{marker}")
    lines += ["", "Changements (CHANGE.md) :", "", notes]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Publie une release (19.0-dev → 19.0 + tag).")
    parser.add_argument("version", help="ex. 19.0.1.0.0")
    parser.add_argument("--apply", action="store_true", help="publier (sinon : vérifications seulement)")
    parser.add_argument("--skip-ci", action="store_true", help="ne pas exiger la CI verte")
    parser.add_argument("--allow-same-versions", action="store_true", help="module modifié sans nouvelle version")
    args = parser.parse_args()

    if not Path("CHANGE.md").exists():
        sys.exit("À lancer depuis la racine d'un dépôt Comic Collection (CHANGE.md introuvable).")
    try:
        problems, previous, changed, versions, notes, head = check(args.version, args.skip_ci, args.allow_same_versions)
    except ReleaseError as exc:
        sys.exit(f"Erreur : {exc}")
    message = tag_message(args.version, previous, changed, versions, notes)
    print(message.split("Changements")[0].rstrip())
    if problems:
        print("\nRelease impossible :")
        for problem in problems:
            print(f"  - {problem}")
        sys.exit(1)
    if not args.apply:
        print(f"\nVérifications OK. Relancer avec --apply pour publier v{args.version} ({head[:7]}).")
        return
    tag = f"v{args.version}"
    git("push", "origin", f"{head}:refs/heads/{STABLE}")
    git("fetch", "--quiet", "origin", f"{STABLE}:{STABLE}", check=False)
    subprocess.run(["git", "tag", "-a", tag, head, "-F", "-"], input=message, text=True, check=True)
    git("push", "origin", tag)
    print(f"\nPublié : {STABLE} → {head[:7]}, tag {tag} poussé (la GitHub Release est créée par la CI).")


if __name__ == "__main__":
    main()
