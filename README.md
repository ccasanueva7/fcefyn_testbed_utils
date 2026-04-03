# fcefyn-testbed-utils

Complementary infrastructure for the FCEFyN HIL (Hardware-in-the-Loop) testbed: configs, scripts, and firmwares that are not part of the contributed repositories libremesh-tests and openwrt-tests.

---

Documentation: https://fcefyn-testbed.github.io/fcefyn_testbed_utils/

### Local preview (MkDocs)

Use the same dependencies as CI (includes `mkdocs-panzoom-plugin` for Mermaid pan/zoom):

```bash
python3 -m venv .venv-docs
source .venv-docs/bin/activate   # Windows: .venv-docs\Scripts\activate
pip install -r requirements-docs.txt
mkdocs serve #or mkdocs serve --livereload
```

If `mkdocs serve` reports `The "panzoom" plugin is not installed`, the active environment is missing dependencies: run `pip install -r requirements-docs.txt` again (or `pip install mkdocs-panzoom-plugin`) in that environment.