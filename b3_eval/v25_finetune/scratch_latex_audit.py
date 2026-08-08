import re
text = open('stbv_paper.tex', encoding='utf-8').read()
labels = set(re.findall(r'\\label\{([^}]+)\}', text))
refs = set(re.findall(r'\\(?:ref|eqref)\{([^}]+)\}', text))
missing = refs - labels
dup_labels = [l for l in labels if text.count('\\label{' + l + '}') > 1]
unref_labels = labels - refs
print('labels', len(labels), 'refs', len(refs))
print('MISSING (ref w/o label):', missing)
print('DUP labels:', dup_labels)
print('unreferenced labels (informational):', sorted(unref_labels))

cites = set(re.findall(r'\\cite[a-z]*\{([^}]+)\}', text))
cite_keys = set()
for c in cites:
    cite_keys.update(k.strip() for k in c.split(','))
bibitems = set(re.findall(r'\\bibitem\{([^}]+)\}', text))
print('cite keys', len(cite_keys), 'bibitems', len(bibitems))
print('cited but no bibitem:', cite_keys - bibitems)
print('bibitem never cited:', bibitems - cite_keys)

# figures/tables
fig_labels = [l for l in labels if 'fig' in l.lower()]
tab_labels = [l for l in labels if 'tab' in l.lower()]
print('fig labels', len(fig_labels))
print('tab labels', len(tab_labels))

# includegraphics missing files
import pathlib
graphics = re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', text)
print('includegraphics count', len(graphics))
for g in graphics:
    candidates = [g, g + '.pdf', g + '.png']
    if not any(pathlib.Path(c).exists() for c in candidates):
        print('  MISSING FILE:', g)
