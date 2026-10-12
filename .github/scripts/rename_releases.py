#!/usr/bin/env python3
"""Give a document's past releases its new id, after the id changed.

    python3 .github/scripts/rename_releases.py notes lecture            # what would change
    python3 .github/scripts/rename_releases.py notes lecture --apply    # change it

A document's id is in the name of everything it released: the tag
v<version>-<id>, the release's title, and the files attached to it
(v0.1.2-<id>.pdf, diff-..., arxiv-bundle-..., clean-...). Renaming the table in
docs.toml changes none of that, and the document then looks new: the next
release finds no previous tag, so it carries no diff and no list of commits.
This moves the history over, every release of the old id:

    tag       v0.1.2-notes        ->  v0.1.2-lecture    (same commit)
    release   moved to the new tag, title renamed, same release, same files
    files     v0.1.2-notes.pdf    ->  v0.1.2-lecture.pdf
    CHANGELOG ## v0.1.2-notes     ->  ## v0.1.2-lecture (in the working tree; commit it)

The old tags are deleted. GitHub does not redirect them: a link to
.../releases/tag/v0.1.2-notes, or to a file under it, stops working. The PDFs
themselves are not touched, only named.

A pushed tag starts Release.yml, which would try to release each renamed tag
again from a commit where the document still has its old id. The workflow is
therefore switched off while the tags move and on again afterwards, also when
a step fails. Needs gh, signed in with write access.

docs.toml, the root file and src/<id>/ are renamed by hand, in a PR. When that
PR is merged, AutoRelease.yml does the rest by itself, before it releases
anything:

    python3 .github/scripts/rename_releases.py --renamed-since <commit>    # prints "old new" per renamed document

compares docs.toml at that commit with the one in the working tree. A table
is a rename only when the file says so: the file a document was made from now
belongs to another table, because git sees it renamed to that table's root (or
source) or because that table names the same file. Two documents that trade
ids are found the same way and moved through a temporary id, in three steps. A
document removed and another added in one PR is not a rename, and nothing is
moved for it.
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHANGELOG = ROOT / ".github" / "CHANGELOG.md"
ID = re.compile(r"[A-Za-z0-9_]+")


def plan(old: str, new: str, tags: list[str], releases: list[dict]) -> list[dict]:
    """One entry per tag of the old id: the new tag, and the release and files that follow it."""
    for doc_id in (old, new):
        if not ID.fullmatch(doc_id):
            sys.exit(f"'{doc_id}' is not a document id (letters, digits and _)")
    if old == new:
        sys.exit("the two ids are the same")
    by_tag = {r["tag_name"]: r for r in releases}
    steps = []
    for tag in sorted(tags):
        target = renamed(tag, old, new)
        if target is None:
            continue
        if target in tags:
            sys.exit(f"{target} exists already; nothing was changed")
        step = {"old": tag, "new": target, "release": None, "title": None, "assets": []}
        release = by_tag.get(tag)
        if release:
            step["release"] = release["id"]
            # A title that was edited by hand to something else is left as it is.
            step["title"] = (release.get("name") or "").replace(tag, target)
            step["assets"] = [(a["id"], a["name"], a["name"].replace(tag, target))
                              for a in release.get("assets", []) if tag in a["name"]]
        steps.append(step)
    return steps


VERSION = r"\d+\.\d+\.\d+"


def renamed(tag: str, old: str, new: str) -> str | None:
    """The tag under the new id, or None if it is not a tag of the old one.

    v<version>-<id> is the form in use. <id>-v<version> is the one before it,
    which a repository that started early still has; it keeps its form.
    """
    if re.fullmatch(rf"v{VERSION}-{re.escape(old)}", tag):
        return tag[: -len(old)] + new
    if re.fullmatch(rf"{re.escape(old)}-v{VERSION}", tag):
        return new + tag[len(old):]
    return None


def heading_tags(text: str, old: str) -> list[str]:
    return [t for t in re.findall(r"^## (\S+)", text, flags=re.M) if renamed(t, old, "x") is not None]


def rewrite_changelog(text: str, old: str, new: str) -> str:
    """The headings of the old id's entries; nothing inside an entry."""
    return re.sub(r"^## (\S+)", lambda m: "## " + (renamed(m[1], old, new) or m[1]), text, flags=re.M)


def files(manifest: str) -> dict[str, str]:
    """id -> the file the document is made from, for every table with a version."""
    return {doc_id: table.get("root") or table.get("source") or f"{doc_id}.tex"
            for doc_id, table in tomllib.loads(manifest).items()
            if isinstance(table, dict) and "version" in table}


def detect(before: dict[str, str], after: dict[str, str], moved: dict[str, str]) -> dict[str, str]:
    """old id -> new id for each document whose table was renamed.

    before, after: id -> file, from the two manifests. moved: old path -> new
    path, the renames git found between the two commits.

    A document is followed by its file. It has a new id when the file it was
    made from now belongs to another table: because git saw the file renamed
    to that table's, or because that table now names the same file. Two
    documents that trade ids (main becomes notes and notes becomes main) are
    found the same way, each file having gone to the other's table.

    What does not hold together is dropped, and nothing is moved for it: two
    documents heading for one id, a document that keeps its table while its
    file seems to have gone elsewhere, a target id that already has a document
    which is not itself moving away.
    """
    owner = {path: doc_id for doc_id, path in after.items()}
    pairs = {}
    for old, path in before.items():
        target = owner.get(moved[path]) if path in moved else owner.get(path)
        if target and target != old:
            pairs[old] = target
    while True:
        targets = list(pairs.values())
        bad = [old for old, new in pairs.items()
               if targets.count(new) > 1                 # two documents, one id
               or (old in after and old not in targets)  # its table stays and nobody takes it
               or (new in before and new not in pairs)]  # the id is taken by a document that stays
        if not bad:
            return pairs
        for old in bad:
            del pairs[old]


def order(pairs: dict[str, str]) -> list[tuple[str, str]]:
    """The renames one after another, so that none lands on tags still in use.

    A swap cannot be done in place: v0.1.0-main cannot become v0.1.0-notes
    while notes still has its own. One of the two steps aside first, under an
    id that exists only for the length of the move.
    """
    pending = dict(pairs)
    steps = []
    while pending:
        free = [old for old, new in pending.items() if new not in pending]
        if free:
            steps.append((free[0], pending.pop(free[0])))
        else:
            old = next(iter(pending))
            aside = f"renaming_{old}"
            steps.append((old, aside))
            pending[aside] = pending.pop(old)
    return steps


def renamed_since(rev: str) -> list[tuple[str, str]]:
    before = files(run("git", "show", f"{rev}:docs.toml", capture=True))
    after = files((ROOT / "docs.toml").read_text())
    # --break-rewrites: two files that traded contents both exist before and
    # after, and git calls that two edits unless told to look at them as
    # deleted and added.
    status = run("git", "diff", "--break-rewrites", "--find-renames", "--name-status", "--diff-filter=R",
                 rev, "HEAD", capture=True)
    moved = {line.split("\t")[1]: line.split("\t")[2] for line in status.splitlines() if line}
    return order(detect(before, after, moved))


def run(*command: str, capture: bool = False) -> str:
    result = subprocess.run(command, cwd=ROOT, check=True, text=True, capture_output=capture)
    return result.stdout if capture else ""


def api(method: str, path: str, **fields: str) -> None:
    run("gh", "api", "-X", method, path, *(arg for k, v in fields.items() for arg in ("-f", f"{k}={v}")),
        capture=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("old", nargs="?", help="the id the releases carry")
    parser.add_argument("new", nargs="?", help="the id they should carry")
    parser.add_argument("--renamed-since", metavar="COMMIT",
                        help="print 'old new' for each document renamed in docs.toml since that commit, and stop")
    parser.add_argument("--keep-workflow", action="store_true",
                        help="leave the release workflow on: for a run inside Actions, whose pushes start no workflow")
    parser.add_argument("--apply", action="store_true", help="make the changes; without it, only print them")
    parser.add_argument("--release-workflow", default="Release.yml",
                        help="the workflow a pushed tag starts, switched off meanwhile (default: Release.yml)")
    args = parser.parse_args()
    if args.renamed_since:
        for old, new in renamed_since(args.renamed_since):
            print(old, new)
        return 0
    if not (args.old and args.new):
        parser.error("give the old and the new id, or --renamed-since")

    repo = run("gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner", capture=True).strip()
    run("git", "fetch", "--quiet", "--tags", "origin")
    tags = run("git", "tag", "--list", capture=True).split()
    releases = json.loads(run("gh", "api", "--paginate", "--slurp", f"repos/{repo}/releases", capture=True))
    releases = [r for page in releases for r in page]
    steps = plan(args.old, args.new, tags, releases)
    if not steps:
        print(f"{repo}: no tag of the document '{args.old}'; nothing to rename")
        return 0

    for step in steps:
        print(f"{step['old']}  ->  {step['new']}" + ("" if step["release"] else "   (a tag with no release)"))
        for _, before, after in step["assets"]:
            print(f"    {before}  ->  {after}")
    headings = len(heading_tags(CHANGELOG.read_text(), args.old)) if CHANGELOG.is_file() else 0
    print(f"{headings} heading(s) in {CHANGELOG.relative_to(ROOT)}")
    if not args.apply:
        print(f"\nNothing was changed. With --apply: {len(steps)} tag(s) of {repo} are renamed and the old ones"
              " deleted; links to them stop working.")
        return 0

    if not args.keep_workflow:
        run("gh", "workflow", "disable", args.release_workflow)
    try:
        # New tags first, on the objects the old ones name: a release moved to a
        # tag that does not exist yet would be given one on the default branch.
        run("git", "push", "--quiet", "origin", *(f"refs/tags/{s['old']}:refs/tags/{s['new']}" for s in steps))
        for step in steps:
            if step["release"]:
                api("PATCH", f"repos/{repo}/releases/{step['release']}", tag_name=step["new"], name=step["title"])
                for asset_id, _, after in step["assets"]:
                    api("PATCH", f"repos/{repo}/releases/assets/{asset_id}", name=after)
        # Old tags last: a release whose tag is deleted under it turns into a draft.
        run("git", "push", "--quiet", "origin", *(f":refs/tags/{s['old']}" for s in steps))
    finally:
        if not args.keep_workflow:
            run("gh", "workflow", "enable", args.release_workflow)
    for step in steps:
        run("git", "tag", step["new"], step["old"])
        run("git", "tag", "--delete", step["old"], capture=True)
    if headings:
        CHANGELOG.write_text(rewrite_changelog(CHANGELOG.read_text(), args.old, args.new))
        print(f"{CHANGELOG.relative_to(ROOT)} rewritten; commit it")
    print(f"{len(steps)} release tag(s) renamed in {repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
