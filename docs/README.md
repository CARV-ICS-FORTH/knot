# Karvdash documentation

To view the docs, compile:
```
make html
```

Then, open `_build/html/index.html` in a browser.

How to export:
* Change theme to `alabaster` in `conf.py`.
* Comment out all `Indices and tables` in `index.rst`. Mark table of contents as `:numbered:`.
* Run: `make singlehtml`.
* Print as PDF.
