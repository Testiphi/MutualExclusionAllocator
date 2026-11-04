"""Official installed SDK signing/models with a fake HTTP boundary: never send."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest
from urllib.parse import parse_qs,urlsplit
from unittest.mock import patch

from backend.image_safety_aliyun import parse_config, AliyunBaselineAdapter, SafetyError
from backend.image_safety_sdk import _SdkTransport,SdkProcessReviewer,read_credentials,_BoundedHTTPS
from backend.test_image_safety_aliyun import config,image


def fake_hang(connection,config,raw,mime):
    time.sleep(5)


def fake_approval(connection,config,raw,mime):
    connection.send({'ok':{'approved':True,'provider':'aliyun','service':'baselineCheck',
        'policy_version':'baseline-none-v1','image_sha256':hashlib.sha256(raw).hexdigest()}})
    connection.close()


class ReviewerGateTests(unittest.TestCase):
    def test_gate_denies_before_process_or_credentials(self):
        reviewer=SdkProcessReviewer(parse_config(config(mode='live')))
        with patch('backend.image_safety_sdk.read_credentials',side_effect=AssertionError()),patch('multiprocessing.get_context',side_effect=AssertionError()):
            with self.assertRaisesRegex(SafetyError,'RECOGNITION_DISABLED'):reviewer.review(image(),'image/png')

    def test_private_credentials_loader_strict_shape_and_no_path_echo(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder).resolve()/'private.json'
            path.write_text(json.dumps({'access_key_id':'fixture-only','access_key_secret':'fixture-only-secret'}));path.chmod(0o600)
            self.assertEqual(read_credentials(path)['access_key_id'],'fixture-only')
            path.write_text(json.dumps({'access_key_id':'fixture','access_key_secret':'fixture','extra':'bad'}))
            with self.assertRaises(SafetyError):read_credentials(path)

    def test_real_child_success_uses_synthetic_result_without_network(self):
        reviewer=SdkProcessReviewer(parse_config(config(mode='live')),allow_live_calls=True,child_target=fake_approval)
        self.assertTrue(reviewer.review(image(),'image/png')['approved'])

    def test_hard_deadline_reaps_a_hung_child(self):
        settings=parse_config(config(mode='live',connect_timeout_seconds=1,read_timeout_seconds=1,total_timeout_seconds=1))
        reviewer=SdkProcessReviewer(settings,allow_live_calls=True,child_target=fake_hang)
        started=time.monotonic()
        with self.assertRaisesRegex(SafetyError,'IMAGE_SAFETY_TIMEOUT'):reviewer.review(image(),'image/png')
        self.assertLess(time.monotonic()-started,4)


@unittest.skipUnless(importlib.util.find_spec('alibabacloud_green20220302') and importlib.util.find_spec('oss2'),'Isolated pinned SDK dependencies required')
class RealSdkMockWireTests(unittest.TestCase):
    def test_actual_sdk_does_not_retry_http_failure(self):
        from unittest.mock import Mock
        settings=parse_config(config(mode='live'))
        sender=Mock()
        sender.send.return_value=(500,{'content-type':'application/json'},
            b'{"Code":"InternalError","Message":"fixture-private-error","RequestId":"fixture"}')
        with patch('socket.socket.connect',side_effect=AssertionError('NETWORK_FORBIDDEN')):
            transport=_SdkTransport(settings,{'access_key_id':'fixture-id','access_key_secret':'fixture-secret'},sender=sender)
            try:
                with self.assertRaisesRegex(SafetyError,'IMAGE_SAFETY_UNAVAILABLE') as caught:
                    AliyunBaselineAdapter(settings,transport,allow_live_calls=True).review(image(),'image/png')
            finally:transport.close()
        self.assertEqual(sender.send.call_count,1)
        self.assertNotIn('fixture-private-error',str(caught.exception))

    def test_real_sdk_signing_request_models_and_oss_upload_are_offline(self):
        settings=parse_config(config(mode='live'))
        calls=[]
        class Sender:
            def send(self,method,url,headers,data,timeout,expected_host):
                self.assertion=None
                calls.append({'method':method,'url':url,'headers':dict(headers),'data':data,'timeout':timeout,'host':expected_host})
                if expected_host.startswith('fixture-bucket.'):
                    return 200,{'content-length':'0','etag':hashlib.md5(image()).hexdigest()},b''
                body=parse_qs(data.decode() if isinstance(data,bytes) else data or '')
                query=parse_qs(urlsplit(url).query)
                action=headers.get('x-acs-action') or query.get('Action',[None])[0] or body.get('Action',[None])[0]
                if action=='DescribeUploadToken':
                    response={'Code':200,'Data':{'AccessKeyId':'fixture-temporary','AccessKeySecret':'fixture-secret',
                        'SecurityToken':'fixture-token','BucketName':'fixture-bucket','FileNamePrefix':'upload/fixture/',
                        'OssInternetEndPoint':'https://oss-cn-shanghai.aliyuncs.com','Expiration':int(time.time())+3600}}
                else:
                    assert action=='ImageModeration',action
                    service=body.get('Service',query.get('Service',[None]))[0]
                    assert service=='baselineCheck',service
                    params=json.loads(body.get('ServiceParameters',query.get('ServiceParameters',[None]))[0])
                    response={'Code':200,'Data':{'DataId':params['dataId'],'RiskLevel':'none','Result':[{'Label':'nonLabel'}]}}
                return 200,{'content-type':'application/json'},json.dumps(response).encode()
        # The private transport is only constructed directly for this serial offline SDK test.
        with patch('socket.socket.connect',side_effect=AssertionError('NETWORK_FORBIDDEN')):
            transport=_SdkTransport(settings,{'access_key_id':'fixture-id','access_key_secret':'fixture-secret'},sender=Sender())
            try:verdict=AliyunBaselineAdapter(settings,transport,allow_live_calls=True).review(image(),'image/png')
            finally:transport.close()
        self.assertTrue(verdict['approved']);self.assertEqual(len(calls),3)
        self.assertTrue(any('authorization' in {k.lower() for k in c['headers']} for c in calls))
        self.assertEqual({c['host'] for c in calls},{settings.endpoint,'fixture-bucket.oss-cn-shanghai.aliyuncs.com'})

    def test_http_sender_disables_redirects_env_proxy_and_bounds_responses(self):
        sender=_BoundedHTTPS()
        self.assertFalse(sender.session.trust_env)
        from unittest.mock import MagicMock
        response=MagicMock();response.status_code=200;response.headers={}
        response.iter_content.return_value=[b'x'*65537]
        response.__enter__.return_value=response
        with patch.object(sender.session,'request',return_value=response) as request:
            with self.assertRaisesRegex(SafetyError,'TOO_LARGE'):
                sender.send('POST','https://green-cip.cn-shanghai.aliyuncs.com/',{},b'',(1,1),'green-cip.cn-shanghai.aliyuncs.com')
            self.assertFalse(request.call_args.kwargs['allow_redirects'])
            self.assertTrue(request.call_args.kwargs['stream'])
        with self.assertRaisesRegex(SafetyError,'TARGET_INVALID'):
            sender.send('POST','http://127.0.0.1/',{},b'',(1,1),'green-cip.cn-shanghai.aliyuncs.com')
