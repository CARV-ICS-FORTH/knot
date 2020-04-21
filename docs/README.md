# Karvdash documentation

To view the docs, install the Karvdash API client:
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
(cd ../client && ./setup.py install)
```

Compile:
```
make html
```

Then, open `_build/html/index.html` in a browser.

How to export:
* Change theme to `alabaster` in `conf.py`.
* Comment out all `Indices and tables` in `index.rst`. Mark table of contents as `:numbered:`.
* Run: `make singlehtml`.
* Print as PDF.
