"""Local-only safety rehearsal on an existing explicitly created demo JobStore.

This is a receipt ledger, not another OCR queue. It never starts a model and
cannot wrap a production store. Public HTTP routes/configuration are untouched.
"""
import hashlib
import re
import time

from backend.image_safety_aliyun import SafetyError
from backend.map_recognition import RecognitionError, TTL, validate_image


class LocalModeratedSubmission:
    def __init__(self, store, adapter):
        if store.production or not (store.root / '.racepick-map-demo.json').is_file():
            raise ValueError('Only an explicitly provisioned local demo queue is accepted')
        self.store, self.adapter = store, adapter
        with store.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS local_safety_receipts(
                owner TEXT NOT NULL, request_key TEXT NOT NULL, version TEXT NOT NULL,
                image_sha TEXT NOT NULL, state TEXT NOT NULL, error_code TEXT,
                created REAL NOT NULL, expires REAL NOT NULL,
                PRIMARY KEY(owner,request_key))''')

    def _existing(self, db, owner, key, version, sha):
        job = db.execute('SELECT * FROM jobs WHERE owner=? AND request_key=?', (owner, key)).fetchone()
        if job:
            if (job['server'], job['version'], job['image_sha']) != ('cn', version, sha):
                raise SafetyError('REQUEST_KEY_CONFLICT')
            if job['state'] == 'expired' or job['expires'] <= time.time():
                raise SafetyError('JOB_EXPIRED')
            return job['id']
        return None

    def submit(self, owner, key, version, image, mime):
        if (not isinstance(owner, str) or not re.fullmatch(r'mini-v1:[a-f0-9]{64}', owner)
                or not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,80}', key)
                or not isinstance(version, str) or not re.fullmatch(r'[a-f0-9]{64}', version)):
            raise SafetyError('INVALID_BINDING')
        try:
            validate_image(image, mime)
        except RecognitionError:
            raise SafetyError('IMAGE_INVALID') from None
        sha = hashlib.sha256(image).hexdigest()
        deciding = False
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            existing = self._existing(db, owner, key, version, sha)
            if existing:
                return existing
            row = db.execute('SELECT * FROM local_safety_receipts WHERE owner=? AND request_key=?',
                             (owner, key)).fetchone()
            if row:
                if (row['version'], row['image_sha']) != (version, sha):
                    raise SafetyError('REQUEST_KEY_CONFLICT')
                if row['expires'] <= time.time():
                    raise SafetyError('JOB_EXPIRED')
                if row['state'] != 'approved':
                    raise SafetyError(row['error_code'] or 'IMAGE_SAFETY_UNCERTAIN')
            else:
                now = time.time()
                db.execute('INSERT INTO local_safety_receipts VALUES (?,?,?,?,?,?,?,?)',
                           (owner, key, version, sha, 'deciding', None, now, now+TTL))
                deciding = True
        if deciding:
            try:
                verdict = self.adapter.review(image, mime)
                if verdict != {'approved': True, 'provider': 'aliyun', 'service': 'baselineCheck',
                               'policy_version': 'baseline-none-v1', 'image_sha256': sha}:
                    raise SafetyError('IMAGE_SAFETY_UNAVAILABLE')
            except BaseException as error:
                # Persist ambiguity before propagating; never silently replay a paid operation.
                code = error.code if isinstance(error, SafetyError) else 'IMAGE_SAFETY_UNCERTAIN'
                with self.store.connect() as db:
                    db.execute('UPDATE local_safety_receipts SET state=?,error_code=? WHERE owner=? AND request_key=?',
                               ('rejected' if code == 'IMAGE_SAFETY_REJECTED' else 'uncertain', code, owner, key))
                if isinstance(error, (SafetyError, KeyboardInterrupt, SystemExit)):
                    raise
                raise SafetyError('IMAGE_SAFETY_UNCERTAIN') from None
            with self.store.connect() as db:
                db.execute("UPDATE local_safety_receipts SET state='approved' WHERE owner=? AND request_key=?",
                           (owner, key))
        # Capacity and quotas remain enforced by the original single JobStore transaction.
        # A full queue can retry this same approved key without another supplier call.
        job_id = self.store.create(owner, key, 'cn', version, image, mime)
        with self.store.connect() as db:
            # Do not extend the one-hour lifetime by waiting or retrying after approval.
            row = db.execute('SELECT expires FROM local_safety_receipts WHERE owner=? AND request_key=?',
                             (owner, key)).fetchone()
            db.execute('UPDATE jobs SET expires=min(expires,?) WHERE id=?', (row['expires'], job_id))
        return job_id

    def recover(self, owner, key, version):
        with self.store.connect() as db:
            row = db.execute('SELECT * FROM local_safety_receipts WHERE owner=? AND request_key=?',
                             (owner, key)).fetchone()
            if not row:
                return {'recovery': 'not_found', 'retry_same_key': True}
            if row['version'] != version:
                raise SafetyError('CATALOG_CHANGED')
            if row['expires'] <= time.time():
                raise SafetyError('JOB_EXPIRED')
            existing = self._existing(db, owner, key, version, row['image_sha'])
            if existing:
                return {'recovery': 'found', 'id': existing, 'retry_same_key': False}
            # These are LOCAL diagnostic states, never a change to the native HTTP protocol.
            return {'recovery': row['state'], 'retry_same_key': row['state'] == 'approved',
                    'code': row['error_code']}
