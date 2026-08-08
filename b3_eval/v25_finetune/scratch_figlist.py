import re
text = open('stbv_paper.tex', encoding='utf-8').read()
figs = re.findall(r'\\begin\{figure\}.*?\\label\{([^}]+)\}', text, re.DOTALL)
for i, f in enumerate(figs, 1):
    print(i, f)
print('total', len(figs))
