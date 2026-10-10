# B2 local quality and private handoff policy

Scope confirmed by the user: trusted local computer, no public access, no
application login/authentication, and Git/CI later. Do not add accounts, tokens,
keys or public infrastructure as a prerequisite for handing B2 to Team A.

## Privacy boundary

Both B1's database and the API-only Compose publication bind to 127.0.0.1.
Windows development instructions also bind Uvicorn to 127.0.0.1. The container's
internal 0.0.0.0 listener is behind that loopback publication; it is not a public
host binding. Do not change these bindings or add tunnels/port-forwarding/public
proxies. Existing Windows folder permissions are unchanged, by user choice.

Source files are needed to run the source project, or a separately built image
can run the backend. File possession is not authentication for an already-running
localhost server: other processes/users on the trusted host can make requests.
This is intentionally a trusted-machine boundary, not per-user confidentiality.
DB connection secrets and genuine scientific publication reviewer declarations
remain necessary internals; they are not an application login system. Private
configuration is excluded from the handoff ZIP. Browser CORS is not authentication.

## Repeatable local quality checks

Run from the project root. Use a NEW tooling environment, never replace B1's
working environment. The quality tools are development-only, not runtime pins:

```powershell
py -3.13 -m venv C:\receiving\b2-quality-tools
C:\receiving\b2-quality-tools\Scripts\python.exe -m pip install -r services/api/requirements-quality.txt
.\.venv\Scripts\python.exe scripts/check_b2_quality.py --quality-python C:\receiving\b2-quality-tools\Scripts\python.exe --output C:\receiving\quality-NEW.json
```

Ruff 0.16.10 uses explicit E4/E9/F correctness/import/syntax checks across B2's
31 application modules, B2 tests and twelve operational/verification scripts.
Only E402 ordering is excepted for the production entry point and bootstrapped
CLI imports, where startup must configure the environment/project path first.
No global unused-name suppression or all-rules/style certificate is claimed.

Mypy 2.4.0 checks all 31 B2 application modules for the supported Linux Python
3.13 runtime, including bodies of unannotated functions. It retains imported
B1/third-party signatures with follow_imports=silent, rather than rewriting B1
or reporting their implementation errors as B2 errors. No blanket missing-import
or type-error suppression is used. This is gradual typing, not --strict/full
annotation coverage. Functional Windows and Linux tests cover platform branches.
The checked signatures come from the real verified runtime interpreter via
--python-executable, not an empty tooling environment. On Windows use a real
cache directory; do not use NUL for mypy's cache.

The script refuses unpinned tool versions, existing report output and source
changes during checks. Reports preserve the exact source hashes and check scope.
The refreshed packager requires a passing quality report whose source matches
the delivered files. It does not silently count regression tests as lint/type.

## Ready to hand over versus accepted after merge

The local B2 handover gate requires passing quality, host regression/OpenAPI,
current hardened container/large-file checks, exact-image vulnerability review,
provisional performance and verified source/evidence archive. After source changes
rebuild and reverify the actual image; previous results cannot approve a new image.

Team A can receive this tested B2 package without waiting for Git or adding login.
Final merge acceptance requires their actual files/output namespace and API/scientific
contract decisions, real reviewed bundles, agreed format/size/workload targets and
receiver acknowledgement. These are joint integration inputs, not missing public
login functionality. Known reviewer-identity disclosure policy and KML scientific
validation decisions remain documented; do not invent owner sign-off.

Sources: [Ruff configuration](https://docs.astral.sh/ruff/configuration/),
[mypy existing-code guidance](https://mypy.readthedocs.io/en/stable/existing_code.html),
[mypy configuration](https://mypy.readthedocs.io/en/stable/config_file.html).
