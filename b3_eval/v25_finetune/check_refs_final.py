import re
s = open("stbv_paper.tex", encoding="utf-8").read()
labels = set(re.findall(r"\\label\{([^}]+)\}", s))
refs = set(re.findall(r"\\ref\{([^}]+)\}", s))
cites = set(re.findall(r"\\cite\{([^}]+)\}", s))
bibitems = set(re.findall(r"\\bibitem\{([^}]+)\}", s))
missing_refs = refs - labels
cite_keys = set()
for c in cites:
    cite_keys.update(k.strip() for k in c.split(","))
missing_cites = cite_keys - bibitems
print("labels", len(labels), "refs", len(refs))
print("missing refs (dangling):", missing_refs)
print("cite keys", len(cite_keys), "bibitems", len(bibitems))
print("missing cites (dangling):", missing_cites)
print("unused labels:", labels - refs)
