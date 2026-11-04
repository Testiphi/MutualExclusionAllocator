"""Synthetic local images, fake supplier, one temporary JobStore; network forbidden."""
import copy
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from PIL import Image
from backend.image_safety_aliyun import (
    AliyunBaselineAdapter, SafetyError, load_config, parse_config)
from backend.image_safety_local import LocalModeratedSubmission
from backend.map_recognition import JobStore, RecognitionError

ROOT = Path(__file__).resolve().parents[1]
OWNER = 'mini-v1:' + 'a'*64
VERSION = 'b'*64
KEY = 'baseline-fixture-key-0001'


def image(color='red'):
    out = io.BytesIO()
    Image.new('RGB', (640, 360), color).save(out, format='PNG')
    return out.getvalue()


def config(**changes):
    value = json.loads((ROOT/'production/aliyun-baseline.config.example.json').read_text())
    return {**value, 'mode': 'simulation', **changes}


def transport():
    fake = Mock()
    fake.is_simulated = True
    fake.describe_upload_token.return_value = {'statusCode': 200, 'body': {'Code': 200, 'Data': {
        'AccessKeyId': 'fixture-not-a-key', 'AccessKeySecret': 'fixture-not-a-secret',
        'SecurityToken': 'fixture-only-token', 'BucketName': 'fixture-bucket',
        'FileNamePrefix': 'temporary-fixture/',
        'OssInternetEndPoint': 'https://oss-cn-shanghai.aliyuncs.com',
        'Expiration': int(time.time()) + 3600}}}
    fake.upload_image.return_value = {'status': 200}

    def approved(**kwargs):
        data_id = json.loads(kwargs['service_parameters'])['dataId']
        return {'statusCode': 200, 'body': {'Code': 200, 'RequestId': 'fixture-request',
                'Data': {'RiskLevel': 'none', 'DataId': data_id,
                         'Result': [{'Label': 'nonLabel', 'Description': 'fixture normal'}]}}}
    fake.image_moderation.side_effect = approved
    return fake


class BaselineAdapterTests(unittest.TestCase):
    def setUp(self):
        self.net = patch('socket.socket.connect', side_effect=AssertionError('NETWORK_FORBIDDEN'))
        self.net.start(); self.addCleanup(self.net.stop)
        self.fake = transport()
        self.adapter = AliyunBaselineAdapter(parse_config(config()), self.fake)
        self.raw = image()

    def test_template_disabled_no_credentials_read_or_transport_call(self):
        declared = load_config(ROOT/'production/aliyun-baseline.config.example.json')
        with self.assertRaisesRegex(SafetyError, 'RECOGNITION_DISABLED'):
            AliyunBaselineAdapter(declared, self.fake).review(self.raw, 'image/png')
        self.assertEqual(self.fake.mock_calls, [])

    def test_config_rejects_live_custom_host_services_retries_and_relaxed_policy(self):
        for change in [{'mode': 'automatic'}, {'region': 'us-west-1'}, {'service': 'postImageCheck'},
                       {'endpoint': 'https://evil.test'}, {'automatic_retries': 1},
                       {'automatic_retries': False}, {'allow_risk_levels': ['none', 'low']},
                       {'credentials_file': '../../secret'}, {'total_timeout_seconds': 0},
                       {'connect_timeout_seconds': True}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                parse_config(config(**change))

    def test_transport_must_explicitly_be_simulated(self):
        self.fake.is_simulated = False
        with self.assertRaisesRegex(SafetyError, 'TRANSPORT_DISABLED'):
            self.adapter.review(self.raw, 'image/png')
        self.assertEqual(self.fake.mock_calls, [])

    def test_success_uses_official_three_steps_with_no_identity_or_image_url(self):
        verdict = self.adapter.review(self.raw, 'image/png')
        self.assertTrue(verdict['approved'])
        self.assertEqual([c[0] for c in self.fake.mock_calls],
                         ['describe_upload_token', 'upload_image', 'image_moderation'])
        args = self.fake.image_moderation.call_args.kwargs
        self.assertEqual(args['service'], 'baselineCheck')
        params = json.loads(args['service_parameters'])
        self.assertEqual(set(params), {'ossBucketName', 'ossObjectName', 'dataId'})
        self.assertNotIn('fixture-not-a-secret', repr(verdict))
        for call in self.fake.mock_calls:
            self.assertEqual(call.kwargs['retries'], 0)
            self.assertLessEqual(call.kwargs['timeout'], 15)

    def test_invalid_image_never_leaves_adapter(self):
        for raw, mime in [(b'not-an-image', 'image/png'), (self.raw, 'image/jpeg'),
                          (b'x'*8388609, 'image/png')]:
            with self.subTest(mime=mime), self.assertRaisesRegex(SafetyError, 'IMAGE_INVALID'):
                self.adapter.review(raw, mime)
        self.assertEqual(self.fake.mock_calls, [])

    def test_risk_levels_and_manual_review_never_approve(self):
        original = self.fake.image_moderation.side_effect
        for level in ['low', 'medium', 'high']:
            def outcome(level=level, **kwargs):
                value = original(**kwargs); value['body']['Data']['RiskLevel'] = level
                return value
            self.fake.image_moderation.side_effect = outcome
            with self.subTest(level=level), self.assertRaisesRegex(SafetyError, 'IMAGE_SAFETY_REJECTED'):
                self.adapter.review(self.raw, 'image/png')
        def manual(**kwargs):
            value = original(**kwargs); value['body']['Data']['ManualTaskId'] = 'fixture-human'
            return value
        self.fake.image_moderation.side_effect = manual
        with self.assertRaisesRegex(SafetyError, 'IMAGE_SAFETY_REJECTED'):
            self.adapter.review(self.raw, 'image/png')

    def test_malformed_http_business_and_missing_results_fail_closed(self):
        for response in [None, {'statusCode': 500, 'body': {}},
                         {'statusCode': 200, 'body': {'Code': 408, 'Msg': 'private provider text'}},
                         {'statusCode': True, 'body': {'Code': 200}},
                         {'statusCode': 200, 'body': {'Code': 200, 'Data': {'RiskLevel': 'none'}}}]:
            self.fake.image_moderation.side_effect = None
            self.fake.image_moderation.return_value = response
            with self.subTest(response=response), self.assertRaisesRegex(SafetyError, 'UNAVAILABLE') as caught:
                self.adapter.review(self.raw, 'image/png')
            self.assertNotIn('private provider text', str(caught.exception))

    def test_mismatched_data_id_or_exempt_library_is_not_approval(self):
        original = self.fake.image_moderation.side_effect
        for field, value in [('DataId', 'stale-response'), ('Result', []),
                             ('Result', [{'Label': 'nonLabel_lib'}]), ('RiskLevel', 'unknown')]:
            def outcome(field=field, value=value, **kwargs):
                response = original(**kwargs); response['body']['Data'][field] = value
                return response
            self.fake.image_moderation.side_effect = outcome
            with self.subTest(field=field, value=value), self.assertRaisesRegex(SafetyError, 'UNAVAILABLE'):
                self.adapter.review(self.raw, 'image/png')

    def test_upload_token_untrusted_endpoint_or_expired_is_rejected(self):
        original = copy.deepcopy(self.fake.describe_upload_token.return_value)
        for field, value in [('OssInternetEndPoint', 'http://127.0.0.1'),
                             ('OssInternetEndPoint', 'https://evil.test'),
                             ('BucketName', '../escape'), ('FileNamePrefix', '../escape/'),
                             ('Expiration', int(time.time())-1)]:
            response = copy.deepcopy(original); response['body']['Data'][field] = value
            self.fake.describe_upload_token.return_value = response
            with self.subTest(field=field), self.assertRaisesRegex(SafetyError, 'UNAVAILABLE'):
                self.adapter.review(self.raw, 'image/png')
        self.fake.upload_image.assert_not_called()

    def test_timeout_and_uncertain_response_do_not_retry_or_leak(self):
        for error in [TimeoutError('fixture-secret'), OSError('fixture-secret')]:
            self.fake.reset_mock(); self.fake.image_moderation.side_effect = error
            with self.assertRaises(SafetyError) as caught:
                self.adapter.review(self.raw, 'image/png')
            self.assertNotIn('fixture-secret', str(caught.exception))
            self.assertEqual(self.fake.image_moderation.call_count, 1)

    def test_late_success_is_discarded(self):
        adapter = AliyunBaselineAdapter(parse_config(config()), self.fake,
                                        clock=iter([0, 0, 1, 2, 61]).__next__)
        with self.assertRaisesRegex(SafetyError, 'IMAGE_SAFETY_TIMEOUT'):
            adapter.review(self.raw, 'image/png')


class LocalSingleQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='baseline-local-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'.racepick-map-demo.json').write_text(
            json.dumps({'kind': 'racepick-local-map-recognition'}))
        self.store = JobStore(self.root)
        self.fake = transport()
        self.adapter = AliyunBaselineAdapter(parse_config(config()), self.fake)
        self.local = LocalModeratedSubmission(self.store, self.adapter)
        self.raw = image()

    def submit(self, **kwargs):
        return self.local.submit(kwargs.get('owner', OWNER), kwargs.get('key', KEY),
            kwargs.get('version', VERSION), kwargs.get('raw', self.raw), 'image/png')

    def test_approved_job_enters_only_existing_queue_and_response_loss_recovers(self):
        job = self.submit()
        self.assertEqual(self.submit(), job)
        reopened = LocalModeratedSubmission(JobStore(self.root), self.adapter)
        self.assertEqual(reopened.recover(OWNER, KEY, VERSION),
                         {'recovery': 'found', 'id': job, 'retry_same_key': False})
        self.assertEqual(self.fake.image_moderation.call_count, 1)
        self.assertEqual(self.store.claim()['id'], job)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM jobs').fetchone()[0], 1)
        self.assertEqual(list(self.root.glob('*.sqlite3')), [self.store.path])

    def test_same_key_changed_image_or_catalog_rejected_without_supplier(self):
        self.submit()
        for kwargs in [{'raw': image('blue')}, {'version': 'c'*64}]:
            with self.subTest(kwargs=list(kwargs)), self.assertRaisesRegex(SafetyError, 'REQUEST_KEY_CONFLICT'):
                self.submit(**kwargs)
        self.assertEqual(self.fake.image_moderation.call_count, 1)

    def test_different_owner_cannot_recover_original(self):
        self.submit()
        self.assertEqual(self.local.recover('mini-v1:'+'d'*64, KEY, VERSION),
                         {'recovery': 'not_found', 'retry_same_key': True})

    def test_rejection_and_lost_supplier_response_are_not_resubmitted_after_reopen(self):
        for code in ['IMAGE_SAFETY_REJECTED', 'IMAGE_SAFETY_TIMEOUT', 'IMAGE_SAFETY_UNAVAILABLE']:
            adapter = Mock(); adapter.review.side_effect = SafetyError(code)
            local = LocalModeratedSubmission(self.store, adapter)
            key = 'fixture-error-key-' + code
            for _ in range(2):
                with self.assertRaisesRegex(SafetyError, code):
                    local.submit(OWNER, key, VERSION, self.raw, 'image/png')
                local = LocalModeratedSubmission(JobStore(self.root), adapter)
            self.assertEqual(adapter.review.call_count, 1)
            self.assertFalse(local.recover(OWNER, key, VERSION)['retry_same_key'])
        self.assertIsNone(self.store.claim())
        self.assertEqual(list(self.store.media.iterdir()), [])

    def test_full_original_queue_preserves_approval_then_retries_without_resending(self):
        for i in range(8):
            self.store.create('web-fixture-'+str(i), 'web-fixture-key-'+str(i), 'cn', VERSION,
                              self.raw, 'image/png')
        with self.assertRaises(RecognitionError) as caught:
            self.submit()
        self.assertEqual(caught.exception.status, 429)
        self.assertTrue(self.local.recover(OWNER, KEY, VERSION)['retry_same_key'])
        self.store.cancel('web-fixture-0', self.store.claim()['id'], 'cn')
        job = self.submit()
        self.assertEqual(self.fake.image_moderation.call_count, 1)
        self.assertEqual(self.store.get(OWNER, job, 'cn')['state'], 'queued')

    def test_two_owner_limit_is_still_enforced_by_original_store(self):
        self.submit()
        self.submit(key='baseline-second-key')
        with self.assertRaises(RecognitionError) as caught:
            self.submit(key='baseline-third-key')
        self.assertEqual(caught.exception.status, 429)

    def test_cancelled_job_retry_does_not_resurrect_and_late_result_is_ignored(self):
        job = self.submit(); self.store.claim()
        self.store.cancel(OWNER, job, 'cn')
        self.store.finish(job, result={'fixture': True})
        self.assertEqual(self.submit(), job)
        row = self.store.get(OWNER, job, 'cn')
        self.assertEqual((row['state'], row['result']), ('cancelled', None))
        self.assertEqual(self.fake.image_moderation.call_count, 1)

    def test_expired_receipt_cannot_issue_another_supplier_request(self):
        self.submit()
        with self.store.connect() as db:
            db.execute('UPDATE local_safety_receipts SET expires=?', (time.time()-1,))
            db.execute('UPDATE jobs SET expires=?', (time.time()-1,))
        with self.assertRaisesRegex(SafetyError, 'JOB_EXPIRED'):
            self.submit()
        self.assertEqual(self.fake.image_moderation.call_count, 1)

    def test_stale_deciding_record_after_process_exit_blocks_resubmission(self):
        import hashlib
        with self.store.connect() as db:
            db.execute('INSERT INTO local_safety_receipts VALUES (?,?,?,?,?,?,?,?)',
                (OWNER, KEY, VERSION, hashlib.sha256(self.raw).hexdigest(), 'deciding', None,
                 time.time()-10, time.time()+3000))
        with self.assertRaisesRegex(SafetyError, 'IMAGE_SAFETY_UNCERTAIN'):
            self.submit()
        self.fake.image_moderation.assert_not_called()

    def test_concurrent_same_key_does_not_send_a_second_supplier_request(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        entered, release = Event(), Event()
        original = self.fake.image_moderation.side_effect
        def slow(**kwargs):
            entered.set()
            if not release.wait(5):
                raise TimeoutError('fixture coordination timeout')
            return original(**kwargs)
        self.fake.image_moderation.side_effect = slow
        with ThreadPoolExecutor(max_workers=1) as executor:
            first = executor.submit(self.submit)
            try:
                self.assertTrue(entered.wait(5))
                with self.assertRaisesRegex(SafetyError, 'IMAGE_SAFETY_UNCERTAIN'):
                    self.submit()
                self.assertFalse(self.local.recover(OWNER, KEY, VERSION)['retry_same_key'])
            finally:
                release.set()
            job = first.result(timeout=5)
        self.assertEqual(self.submit(), job)
        self.assertEqual(self.fake.image_moderation.call_count, 1)

    def test_lost_response_after_queue_commit_recovers_without_supplier_call(self):
        original = self.store.create
        def committed_then_lost(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError('fixture response lost')
        with patch.object(self.store, 'create', side_effect=committed_then_lost):
            with self.assertRaises(OSError):
                self.submit()
        recovered = self.local.recover(OWNER, KEY, VERSION)
        self.assertEqual(recovered['recovery'], 'found')
        self.assertEqual(self.submit(), recovered['id'])
        self.assertEqual(self.fake.image_moderation.call_count, 1)

    def test_production_queue_is_rejected_before_schema_changes(self):
        self.store.production = True
        with self.assertRaises(ValueError):
            LocalModeratedSubmission(self.store, self.adapter)


if __name__ == '__main__':
    unittest.main()
