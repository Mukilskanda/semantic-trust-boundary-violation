#!/usr/bin/env python3
"""
build_external_corpus.py
=========================
Merges the five source files (directly_authored, claude_generated,
paraphrased_public, gpt, gemini) into one external_corpus.json, with:
  - internal exact-duplicate check
  - a literal-substring overlap check against stbv_bench/transformations.py's
    own template strings, to verify the external corpus does not reuse
    STBV-Bench's templates (a hard requirement for this benchmark's purpose)
  - a family/source/label count manifest

Does NOT touch B3, does NOT retrain anything. Read-only against
stbv_bench/transformations.py (only used for the overlap check).

Run:
    python3 external_semantic_eval/build_external_corpus.py
"""
import json
import hashlib
import re
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent

SOURCES = [
    "corpus_directly_authored.json",
    "corpus_claude_generated.json",
    "corpus_paraphrased_public.json",
    "corpus_gpt.json",
    "corpus_gemini.json",
]


def load_stbv_bench_template_strings():
    """Extract every quoted literal string >= 25 chars from transformations.py,
    as a crude but effective substring-overlap detector against the actual
    fixed template text STBV-Bench's transformation rules emit."""
    src = (REPO / "stbv_bench" / "transformations.py").read_text(encoding="utf-8")
    strings = re.findall(r'"([^"]{25,})"', src) + re.findall(r"'([^']{25,})'", src)
    return [s.lower() for s in strings]


def main():
    all_entries = []
    for fname in SOURCES:
        path = HERE / fname
        entries = json.loads(path.read_text(encoding="utf-8"))
        all_entries.extend(entries)

    if not all_entries:
        print("[FATAL] no entries loaded — did you forget to paste GPT/Gemini output?")
        return 1

    # 1. internal exact-duplicate check
    seen_hash = {}
    dups = []
    for e in all_entries:
        h = hashlib.sha256(e["text"].strip().lower().encode()).hexdigest()
        if h in seen_hash:
            dups.append((e["id"], seen_hash[h]))
        else:
            seen_hash[h] = e["id"]
    if dups:
        print(f"[WARN] {len(dups)} internal exact-duplicate text(s) found: {dups}")

    # 2. STBV-Bench template overlap check
    stbv_strings = load_stbv_bench_template_strings()
    overlap_hits = []
    for e in all_entries:
        text_lower = e["text"].lower()
        for s in stbv_strings:
            # substring match either direction, on a meaningful chunk
            if s in text_lower or text_lower[:60] in s:
                overlap_hits.append((e["id"], s[:60]))
    if overlap_hits:
        print(f"[FAIL] {len(overlap_hits)} entries overlap with STBV-Bench template strings:")
        for eid, s in overlap_hits:
            print(f"    {eid}: matched '{s}...'")
    else:
        print("[OK] zero substring overlap with stbv_bench/transformations.py template strings.")

    # 3. counts
    by_source, by_family, by_label = {}, {}, {}
    for e in all_entries:
        by_source[e["source"]] = by_source.get(e["source"], 0) + 1
        by_family[e["family"]] = by_family.get(e["family"], 0) + 1
        by_label[e["label"]] = by_label.get(e["label"], 0) + 1

    for i, e in enumerate(all_entries):
        e["global_id"] = f"ext_{i:04d}"

    out = {
        "corpus_name": "EXTERNAL_SEMANTIC_EVALUATION_CORPUS",
        "n_total": len(all_entries),
        "by_source": by_source,
        "by_family": by_family,
        "by_label": by_label,
        "internal_exact_duplicates_found": len(dups),
        "stbv_bench_template_overlap_hits": len(overlap_hits),
        "entries": all_entries,
    }
    out_path = HERE / "external_corpus.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"\nWrote {out_path}")
    print(f"  n_total = {len(all_entries)}")
    print(f"  by_source = {by_source}")
    print(f"  by_label = {by_label}")
    print(f"  by_family = {by_family}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
