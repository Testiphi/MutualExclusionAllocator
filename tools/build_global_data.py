"""Build the independently bound international runtime data bundle.

From the repository directory:
    python tools/build_global_data.py --source-dir ../数据源/international-prep-20261023
    python tools/build_global_data.py --source-dir ../数据源/international-prep-20261023 --check

Only accepted maintenance JSON/ledger, OC references, identities and the ASEC
catalog are read. Workbooks, candidates, accounts and credentials are not inputs.
The pure build_bundle function is also the fixture entry point for tests.
"""

from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PureWindowsPath
import re
import tempfile


SERVER_ID = 'global'
SCHEMA_VERSION = 1
CATALOG_FILE = 'cars.global.json'
SCORES_FILE = 'gauntlet_data.global.json'
MANIFEST_FILE = 'global-data-manifest.json'
RUNTIME_FILES = (CATALOG_FILE, SCORES_FILE)
CAPABILITIES = {'zones': ['五区'], 'tiers': ['理论'],
                'max_stars_only': True, 'oc': True}
ZONES = ('五区', '四区')
TIERS = ('理论', '高手', '普通', '自动')
SC_TYPES = {'滑栏杆', '滑雪', '跳楼', '跳图', '跳船', '挂桥',
            '稳定跳图', '旧跳图', '新跳图'}
PERFORMANCE_FIELDS = ('score', 'max_speed', 'acceleration', 'handling', 'nitro')
TRACK_FIELDS = ('大地图', '小地图', 'international_track_id',
                'international_region', 'international_track', 'label_status',
                'has_special_route', 'special_route_note')


def canonical_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def file_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2,
                       allow_nan=False) + '\n').encode('utf-8')


def sha256(value):
    return hashlib.sha256(value).hexdigest()


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _number(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def _normalized_name(value):
    return re.sub(r'[^a-z0-9]', '', str(value).casefold())


def _entry_key(track_id, entry):
    _require(isinstance(entry, dict) and isinstance(entry.get('cars'), list)
             and len(entry['cars']) == 1, 'A score must contain exactly one car')
    car = entry['cars'][0]
    _require(isinstance(car, dict) and isinstance(car.get('name'), str)
             and car['name'], 'A score needs a nonempty car name')
    _require(car.get('oc') is None or type(car['oc']) is bool,
             'OC must be a boolean on cars[0]')
    _require(entry.get('sc') is None or type(entry['sc']) is bool,
             'SC must be a boolean')
    sc = bool(entry.get('sc'))
    route = entry.get('sc_type') or None
    _require((sc and route in SC_TYPES) or (not sc and route is None),
             'SC and sc_type are inconsistent')
    _require(_number(entry.get('time')), 'A score needs a positive finite time')
    return track_id, car['name'], bool(car.get('oc')), sc, route


def _catalog(asec, identities, used_names):
    _require(isinstance(asec.get('cars'), list), 'ASEC cars list is missing')
    by_id = {}
    for car in asec['cars']:
        aid = car.get('id')
        _require(type(aid) is int and aid not in by_id, 'Duplicate/invalid ASEC ID')
        by_id[aid] = car
    identity_records = {}
    for car in identities.get('cars', []):
        name = car.get('nickname')
        _require(isinstance(name, str) and name and name not in identity_records,
                 'Duplicate/invalid maintenance nickname')
        identity_records[name] = car
    _require(used_names <= set(identity_records), 'Score has no approved identity')
    result, seen_ids, seen_titles = [], set(), set()
    for name in sorted(used_names):
        identity = identity_records[name]
        aid = identity.get('asec_id')
        _require(aid in by_id and aid not in seen_ids,
                 'Unknown/duplicate physical ASEC identity')
        source = by_id[aid]
        title = source['brand'] + ' ' + source['model']
        _require(_normalized_name(identity.get('title')) == _normalized_name(title),
                 'Maintenance title does not match its ASEC ID')
        _require(title not in seen_titles, 'Duplicate physical vehicle title')
        maximum = source.get('max_stars')
        _require(type(maximum) is int and 1 <= maximum <= 6,
                 'Invalid ASEC maximum stars')
        variant = 'evo' if name.startswith('evo') else 'regular'
        record = {'title': title, 'nickname': name, 'asec_id': aid,
                  'base_title': title, 'base_class': source['car_class'],
                  'class': source['car_class'], 'class_source': 'base_vehicle_class',
                  'variant': variant, 'max_stars': maximum, 'zones': ['五区'],
                  'star_rule': {'min': maximum, 'max': maximum, 'default': maximum}}
        if variant == 'evo':
            record.update({field: None for field in PERFORMANCE_FIELDS})
            record['stats_status'] = 'evo_configuration_unknown'
        else:
            maximum_data = source.get('detail', {}).get('stars', {}).get(
                'star_' + str(maximum), {})
            stats = maximum_data.get('stats')
            _require(isinstance(stats, list) and len(stats) == 4
                     and all(_number(value) for value in stats)
                     and _number(maximum_data.get('rank')),
                     'Non-EVO maximum-star performance is missing')
            record.update(dict(zip(PERFORMANCE_FIELDS,
                                   [maximum_data['rank'], *stats])))
            record['stats_status'] = 'asec_max_star'
        result.append(record)
        seen_ids.add(aid)
        seen_titles.add(title)
    return {'_comment': 'International accepted-score vehicles only; EVO configuration metrics remain unknown.',
            'capabilities': deepcopy(CAPABILITIES),
            '_nickname_map': {car['nickname']: car['title'] for car in result},
            'cars': result}


def build_bundle(active, accepted_ledger, oc_ledger, asec, identities,
                 source_hashes=None, expected_non_oc=None):
    """Return three JSON documents without filesystem access or input mutation."""
    _require(isinstance(active.get('tracks'), list), 'Active tracks are missing')
    tracks, track_ids, map_keys, used_names, active_values = [], {}, set(), set(), {}
    for original in active['tracks']:
        tid = original.get('international_track_id')
        map_key = original.get('大地图'), original.get('小地图')
        _require(isinstance(tid, str) and tid and tid not in track_ids
                 and all(isinstance(part, str) and part for part in map_key)
                 and map_key not in map_keys, 'Duplicate/invalid international track')
        track = {field: deepcopy(original[field]) for field in TRACK_FIELDS
                 if field in original}
        for zone in ZONES:
            _require(isinstance(original.get(zone), dict), 'Missing explicit zone')
            track[zone] = {}
            for tier in TIERS:
                entries = original[zone].get(tier)
                _require(isinstance(entries, list), 'Missing explicit tier')
                _require((zone, tier) == ('五区', '理论') or not entries,
                         'International phase one supports only five-zone theory')
                track[zone][tier] = []
                for entry in entries:
                    key = _entry_key(tid, entry)
                    _require(key not in active_values, 'Duplicate accepted score')
                    _require(entry['cars'][0].get('stars') is None,
                             'Phase one accepts maximum-star theory without star columns')
                    clean = {'cars': [{'name': key[1]}], 'time': entry['time']}
                    if key[2]:
                        _require(not key[3], 'Phase-one OC must use an ordinary route')
                        clean['cars'][0]['oc'] = True
                    if key[3]:
                        clean.update(sc=True, sc_type=key[4])
                    track[zone][tier].append(clean)
                    active_values[key] = entry['time']
                    used_names.add(key[1])
        tracks.append(track)
        track_ids[tid] = track
        map_keys.add(map_key)
    ledger_values, ledger_identities = {}, {}
    for record in accepted_ledger.get('records', []):
        original_car = (record.get('cars') or [{}])[0]
        name = record.get('car') or original_car.get('name')
        oc = record.get('oc', original_car.get('oc'))
        if record.get('oc') is not None and original_car.get('oc') is not None:
            _require(record['oc'] == original_car['oc'], 'Ledger OC flags disagree')
        car = {'name': name}
        if oc is not None:
            car['oc'] = oc
        _require(record.get('stars', original_car.get('stars')) is None,
                 'Accepted ledger contains an explicit-star score')
        entry = {'cars': [car], 'time': record.get('time'),
                 'sc': record.get('sc'), 'sc_type': record.get('sc_type')}
        key = _entry_key(record.get('target_id'), entry)
        _require(key not in ledger_values, 'Duplicate accepted ledger identity')
        ledger_values[key] = record['time']
        ledger_identities.setdefault(key[1], set()).add(
            record.get('asec_id', record.get('base_car_id')))
    _require(ledger_values == active_values, 'Active JSON and accepted ledger differ')
    if expected_non_oc is not None:
        _require(sum(not key[2] for key in active_values) == expected_non_oc,
                 'Current maintenance non-OC count differs')
    catalog = _catalog(asec, identities, used_names)
    car_ids = {car['nickname']: car['asec_id'] for car in catalog['cars']}
    for name, ids in ledger_identities.items():
        _require(ids == {car_ids[name]}, 'Accepted ledger ASEC identity differs')
    runtime_values = dict(active_values)
    all_keys = set(active_values)
    oc_count = sum(key[2] for key in active_values)
    records = oc_ledger.get('records')
    _require(isinstance(records, list), 'OC records are missing')
    _require(oc_ledger.get('count') == len(records), 'OC reference count differs')
    for record in records:
        tid = record.get('international_track_id')
        _require(tid in track_ids, 'OC references an unknown track')
        _require(record.get('zone') == '五区' and record.get('tier') == '理论',
                 'OC source is outside phase-one capability')
        key = _entry_key(tid, record)
        _require(key[2] and not key[3], 'Phase-one OC must be explicitly OC and ordinary')
        _require(key[1] in car_ids and record.get('base_car_id') == car_ids[key[1]],
                 'OC must reuse an accepted physical vehicle identity')
        _require(str(record.get('status', '')).startswith('accepted'),
                 'OC reference is not accepted')
        if record.get('source_kind') == 'user_authorized_oc_delta_estimate':
            base_time = active_values.get((tid, key[1], False, False, None))
            _require(_number(base_time) and record.get('source_time') == base_time
                     and record.get('adjustment') == -0.1,
                     'OC delta estimate has no matching ordinary source')
            estimate = float((Decimal(str(base_time)) - Decimal('0.1')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP))
            _require(record['time'] == estimate, 'OC delta estimate differs from source rule')
        else:
            _require(record.get('source_kind') == 'user_direct_final_theory',
                     'OC source must be an explicitly accepted final theory value')
        if key in all_keys:
            _require(runtime_values.get(key) == record['time'],
                     'Active and supplemental OC values conflict')
            continue
        track_ids[tid]['五区']['理论'].append(
            {'cars': [{'name': key[1], 'oc': True}], 'time': record['time']})
        all_keys.add(key)
        runtime_values[key] = record['time']
        oc_count += 1
    for track in tracks:
        track['五区']['理论'].sort(key=lambda entry: (entry['time'],
            entry['cars'][0]['name'], bool(entry['cars'][0].get('oc')),
            bool(entry.get('sc')), entry.get('sc_type') or ''))
    scores = {'_version': 2,
              '_comment': 'International five-zone maximum-star theory; OC and special routes have independent score identities.',
              'capabilities': deepcopy(CAPABILITIES),
              'tier_info': {'理论': {'label': '理论档',
                  'desc': '国际服满星理论成绩，普通与OC、特殊跑法分别保存'}},
              'tracks': tracks}
    payload_hashes = {'catalog_payload_sha256': sha256(canonical_bytes(catalog)),
                      'scores_payload_sha256': sha256(canonical_bytes(scores))}
    version_binding = {'server_id': SERVER_ID, 'schema_version': SCHEMA_VERSION,
                       **payload_hashes}
    metadata = {**version_binding,
                'dataset_version': sha256(canonical_bytes(version_binding)),
                'manifest_file': MANIFEST_FILE}
    catalog = {'_meta': deepcopy(metadata), **catalog}
    scores = {'_meta': deepcopy(metadata), **scores}
    count_sc = sum(bool(entry.get('sc')) for track in tracks
                   for entry in track['五区']['理论'])
    manifest = {'_meta': deepcopy(metadata), 'capabilities': deepcopy(CAPABILITIES),
                'files': {}, 'counts': {'physical_cars': len(catalog['cars']),
                    'tracks': len(tracks), 'covered_tracks': sum(bool(t['五区']['理论']) for t in tracks),
                    'score_entries': len(all_keys),
                    'non_oc_entries': sum(not key[2] for key in active_values),
                    'oc_entries': oc_count, 'special_entries': count_sc,
                    'normal_entries': len(all_keys) - count_sc},
                'sources': dict(sorted((source_hashes or {}).items()))}
    for name, value, payload_name in (
            (CATALOG_FILE, catalog, 'catalog_payload_sha256'),
            (SCORES_FILE, scores, 'scores_payload_sha256')):
        raw = file_bytes(value)
        manifest['files'][name] = {'sha256': sha256(raw), 'bytes': len(raw),
                                  'payload_sha256': metadata[payload_name]}
    validate_global_bundle(catalog, scores, manifest)
    return {CATALOG_FILE: catalog, SCORES_FILE: scores, MANIFEST_FILE: manifest}


def validate_global_bundle(catalog, scores, manifest, raw_files=None):
    """Fail closed on server, version, payload, capabilities or identity mismatch."""
    meta = catalog.get('_meta')
    _require(isinstance(meta, dict) and meta.get('server_id') == SERVER_ID
             and meta.get('schema_version') == SCHEMA_VERSION
             and meta.get('manifest_file') == MANIFEST_FILE, 'Not a global data bundle')
    _require(meta == scores.get('_meta') == manifest.get('_meta'),
             'Mixed catalog, scores or manifest metadata')
    _require(catalog.get('capabilities') == scores.get('capabilities')
             == manifest.get('capabilities') == CAPABILITIES, 'Capability mismatch')
    binding = {'server_id': SERVER_ID, 'schema_version': SCHEMA_VERSION}
    for value, field in ((catalog, 'catalog_payload_sha256'),
                         (scores, 'scores_payload_sha256')):
        payload = {key: item for key, item in value.items() if key != '_meta'}
        binding[field] = sha256(canonical_bytes(payload))
        _require(meta.get(field) == binding[field], 'Payload hash mismatch')
    _require(meta.get('dataset_version') == sha256(canonical_bytes(binding)),
             'Dataset version mismatch')
    _require(set(manifest.get('files', {})) == set(RUNTIME_FILES), 'Manifest file set differs')
    for name, value, field in ((CATALOG_FILE, catalog, 'catalog_payload_sha256'),
                               (SCORES_FILE, scores, 'scores_payload_sha256')):
        raw = raw_files[name] if raw_files is not None else file_bytes(value)
        declared = manifest['files'][name]
        _require(declared.get('sha256') == sha256(raw)
                 and declared.get('bytes') == len(raw)
                 and declared.get('payload_sha256') == meta[field], 'Manifest bytes mismatch')
    names, ids, titles = set(), set(), set()
    for car in catalog.get('cars', []):
        name, aid, title = car.get('nickname'), car.get('asec_id'), car.get('title')
        _require(isinstance(name, str) and name and name not in names
                 and type(aid) is int and aid not in ids
                 and isinstance(title, str) and title and title not in titles,
                 'Duplicate/invalid runtime physical car')
        maximum = car.get('max_stars')
        _require(type(maximum) is int and 1 <= maximum <= 6
                 and car.get('zones') == ['五区']
                 and car.get('star_rule') == {'min': maximum, 'max': maximum, 'default': maximum},
                 'Runtime vehicle rules are not maximum-star five-zone only')
        if car.get('variant') == 'evo':
            _require(name.startswith('evo') and car.get('stats_status') == 'evo_configuration_unknown'
                     and all(car.get(field) is None for field in PERFORMANCE_FIELDS),
                     'EVO must not inherit ordinary performance values')
        else:
            _require(car.get('variant') == 'regular'
                     and car.get('stats_status') == 'asec_max_star'
                     and all(_number(car.get(field)) for field in PERFORMANCE_FIELDS),
                     'Regular runtime performance is incomplete')
        names.add(name)
        ids.add(aid)
        titles.add(title)
    _require(catalog.get('_nickname_map') == {c['nickname']: c['title'] for c in catalog['cars']},
             'Runtime nickname map differs from physical catalog')
    seen, used, track_ids, maps = set(), set(), set(), set()
    non_oc, oc, special, covered = 0, 0, 0, 0
    for track in scores.get('tracks', []):
        tid = track.get('international_track_id')
        map_key = track.get('大地图'), track.get('小地图')
        _require(isinstance(tid, str) and tid and tid not in track_ids and map_key not in maps,
                 'Duplicate runtime track')
        for zone in ZONES:
            _require(isinstance(track.get(zone), dict) and set(track[zone]) == set(TIERS),
                     'Runtime zone/tier structure differs')
            for tier, entries in track[zone].items():
                _require(isinstance(entries, list), 'Runtime tier must be a list')
                _require((zone, tier) == ('五区', '理论') or not entries,
                         'Unsupported runtime zone/tier is populated')
                for entry in entries:
                    key = _entry_key(tid, entry)
                    _require(key not in seen and key[1] in names
                             and entry['cars'][0].get('stars') is None,
                             'Duplicate, unknown or non-maximum-star runtime score')
                    _require(not key[2] or not key[3],
                             'Phase-one OC must use an ordinary route')
                    seen.add(key)
                    used.add(key[1])
                    oc += int(key[2])
                    non_oc += int(not key[2])
                    special += int(key[3])
        covered += int(bool(track['五区']['理论']))
        track_ids.add(tid)
        maps.add(map_key)
    _require(used == names, 'Runtime pool must contain exactly score-bearing physical cars')
    expected_counts = {'physical_cars': len(names), 'tracks': len(track_ids),
                       'covered_tracks': covered, 'score_entries': len(seen),
                       'non_oc_entries': non_oc, 'oc_entries': oc,
                       'special_entries': special, 'normal_entries': len(seen) - special}
    _require(manifest.get('counts') == expected_counts, 'Manifest counts differ')
    return expected_counts


def _read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _maintenance_file(directory, reference):
    _require(isinstance(reference, str) and reference, 'Missing maintenance input reference')
    # Older pointers contain local absolute paths. Relocate their filename under
    # the explicitly supplied maintenance directory; never follow personal paths.
    windows = PureWindowsPath(reference)
    if windows.is_absolute() or Path(reference).is_absolute():
        relative = Path(windows.name)
    else:
        relative = Path(reference.replace('\\', '/'))
    result = (directory / relative).resolve()
    _require(result.is_relative_to(directory.resolve()), 'Maintenance input escapes source directory')
    return result


def load_source(source_dir):
    """Load one accepted preparation directory; no personal absolute-path dependency."""
    source_dir = Path(source_dir).resolve()
    maintenance = source_dir if (source_dir / 'current-maintenance.json').is_file() else source_dir / 'maintenance'
    prep = maintenance.parent
    pointer_path = maintenance / 'current-maintenance.json'
    pointer = _read_json(pointer_path)
    paths = {'current-maintenance.json': pointer_path,
             'cars-full.json': prep / 'cars-full.json',
             'gauntlet_data_international.json': _maintenance_file(maintenance, pointer.get('active_json')),
             'score-ledger.json': _maintenance_file(maintenance, pointer.get('active_ledger')),
             'oc-score-ledger.json': _maintenance_file(maintenance, pointer.get('oc_reference_file')),
             'maintenance-car-identities.json': _maintenance_file(maintenance, pointer.get('maintenance_identity_catalog'))}
    raw = {name: path.read_bytes() for name, path in paths.items()}
    documents = {name: json.loads(value.decode('utf-8')) for name, value in raw.items()}
    bundle = build_bundle(documents['gauntlet_data_international.json'],
                         documents['score-ledger.json'], documents['oc-score-ledger.json'],
                         documents['cars-full.json'], documents['maintenance-car-identities.json'],
                         {name: sha256(value) for name, value in raw.items()},
                         pointer.get('active_non_oc_records'))
    _require(all(path.read_bytes() == raw[name] for name, path in paths.items()),
             'Source files changed during generation')
    return bundle, set(paths.values())


def write_bundle(bundle, output_dir, source_paths=()):
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    targets = {name: output_dir / name for name in (*RUNTIME_FILES, MANIFEST_FILE)}
    _require(not set(targets.values()) & set(source_paths), 'Output would overwrite a source input')
    temporary = {}
    try:
        for name, target in targets.items():
            with tempfile.NamedTemporaryFile(dir=output_dir, prefix='.' + name + '.',
                                              suffix='.tmp', delete=False) as handle:
                handle.write(file_bytes(bundle[name]))
                handle.flush()
                os.fsync(handle.fileno())
                temporary[name] = Path(handle.name)
        # Manifest is replaced last. A reader that catches a partial replacement
        # rejects the mismatched pair instead of silently loading national data.
        for name, target in targets.items():
            os.replace(temporary[name], target)
            temporary.pop(name)
    finally:
        for path in temporary.values():
            path.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, required=True,
                        help='Preparation root or its maintenance directory')
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--check', action='store_true', help='Compare reproducible outputs without writing')
    args = parser.parse_args(argv)
    try:
        bundle, source_paths = load_source(args.source_dir)
        if args.check:
            for name, value in bundle.items():
                _require((args.output_dir / name).read_bytes() == file_bytes(value),
                         'Generated output differs: ' + name)
        else:
            write_bundle(bundle, args.output_dir, source_paths)
        print(json.dumps({'server_id': SERVER_ID, 'check_only': args.check,
                          'dataset_version': bundle[MANIFEST_FILE]['_meta']['dataset_version'],
                          **bundle[MANIFEST_FILE]['counts']}, ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, 'Global data build failed: ' + str(error) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
