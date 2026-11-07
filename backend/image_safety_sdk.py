"""Real official SDK transport, restricted to a dedicated, deadline-bounded child.

Importing this module does not load credentials/SDKs, launch a process or connect.
"""
import io
import json
import logging
import multiprocessing
import os
from pathlib import Path
import stat
import time
from urllib.parse import urlsplit

from backend.image_safety_aliyun import AliyunBaselineAdapter, SafetyError

MAX_RESPONSE = 65536


def read_credentials(path):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path or path.is_symlink():
        raise SafetyError('IMAGE_SAFETY_CREDENTIALS_INVALID')
    with path.open('rb') as stream:
        meta = os.fstat(stream.fileno())
        if not stat.S_ISREG(meta.st_mode) or meta.st_nlink != 1 or meta.st_size > 4096:
            raise SafetyError('IMAGE_SAFETY_CREDENTIALS_INVALID')
        if os.name == 'posix' and (meta.st_uid != os.geteuid() or stat.S_IMODE(meta.st_mode) & 0o077):
            raise SafetyError('IMAGE_SAFETY_CREDENTIALS_INVALID')
        value = json.loads(stream.read(4097))
    if (not isinstance(value, dict) or set(value) != {'access_key_id', 'access_key_secret'}
            or any(not isinstance(v, str) or not 1 <= len(v) <= 256
                   or any(ord(c) <= 32 for c in v) for v in value.values())):
        raise SafetyError('IMAGE_SAFETY_CREDENTIALS_INVALID')
    return value


class _BoundedHTTPS:
    def __init__(self):
        import requests
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.mount('https://', requests.adapters.HTTPAdapter(max_retries=0))

    def send(self, method, url, headers, data, timeout, expected_host):
        parts = urlsplit(url)
        if (parts.scheme != 'https' or parts.hostname != expected_host or parts.port not in (None, 443)
                or parts.username or parts.password or parts.fragment):
            raise SafetyError('IMAGE_SAFETY_TARGET_INVALID')
        # Suppress credential/body debug logs in this dedicated child only.
        with self.session.request(method, url, headers=headers, data=data,
                timeout=timeout, allow_redirects=False, stream=True) as response:
            body = bytearray()
            for chunk in response.iter_content(8192):
                body.extend(chunk)
                if len(body) > MAX_RESPONSE:
                    raise SafetyError('IMAGE_SAFETY_RESPONSE_TOO_LARGE')
            return response.status_code, dict(response.headers), bytes(body)


class _SdkTransport:
    is_simulated = False

    def __init__(self, config, credentials, *, sender=None):
        from alibabacloud_green20220302.client import Client
        from alibabacloud_tea_openapi.models import Config
        from darabonba.core import DaraCore
        from darabonba.response import DaraResponse
        self.config = config
        self.sender = sender or _BoundedHTTPS()
        self.client = Client(Config(access_key_id=credentials['access_key_id'],
            access_key_secret=credentials['access_key_secret'], endpoint=config.endpoint,
            region_id=config.region, protocol='https'))

        def sdk_http(request, runtime=None):
            runtime = runtime or {}
            url = DaraCore.compose_url(request)
            code, headers, body = self.sender.send(request.method, url, request.headers,
                request.body, (runtime['connectTimeout']/1000, runtime['readTimeout']/1000),
                self.config.endpoint)
            response = DaraResponse()
            response.status_code, response.status_message = code, ''
            response.headers = {k.lower(): v for k, v in headers.items()}
            response.body = body
            return response
        # This hook is process-local. Never construct this private class in a shared server.
        self.original_action = DaraCore.do_action
        DaraCore.do_action = staticmethod(sdk_http)

    def close(self):
        from darabonba.core import DaraCore
        DaraCore.do_action = self.original_action

    @staticmethod
    def runtime(timeout, connect_timeout):
        from darabonba.runtime import RuntimeOptions
        return RuntimeOptions(autoretry=False, max_attempts=1,
            connect_timeout=int(min(connect_timeout, timeout)*1000),
            read_timeout=int(timeout*1000), ignore_ssl=False)

    def describe_upload_token(self, *, endpoint, timeout, connect_timeout, retries):
        if endpoint != self.config.endpoint or retries != 0:
            raise SafetyError('IMAGE_SAFETY_TARGET_INVALID')
        return self.client.describe_upload_token_with_options(self.runtime(timeout, connect_timeout)).to_map()

    def image_moderation(self, *, endpoint, service, service_parameters, timeout, connect_timeout, retries):
        from alibabacloud_green20220302.models import ImageModerationRequest
        if endpoint != self.config.endpoint or service != 'baselineCheck' or retries != 0:
            raise SafetyError('IMAGE_SAFETY_TARGET_INVALID')
        request = ImageModerationRequest(service=service, service_parameters=service_parameters)
        return self.client.image_moderation_with_options(request, self.runtime(timeout, connect_timeout)).to_map()

    def upload_image(self, *, endpoint, token, object_name, image, mime, timeout, connect_timeout, retries):
        import oss2
        from oss2.http import Response
        if retries != 0:
            raise SafetyError('IMAGE_SAFETY_TARGET_INVALID')
        sender = self.sender
        expected = token['BucketName'] + '.' + urlsplit(endpoint).hostname
        class Session:
            def do_request(self, request, timeout):
                code, headers, raw = sender.send(request.method, request.url, request.headers,
                    request.data, (connect_timeout, timeout), expected)
                # OSS SDK expects a requests-like streaming response.
                class Reply:
                    status_code = code
                    def iter_content(self, size):
                        return iter([raw] if raw else [])
                reply = Reply(); reply.headers = headers
                return Response(reply)
        auth = oss2.StsAuth(token['AccessKeyId'], token['AccessKeySecret'], token['SecurityToken'])
        bucket = oss2.Bucket(auth, endpoint, token['BucketName'], session=Session(),
                             connect_timeout=timeout, enable_crc=True)
        result = bucket.put_object(object_name, image, headers={'Content-Type': mime})
        return {'status': result.status}


def _child_review(connection, config, image, mime):
    logging.disable(logging.CRITICAL)
    try:
        if os.name=='posix':
            import resource
            resource.setrlimit(resource.RLIMIT_CORE,(0,0))
            resource.setrlimit(resource.RLIMIT_NOFILE,(64,64))
            resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
        credentials = read_credentials(config.credentials_file)
        transport = _SdkTransport(config, credentials)
        try:
            result = AliyunBaselineAdapter(config, transport, allow_live_calls=True).review(image, mime)
        finally:
            transport.close()
        connection.send({'ok': result})
    except BaseException as error:
        connection.send({'error': error.code if isinstance(error, SafetyError) else 'IMAGE_SAFETY_UNAVAILABLE'})
    finally:
        connection.close()


class SdkProcessReviewer:
    """No process/credentials/network until explicit live gate and review invocation."""
    def __init__(self, config, *, allow_live_calls=False, child_target=None):
        self.config, self.allowed = config, allow_live_calls is True
        self.child_target = child_target or _child_review

    def review(self, image, mime):
        if not self.allowed or self.config.mode != 'live':
            raise SafetyError('RECOGNITION_DISABLED')
        from backend.map_recognition import validate_image
        validate_image(image, mime)
        context = multiprocessing.get_context('spawn')
        parent, child = context.Pipe(duplex=False)
        process = context.Process(target=self.child_target, args=(child, self.config, image, mime),
                                  name='racepick-safety-sdk', daemon=True)
        started = time.monotonic()
        try:
            process.start(); child.close()
            remaining = self.config.total_timeout_seconds - (time.monotonic()-started)
            if remaining <= 0 or not parent.poll(remaining):
                raise SafetyError('IMAGE_SAFETY_TIMEOUT')
            message = parent.recv()
            if 'ok' not in message:
                raise SafetyError(message.get('error', 'IMAGE_SAFETY_UNAVAILABLE'))
            return message['ok']
        except (EOFError, OSError):
            raise SafetyError('IMAGE_SAFETY_UNAVAILABLE') from None
        finally:
            if process.pid:
                if process.is_alive():process.terminate()
                process.join(2)
                if process.is_alive():process.kill();process.join(2)
                process.close()
            parent.close();child.close()
