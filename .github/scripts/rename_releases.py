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

docs.toml, the root file and src/<id>/ are renamed by hand, in a PR of their
own; run this when that PR is merged, or just before.
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

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
    pattern = re.compile(rf"v\d+\.\d+\.\d+-{re.escape(old)}")
    by_tag = {r["tag_name"]: r for r in releases}
    steps = []
    for tag in sorted(t for t in tags if pattern.fullmatch(t)):
        target = tag[: -len(old)] + new
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


def rewrite_changelog(text: str, old: str, new: str) -> str:
    """The headings of the old id's entries; nothing inside an entry."""
    return re.sub(rf"^(## v\d+\.\d+\.\d+-){re.escape(old)}(?=\s|$)", rf"\g<1>{new}", text, flags=re.M)


def run(*command: str, capture: bool = False) -> str:
    result = subprocess.run(command, cwd=ROOT, check=True, text=True, capture_output=capture)
    return result.stdout if capture else ""


def api(method: str, path: str, **fields: str) -> None:
    run("gh", "api", "-X", method, path, *(arg for k, v in fields.items() for arg in ("-f", f"{k}={v}")),
        capture=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("old", help="the id the releases carry")
    parser.add_argument("new", help="the id they should carry")
    parser.add_argument("--apply", action="store_true", help="make the changes; without it, only print them")
    parser.add_argument("--release-workflow", default="Release.yml",
                        help="the workflow a pushed tag starts, switched off meanwhile (default: Release.yml)")
    args = parser.parse_args()

    repo = run("gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner", capture=True).strip()
    run("git", "fetch", "--quiet", "--tags", "origin")
    tags = run("git", "tag", "--list", capture=True).split()
    releases = json.loads(run("gh", "api", "--paginate", "--slurp", f"repos/{repo}/releases", capture=True))
    releases = [r for page in releases for r in page]
    steps = plan(args.old, args.new, tags, releases)
    if not steps:
        print(f"{repo}: no tag v<version>-{args.old}; nothing to rename")
        return 0

    for step in steps:
        print(f"{step['old']}  ->  {step['new']}" + ("" if step["release"] else "   (a tag with no release)"))
        for _, before, after in step["assets"]:
            print(f"    {before}  ->  {after}")
    headings = len(re.findall(rf"^## v\d+\.\d+\.\d+-{re.escape(args.old)}(?=\s|$)", CHANGELOG.read_text(), flags=re.M)) \
        if CHANGELOG.is_file() else 0
    print(f"{headings} heading(s) in {CHANGELOG.relative_to(ROOT)}")
    if not args.apply:
        print(f"\nNothing was changed. With --apply: {len(steps)} tag(s) of {repo} are renamed and the old ones"
              " deleted; links to them stop working.")
        return 0

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
