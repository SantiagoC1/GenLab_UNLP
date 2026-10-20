#!/usr/bin/env python3
"""Crea labels, milestones e issues en el repo de GitHub a partir de issues.json.

Uso:
  python3 crear_issues.py --repo OWNER/REPO --dry-run
  python3 crear_issues.py --repo OWNER/REPO --a USER_A --b USER_B --c USER_C

Requiere la CLI `gh` autenticada. Es idempotente: no duplica labels, milestones ni issues (compara por titulo).
"""
import argparse, json, subprocess, sys

def gh(args, inp=None):
    r = subprocess.run(["gh"] + args, input=inp, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])}: {r.stderr.strip()}")
    return r.stdout

ap = argparse.ArgumentParser()
ap.add_argument("--repo", required=True)
ap.add_argument("--file", default="issues.json")
ap.add_argument("--a"); ap.add_argument("--b"); ap.add_argument("--c")
ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()
data = json.load(open(a.file, encoding="utf-8"))
users = {"A": a.a, "B": a.b, "C": a.c}
COLORS = {"area": "1d76db", "integrante": "5319e7", "puntos": "c5def5", "chatbot": "0e8a16", "deseo": "fbca04"}

labels = sorted({l for i in data["issues"] for l in i["labels"]})
if a.dry_run:
    print(f"{len(labels)} labels, {len(data['milestones'])} milestones, {len(data['issues'])} issues")
    for i in data["issues"]:
        print(f"  {i['milestone']:9} {i['assignee_key']} {i['title']}  {i['labels']}")
    sys.exit(0)

for l in labels:
    gh(["label", "create", l, "--repo", a.repo, "--color", COLORS.get(l.split(":")[0], "ededed"), "--force"])
print(f"labels listos: {len(labels)}")

existing_ms = {m["title"] for m in json.loads(gh(["api", f"repos/{a.repo}/milestones?state=all&per_page=100"]))}
for m in data["milestones"]:
    if m["title"] not in existing_ms:
        gh(["api", f"repos/{a.repo}/milestones", "-f", f"title={m['title']}", "-f", f"due_on={m['due']}T23:59:59Z"])
print("milestones listos")

existing = {i["title"] for i in json.loads(gh(["issue", "list", "--repo", a.repo, "--state", "all", "--limit", "500", "--json", "title"]))}
n = 0
for i in data["issues"]:
    if i["title"] in existing:
        continue
    cmd = ["issue", "create", "--repo", a.repo, "--title", i["title"], "--body-file", "-", "--milestone", i["milestone"]]
    for l in i["labels"]:
        cmd += ["--label", l]
    u = users.get(i["assignee_key"])
    if u:
        cmd += ["--assignee", u]
    print(gh(cmd, inp=i["body"]).strip())
    n += 1
print(f"issues creados: {n} (ya existian: {len(data['issues']) - n})")
