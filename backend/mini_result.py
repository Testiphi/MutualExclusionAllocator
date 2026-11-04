"""Map-only native result validation, shared by HTTP gateway and queue bridge."""
import json
from backend.mini_auth import fail


def native_result(raw, catalog):
    if raw is None:
        return None
    value = json.loads(raw)
    if value.get('schema_version') != 1 or value.get('server') != 'cn' or value.get('catalog_version') != catalog['version']:
        fail(503, 'RESULT_INVALID', '识别结果绑定无效')
    if value.get('status') not in ('complete','partial','rejected'):
        fail(503,'RESULT_INVALID','识别结果状态无效')
    slots = value.get('slots')
    if not isinstance(slots, list) or len(slots) != 5:
        fail(503, 'RESULT_INVALID', '识别结果槽位无效')
    clean = []
    for i, slot in enumerate(slots, 1):
        if slot.get('slot') != i or slot.get('state') not in ('matched', 'ambiguous', 'unresolved'):
            fail(503, 'RESULT_INVALID', '识别结果槽位无效')
        matched = slot['state'] == 'matched'
        if matched and {'big': slot.get('big'), 'small': slot.get('small')} not in catalog['maps']:
            fail(503, 'RESULT_INVALID', '识别结果地图不在目录')
        clean.append({'slot': i, 'state': slot['state'], 'big': slot.get('big') if matched else None,
                      'small': slot.get('small') if matched else None})
    # Do not return observed text/boxes/diagnostics containing unrelated OCR text.
    return {'schema_version': 1, 'server': 'cn', 'catalog_version': catalog['version'],
            'status': value.get('status'), 'slots': clean, 'needs_user_confirmation': True}
