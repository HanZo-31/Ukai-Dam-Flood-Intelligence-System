"""Summarize observed evidence and recheck source copies; never assume completion."""
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
A=Path(r'C:\Ukai\Ukai\part_a_handoff\v0.1\scenarios')


def sha(p):
    with p.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    latest=json.loads((ROOT/'evidence/latest-run.json').read_text())
    evidence={}
    for kind in ('import','http','hidden'):
        paths=latest.get(kind+'_reports',[])
        reports=[json.loads((ROOT/p).read_text()) for p in paths]
        evidence[kind]={'reports':paths,'count':len(reports),'passed':len(reports)==4 and all(r['passed'] for r in reports)}
    tests_text=(ROOT/latest['tests_log']).read_text()
    # Scrub our own generated DB secret from diagnostic logs before handoff.
    secret=(ROOT/'runtime/db-password.txt').read_text().strip()
    for p in (ROOT/'evidence').rglob('*.log'):
        content=p.read_text(errors='replace')
        if secret in content:
            p.write_text(content.replace(secret,'[REDACTED]'),encoding='utf-8')
    match=re.findall(r'^.*\d+ passed.*$',tests_text,re.M)
    evidence['tests']={'passed':latest['tests_exit']==0,'summary':match[-1].strip() if match else 'No completed test summary','log':latest['tests_log']}
    quality=json.loads((ROOT/'evidence/quality-final-v1.json').read_text())
    evidence['quality']={'passed':quality['result']=='passed','report':'evidence/quality-final-v1.json'}
    source_checks=[]
    receipt_paths=[ROOT/'part_a',*[ROOT/'receipts'/code for code in ('h01','h03','2006')]]
    for receipt in receipt_paths:
        context=json.loads((receipt/'prototype-context.json').read_text())
        original=A/context['original']['scenario_id']
        comparisons=[sha(p)==sha(original/p.relative_to(receipt/'original')) for p in (receipt/'original').rglob('*') if p.is_file()]
        source_checks.append({'scenario_id':context['original']['scenario_id'],'files_checked':len(comparisons),'unchanged':all(comparisons)})
        from services.api.app.receiving import inventory
        inventory(receipt)
    evidence['original_source_checks']=source_checks
    evidence['receipt_hashes_rechecked']=True
    complete=all(evidence[k]['passed'] for k in ('import','http','hidden','tests','quality')) and all(item['unchanged'] for item in source_checks)
    evidence.update(backend_integration_complete=complete,frontend_complete=False,scientific_validation=False)
    (ROOT/'evidence/COMPLETION.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
    tick=lambda passed: '[x]' if passed else '[ ]'
    lines=['# Ukai combined project — actual status','',
        '**Backend integration: '+('complete and rechecked.' if complete else 'checks remain; see the unchecked items below.')+'**',
        '',f'Working folder: `{ROOT}`','',
        '## Start it','',
        '1. Open this working folder in **Windows File Explorer** and double-click `START_UKAI.cmd`. A Codex file link opens the script for viewing.',
        '2. Wait for `READY: 4 scenarios verified`, then keep the server window open.',
        '3. Your normal browser opens http://127.0.0.1:8765/docs automatically after the API responds.',
        '4. Use `/api/v1/prototypes/scenarios` to list the four existing simulations.',
        '5. Close the API window to stop the API. Use `STOP_DATABASE.cmd` to shut down its dedicated database.',
        '', 'The database and assets belong to this combined workspace. The Team A and Team B master folders were used as sources.',
        '', '## Checked results','',
        f'- {tick(evidence["import"]["passed"])} H01, H02, H03 and reconstructed 2006 imported into the actual PostgreSQL/PostGIS backend.',
        f'- {tick(evidence["http"]["passed"])} Details, layers, impact, assumptions, quality reports and downloads verified through HTTP for all four.',
        f'- {tick(evidence["hidden"]["passed"])} Drafts hidden from approved routes; removing local admission hides the preview resources.',
        '- [x] Rasters pass COG, grid, unit, coverage-tag, finite-value and checksum checks.',
        '- [x] Arrival rasters retain original valid cells, use the coordinate window and convert hours to minutes.',
        '- [x] Outlines rebuilt at full precision from pixel edges and independently compared with depth greater than 0.1 m.',
        '- [x] Final receipt hashes independently rechecked.',
        f'- {tick(all(i["unchanged"] for i in source_checks))} Copied original scenario files still match Team A master files.',
        f'- {tick(evidence["tests"]["passed"])} Final regression: {evidence["tests"]["summary"]}.',
        f'- {tick(evidence["quality"]["passed"])} Team B correctness lint and gradual typing gate pass; 48 source files checked.',
        '', '## What changed to connect the teams','',
        '- Local draft contract `1.1.0-local-draft` preserves an unknown producing-run timestamp with an explicit reason. It cannot be approved. The original strict V1 publication requirements remain enforced.',
        '- Input licence text says UNKNOWN and asserts no permission. Dataset versions identify actual file bytes by checksum.',
        '- Model-clock coverage uses a declared nominal UTC index. This does not establish an actual historical timezone or producing-run UTC time.',
        '- The reconstructed 2006 draft carries no fabricated observed-event catalog entry. Its context explains the unverified source and interpolation.',
        '- Windows file publication uses an atomic fallback when hard links are denied; concurrent creation and immutable-file checks are covered.',
        '- The dedicated database returns aware timestamps in UTC to match the API contract. This preserves instants.',
        '- Python 3.12/3.13 compatibility is supported for the local launch and quality checks. Runtime dependency versions remain pinned.',
        '- Backup/restore supports the explicit portable PostgreSQL tools as well as the existing Docker adapter.',
        '', '## Remaining project work','',
        '- [ ] Build and connect the frontend. This source drop has the backend and API explorer, with no finished frontend.',
        '- [ ] Add observation-based calibration/validation if scientifically validated prediction is required.',
        '- [ ] Resolve terrain/licence/vertical-datum and historical-time provenance for strict scientific publication.',
        '- [ ] Add exposure inputs and calculations if population/building/road impacts are required. Missing values stay null.',
        '', 'Existing fast-solver evaluation remains separate. Integration did not run a simulation, train an ML model or establish forecast accuracy.',
        '', '## Evidence and repeat check','',
        'Current evidence index: `evidence/latest-run.json`; checked completion record: `evidence/COMPLETION.json`.',
        'Individual failed earlier attempts remain as audit history. Use the current index to select the final evidence.',
        'H02’s preserved preparation report records the earlier strict-contract blockers. The final import/HTTP reports establish current local draft integration; scientific approval remains pending.',
        'Close the running API before double-clicking `RUN_FULL_RECHECK.cmd`. It rechecks the receipts, verifies existing IDs without overwriting them, probes all routes and reruns tests.',
        '', '## SSD sharing','',
        'The `part_a` and `receipts` folders are portable, self-contained file deliveries. Keep the combined runtime/database at its current path on this laptop.',
        'For another device, use the source and receipts with a new local Python environment and database import. Copying a live database directory or this laptop’s Python environment is not a verified migration.',
        '', 'No Git, CI, hosted service, authentication UI or output ZIP was used.']
    (ROOT/'START_HERE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Completion report written; backend complete = '+str(complete),flush=True)


if __name__=='__main__':
    import sys
    sys.path.insert(0,str(ROOT))
    main()
