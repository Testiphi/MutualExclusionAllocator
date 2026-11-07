"""baselineCheck workflow. Live transport requires a separate explicit capability."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import secrets
import time

KIND = 'racepick-aliyun-baseline-preparation-v1'
REGIONS = {'cn-shanghai', 'cn-hangzhou', 'cn-beijing', 'cn-shenzhen', 'cn-chengdu'}


class SafetyError(Exception):
    """Public errors never include provider messages, credentials or image text."""
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class BaselineConfig:
    mode: str
    region: str
    credentials_file: str
    connect_timeout_seconds: int
    read_timeout_seconds: int
    total_timeout_seconds: int
    service: str = 'baselineCheck'

    @property
    def endpoint(self):
        return 'green-cip.' + self.region + '.aliyuncs.com'


def parse_config(value):
    fields = {'kind', 'mode', 'region', 'service', 'credentials_file',
              'connect_timeout_seconds', 'read_timeout_seconds',
              'total_timeout_seconds', 'automatic_retries', 'allow_risk_levels'}
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError('Invalid baseline configuration fields')
    if any(not isinstance(value[name], str) for name in ('kind', 'mode', 'region', 'service')):
        raise ValueError('Invalid baseline configuration values')
    if (value['kind'] != KIND or value['mode'] not in ('disabled', 'simulation', 'live')
            or value['region'] not in REGIONS or value['service'] != 'baselineCheck'
            or type(value['automatic_retries']) is not int or value['automatic_retries'] != 0
            or value['allow_risk_levels'] != ['none']):
        raise ValueError('Only baselineCheck with no retries is supported')
    for name, maximum in [('connect_timeout_seconds', 10), ('read_timeout_seconds', 30),
                          ('total_timeout_seconds', 60)]:
        if type(value[name]) is not int or not 1 <= value[name] <= maximum:
            raise ValueError('Invalid timeout configuration')
    if value['total_timeout_seconds'] < value['read_timeout_seconds']:
        raise ValueError('Total timeout must cover read timeout')
    credential_path = value['credentials_file']
    if (not isinstance(credential_path, str) or not credential_path.startswith('/')
            or '\\' in credential_path or '..' in credential_path.split('/')
            or '?' in credential_path or '#' in credential_path):
        raise ValueError('Use a private absolute server credentials path')
    return BaselineConfig(**{name: value[name] for name in (
        'mode', 'region', 'credentials_file', 'connect_timeout_seconds',
        'read_timeout_seconds', 'total_timeout_seconds', 'service')})


def load_config(path):
    # Configuration validation must not open a credentials file or initialize state.
    return parse_config(json.loads(Path(path).read_text(encoding='utf-8')))


def _body(response):
    if (not isinstance(response, dict) or type(response.get('statusCode')) is not int
            or response['statusCode'] != 200 or not isinstance(response.get('body'), dict)):
        raise SafetyError('IMAGE_SAFETY_UNAVAILABLE')
    body = response['body']
    if type(body.get('Code')) is not int or body['Code'] != 200:
        raise SafetyError('IMAGE_SAFETY_UNAVAILABLE')
    return body


class AliyunBaselineAdapter:
    """Transport port mirrors official token -> temporary OSS -> sync API steps.

    The optional SDK process reviewer normalizes response maps and constrains I/O.
    This workflow never discovers or enables a transport implicitly.
    """
    def __init__(self, config, transport=None, *, clock=time.monotonic, allow_live_calls=False):
        if not isinstance(config, BaselineConfig):
            raise ValueError('Expected a parsed baseline configuration')
        self.config, self.transport, self.clock = config, transport, clock
        self.allow_live_calls = allow_live_calls is True

    def review(self, raw, mime):
        if self.config.mode == 'disabled' or (self.config.mode == 'live' and not self.allow_live_calls):
            raise SafetyError('RECOGNITION_DISABLED')
        expected = self.config.mode == 'simulation'
        if type(getattr(self.transport, 'is_simulated', None)) is not bool or self.transport.is_simulated != expected:
            raise SafetyError('IMAGE_SAFETY_TRANSPORT_DISABLED')
        from backend.map_recognition import validate_image, RecognitionError
        try:
            validate_image(raw, mime)
        except RecognitionError:
            raise SafetyError('IMAGE_INVALID') from None
        started = self.clock()

        def remaining():
            seconds = self.config.total_timeout_seconds - (self.clock() - started)
            if seconds <= 0:
                raise SafetyError('IMAGE_SAFETY_TIMEOUT')
            return min(seconds, self.config.read_timeout_seconds)

        try:
            token = _body(self.transport.describe_upload_token(
                endpoint=self.config.endpoint, timeout=remaining(),
                connect_timeout=self.config.connect_timeout_seconds, retries=0)).get('Data')
            if not isinstance(token, dict):
                raise SafetyError('IMAGE_SAFETY_UNAVAILABLE')
            fields = ('AccessKeyId', 'AccessKeySecret', 'SecurityToken', 'BucketName',
                      'FileNamePrefix', 'OssInternetEndPoint', 'Expiration')
            if any(not isinstance(token.get(n), str) or not token[n] for n in fields[:-1]):
                raise SafetyError('IMAGE_SAFETY_UNAVAILABLE')
            if type(token.get('Expiration')) is not int or token['Expiration'] <= time.time() + 60:
                raise SafetyError('IMAGE_SAFETY_UNAVAILABLE')
            host = token['OssInternetEndPoint']
            # Do not permit a token response to redirect future network code to arbitrary hosts.
            host = host.removeprefix('https://')
            if (not re.fullmatch(r'oss-cn-[a-z0-9-]+\.aliyuncs\.com', host)
                    or not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,61}[a-z0-9]', token['BucketName'])
                    or not re.fullmatch(r'[A-Za-z0-9_/-]{1,256}', token['FileNamePrefix'])
                    or '..' in token['FileNamePrefix'] or not token['FileNamePrefix'].endswith('/')):
                raise SafetyError('IMAGE_SAFETY_UNAVAILABLE')
            # Names contain neither owner/key nor image filename or OCR text.
            object_name = token['FileNamePrefix'] + secrets.token_hex(16)
            upload = self.transport.upload_image(
                endpoint='https://' + host, token=token, object_name=object_name,
                image=raw, mime=mime, timeout=remaining(),
                connect_timeout=self.config.connect_timeout_seconds, retries=0)
            if not isinstance(upload, dict) or type(upload.get('status')) is not int or upload['status'] != 200:
                raise SafetyError('IMAGE_SAFETY_UNAVAILABLE')
            data_id = secrets.token_hex(16)
            response = self.transport.image_moderation(
                endpoint=self.config.endpoint, service='baselineCheck',
                service_parameters=json.dumps({'ossBucketName': token['BucketName'],
                    'ossObjectName': object_name, 'dataId': data_id}, separators=(',', ':')),
                timeout=remaining(), connect_timeout=self.config.connect_timeout_seconds, retries=0)
            remaining()  # Reject a response arriving after the total deadline.
            data = _body(response).get('Data')
            if (not isinstance(data, dict) or data.get('DataId') != data_id
                    or data.get('RiskLevel') not in ('none', 'low', 'medium', 'high')):
                raise SafetyError('IMAGE_SAFETY_UNAVAILABLE')
            # Conservative initial policy: only an explicit none is accepted.
            if data['RiskLevel'] != 'none' or data.get('ManualTaskId'):
                raise SafetyError('IMAGE_SAFETY_REJECTED')
            results = data.get('Result')
            if (not isinstance(results, list) or len(results) != 1
                    or not isinstance(results[0], dict) or results[0].get('Label') != 'nonLabel'
                    or data.get('FrameNum') not in (None, 1)):
                # Official normal marker only; custom exempt libraries are not approval.
                raise SafetyError('IMAGE_SAFETY_UNAVAILABLE')
            return {'approved': True, 'provider': 'aliyun', 'service': 'baselineCheck',
                    'policy_version': 'baseline-none-v1',
                    'image_sha256': hashlib.sha256(raw).hexdigest()}
        except SafetyError:
            raise
        except TimeoutError:
            raise SafetyError('IMAGE_SAFETY_TIMEOUT') from None
        except Exception:
            # A lost response is not evidence that the supplier did not charge.
            raise SafetyError('IMAGE_SAFETY_UNAVAILABLE') from None
