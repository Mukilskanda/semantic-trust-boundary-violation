@echo off
for /f "delims=" %%F in ('dir /b *.tex ^| findstr /v "^wrapper_"') do (
    echo \documentclass{standalone} > wrapper_%%~nF.tex
    echo \usepackage{tikz} >> wrapper_%%~nF.tex
    echo \usepackage{xcolor} >> wrapper_%%~nF.tex
    echo \usepackage{DejaVuSans} >> wrapper_%%~nF.tex
    echo \renewcommand*\familydefault{\sfdefault} >> wrapper_%%~nF.tex
    echo \usepackage{amsmath} >> wrapper_%%~nF.tex
    echo \usepackage{amssymb} >> wrapper_%%~nF.tex
    echo \usepackage{pgfplots} >> wrapper_%%~nF.tex
    echo \pgfplotsset{compat=newest} >> wrapper_%%~nF.tex
    echo \usetikzlibrary{arrows.meta, positioning, shapes.geometric, fit, calc, backgrounds, patterns, spy, intersections, decorations.pathmorphing} >> wrapper_%%~nF.tex
    echo \begin{document} >> wrapper_%%~nF.tex
    echo \input{%%F} >> wrapper_%%~nF.tex
    echo \end{document} >> wrapper_%%~nF.tex
    
    pdflatex -interaction=nonstopmode wrapper_%%~nF.tex
    
    if exist wrapper_%%~nF.pdf (
        move /Y wrapper_%%~nF.pdf %%~nF.pdf
    )
    del wrapper_%%~nF.*
)
