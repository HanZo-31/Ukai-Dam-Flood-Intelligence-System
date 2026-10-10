"""Local stored-reference fallback; diagnostic ML is explicitly unavailable."""
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import threading
import time
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

FAMILY: Literal['ukai-hyp-fixed-shape-v1'] = 'ukai-hyp-fixed-shape-v1'
ID_PATTERN = r'^[a-z0-9][a-z0-9_-]{2,99}$'


class CandidateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False, strict=True)
    schema_version: Literal['1.0.0'] = '1.0.0'
    request_id: str = Field(pattern=ID_PATTERN)
    mode: Literal['stored_reference'] = 'stored_reference'
    input_family: Literal['ukai-hyp-fixed-shape-v1'] = FAMILY
    peak_release_m3s: float = Field(ge=15000, le=30000)
    allow_nearest_stored: bool = False


class ReferenceResources(BaseModel):
    model_config = ConfigDict(extra='forbid')
    detail: str = Field(pattern=r'^/api/v1/prototypes/scenarios/')
    layers: str = Field(pattern=r'^/api/v1/prototypes/scenarios/')
    impact: str = Field(pattern=r'^/api/v1/prototypes/scenarios/')
    assumptions: str = Field(pattern=r'^/api/v1/prototypes/scenarios/')
    quality_report: str = Field(pattern=r'^/api/v1/prototypes/scenarios/')


class CandidateResult(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    schema_version: Literal['1.0.0']
    job_id: str = Field(pattern=ID_PATTERN)
    request_id: str = Field(pattern=ID_PATTERN)
    status: Literal['completed']
    mode: Literal['stored_reference']
    input_family: Literal['ukai-hyp-fixed-shape-v1']
    requested_peak_release_m3s: float = Field(ge=15000, le=30000)
    # Pydantic validates numeric literals; preserve the frozen number-enum schema.
    actual_peak_release_m3s: Literal[15000., 20000., 30000.]  # type: ignore[valid-type]
    cache_hit: bool
    computed: Literal[False]
    engine: Literal['HEC-RAS stored reference']
    scientifically_validated: Literal[False]
    calibration_status: Literal['uncalibrated']
    warnings: list[str]
    completed_at: AwareDatetime
    elapsed_wall_seconds: float = Field(ge=0)
    timing_scope: str
    source_scenario_id: str
    source_run_id: str
    reference_resources: ReferenceResources


class Capabilities(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal['1.0.0']
    input_family: Literal['ukai-hyp-fixed-shape-v1']
    supported_modes: list[Literal['stored_reference']]
    stored_peaks_m3s: list[float]
    selection_range_m3s: list[float]
    experimental_ml_enabled: Literal[False]
    model_status: Literal['diagnostic_only_gate_not_passed']
    model_unavailable_reason: str
    scientifically_validated: Literal[False]
    calibration_status: Literal['uncalibrated']
    additional_scenario_runs: Literal[0]
    historical_2006_is_separate_reference: Literal[True]


def checksum(path):
    with path.open('rb') as handle:
        return 'sha256:' + hashlib.file_digest(handle, 'sha256').hexdigest()


def create_app(source: Path, state: Path):
    source, state = source.resolve(), state.resolve()
    if state.is_relative_to(source) or source.is_relative_to(state):
        raise ValueError('Use separate writable candidate state')
    state.mkdir(parents=True, exist_ok=True)
    roots = {15000.: source / 'receipts/h01', 20000.: source / 'part_a', 30000.: source / 'receipts/h03'}
    manifests = {peak: json.loads((root / 'prototype-manifest.json').read_text()) for peak, root in roots.items()}
    manifest_hashes = {peak: checksum(root / 'prototype-manifest.json') for peak, root in roots.items()}
    lock = threading.Lock()
    app = FastAPI(title='Ukai local candidate service', version='1.0.0',
        description='Stored-reference selection fallback. Experimental ML gate is not passed.',
        docs_url=None, redoc_url=None)
    app.add_middleware(CORSMiddleware, allow_origins=['http://127.0.0.1:5174', 'http://127.0.0.1:5175',
        'http://localhost:5174', 'http://localhost:5175'], allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])

    @app.middleware('http')
    async def peer(request: Request, call_next):
        if request.client is None or request.client.host not in {'127.0.0.1', '::1'}:
            return JSONResponse({'reason': 'loopback_required'}, status_code=404)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        return response

    def capability():
        return {'schema_version': '1.0.0', 'input_family': FAMILY,
            'supported_modes': ['stored_reference'], 'stored_peaks_m3s': sorted(roots),
            'selection_range_m3s': [15000, 30000], 'experimental_ml_enabled': False,
            'model_status': 'diagnostic_only_gate_not_passed',
            'model_unavailable_reason': 'Only one intermediate scenario holdout; original plan requires at least two. Flood expansion domain also unavailable.',
            'scientifically_validated': False, 'calibration_status': 'uncalibrated',
            'additional_scenario_runs': 0, 'historical_2006_is_separate_reference': True}

    def verify(peak):
        manifest, root = manifests[peak], roots[peak]
        if checksum(root / 'prototype-manifest.json') != manifest_hashes[peak]:
            raise ValueError('Immutable reference metadata changed')
        def bound_file(relative, expected):
            if not isinstance(relative, str) or not relative:
                raise ValueError('Invalid reference path')
            portable = PurePosixPath(relative)
            if (portable.is_absolute() or '..' in portable.parts or ':' in relative
                    or '\\' in relative or '\x00' in relative or portable.as_posix() != relative):
                raise ValueError('Nonportable reference path')
            target = (root / relative).resolve()
            if not target.is_relative_to(root) or not target.is_file() or checksum(target) != expected:
                raise ValueError('Reference validation failed')
        for dataset in manifest['datasets']:
            bound_file(dataset['source_reference'], dataset['checksum'])
        for role, relative in manifest['assets'].items():
            bound_file(relative, manifest['asset_metadata'][role]['checksum'])
        for relative, expected in [(manifest['assumptions_url'], manifest['assumptions_checksum']),
                (manifest['quality']['report_reference'], manifest['quality']['report_checksum'])]:
            bound_file(relative, expected)

    @app.get('/docs', include_in_schema=False, response_class=HTMLResponse)
    def offline_documentation():
        # Static local reference, not CDN-backed Swagger. Public OpenAPI stays unchanged.
        return HTMLResponse('''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Ukai candidate API — offline reference</title>
<style>body{font:17px system-ui;max-width:850px;margin:2rem auto;padding:0 1rem;line-height:1.6}
pre{background:#eef2f5;padding:1rem;overflow:auto}a:focus-visible{outline:3px solid #165fc7}</style></head>
<body><main><h1>Ukai candidate API — offline reference</h1>
<p>Contract 1.0.0. Stored-reference lookup only; computed:false. Experimental ML is disabled.
This page uses no external assets. It is an API reference, not an interactive Swagger console.</p>
<nav aria-label="Local API resources"><ul><li><a href="/openapi.json">Local OpenAPI JSON</a></li>
<li><a href="/api/v1/candidates/capabilities">Current capabilities</a></li></ul></nav>
<h2>Endpoints</h2><ul><li>GET /api/v1/candidates/capabilities</li>
<li>POST /api/v1/candidates/jobs</li><li>GET /api/v1/candidates/jobs/{job_id}</li></ul>
<h2>Stored lookup request</h2><pre>{
  "schema_version": "1.0.0", "request_id": "offline-example-001",
  "mode": "stored_reference", "input_family": "ukai-hyp-fixed-shape-v1",
  "peak_release_m3s": 20000, "allow_nearest_stored": false
}</pre><p>Peak bounds: 15000–30000 m³/s. Only 15000, 20000 and 30000 are stored.
Intermediate lookup requires explicit nearest opt-in; always show the actual returned peak.
The result's prototype resource links belong to the reference API adapter, not this candidate server.</p>
<h2>Failures</h2><p>400 selection unavailable; 404 job absent; 409 request conflict/busy;
422 invalid request; 503 source or job evidence unavailable. Missing values are not zero.
These are simulated, uncalibrated references, not forecasts or emergency instructions.</p>
</main></body></html>''', headers={
            'Content-Security-Policy': "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'",
            'X-Content-Type-Options': 'nosniff'})

    def read_saved(path, job_id):
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
            raise ValueError('Invalid bounded job evidence')
        saved = json.loads(path.read_text())
        result = CandidateResult.model_validate(saved['result'])
        peak = result.actual_peak_release_m3s
        manifest = manifests[peak]
        base = '/api/v1/prototypes/scenarios/' + manifest['scenario_id']
        expected_links = {'detail': base, 'layers': base + '/layers', 'impact': base + '/impact',
                          'assumptions': base + '/assumptions', 'quality_report': base + '/quality-report'}
        expected_peak = min(roots, key=lambda value: (abs(value - result.requested_peak_release_m3s), value))
        if (result.job_id != job_id or result.request_id != job_id
                or peak != expected_peak
                or result.source_scenario_id != manifest['scenario_id'] or result.source_run_id != manifest['run_id']
                or result.reference_resources.model_dump() != expected_links
                or result.cache_hit or 'stored_reference_not_new_prediction' not in result.warnings):
            raise ValueError('Stored job/source identity mismatch')
        verify(peak)
        return saved, result

    @app.get('/api/v1/candidates/capabilities', response_model=Capabilities)
    def capabilities():
        return capability()

    def job_path(job_id):
        import re
        if not re.fullmatch(ID_PATTERN, job_id):
            raise HTTPException(404, detail='unknown_job')
        return state / (job_id + '.json')

    @app.get('/api/v1/candidates/jobs/{job_id}', response_model=CandidateResult)
    def get_job(job_id: str):
        path = job_path(job_id)
        if not path.is_file():
            raise HTTPException(404, detail='unknown_job')
        try:
            _, result = read_saved(path, job_id)
            return result
        except (OSError, ValueError, KeyError, TypeError):
            raise HTTPException(503, detail='job_evidence_unavailable') from None

    @app.post('/api/v1/candidates/jobs', response_model=CandidateResult)
    def select_reference(request: CandidateRequest):
        started = time.perf_counter()
        if not math.isfinite(request.peak_release_m3s):
            raise HTTPException(422, detail='finite_release_required')
        if not lock.acquire(blocking=False):
            raise HTTPException(409, detail='candidate_service_busy')
        try:
            path = job_path(request.request_id)
            identity = hashlib.sha256(request.model_dump_json().encode()).hexdigest()
            if path.exists():
                saved, result = read_saved(path, request.request_id)
                if saved['request_checksum'] != identity:
                    raise HTTPException(409, detail='request_identity_conflict')
                if result.requested_peak_release_m3s != request.peak_release_m3s:
                    raise ValueError('Job identity mismatch')
                return result.model_copy(update={'cache_hit': True})
            if not request.allow_nearest_stored and request.peak_release_m3s not in roots:
                raise HTTPException(400, detail='requested_peak_not_stored')
            actual = min(roots, key=lambda peak: (abs(peak - request.peak_release_m3s), peak))
            manifest = manifests[actual]
            # Validate references before advertising completion; no scientific writes/import.
            verify(actual)
            base = '/api/v1/prototypes/scenarios/' + manifest['scenario_id']
            result = {'schema_version': '1.0.0', 'job_id': request.request_id, 'request_id': request.request_id,
                'status': 'completed', 'mode': 'stored_reference', 'input_family': FAMILY,
                'requested_peak_release_m3s': request.peak_release_m3s, 'actual_peak_release_m3s': actual,
                'cache_hit': False, 'computed': False, 'engine': 'HEC-RAS stored reference',
                'scientifically_validated': False, 'calibration_status': 'uncalibrated',
                'warnings': ['simulated', 'uncalibrated', 'stored_reference_not_new_prediction'],
                'completed_at': datetime.now(timezone.utc).isoformat(),
                'elapsed_wall_seconds': time.perf_counter() - started,
                'timing_scope': 'reference_selection_and_hash_validation; not hydraulic run or browser-ready latency',
                'source_scenario_id': manifest['scenario_id'], 'source_run_id': manifest['run_id'],
                'reference_resources': {'detail': base, 'layers': base + '/layers', 'impact': base + '/impact',
                    'assumptions': base + '/assumptions', 'quality_report': base + '/quality-report'}}
            temporary = state / (request.request_id + '.pending')
            result = CandidateResult.model_validate(result).model_dump(mode='json')
            try:
                with temporary.open('x', encoding='utf-8') as handle:
                    json.dump({'request_checksum': identity, 'result': result}, handle, allow_nan=False)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.link(temporary, path)  # Atomically publish complete bytes, never overwrite.
            finally:
                temporary.unlink(missing_ok=True)
            return result
        except HTTPException:
            raise
        except (ValueError, OSError, KeyError, TypeError):
            raise HTTPException(503, detail='candidate_reference_unavailable') from None
        finally:
            lock.release()

    return app
