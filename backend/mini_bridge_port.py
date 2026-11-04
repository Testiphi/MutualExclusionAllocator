"""Guest-side queue port: socket only; never mounts/opens the queue or business DB."""
import json

from backend.mini_auth import MiniError
from backend.image_safety_aliyun import SafetyError


class BridgeRecognitionPort:
    production=True
    is_bridge=True

    def __init__(self,client,catalog):
        self.client=client
        self.fixed_catalog=json.loads(json.dumps(catalog))
        self.ready=False

    def call(self,op,owner=None,**fields):
        message={'op':op,'owner':owner or 'mini-v1:'+'0'*64,'server':'cn',
                 'catalog_version':self.fixed_catalog['version'],**fields}
        try:return self.client.request(message)
        except SafetyError as error:self.error(error)
        except (OSError,ValueError,KeyError,TypeError):
            raise MiniError(503,'OCR_UNAVAILABLE','识图队列连接暂不可用，请按原编号恢复',5) from None

    @staticmethod
    def error(error):
        statuses={'RECOGNITION_DISABLED':503,'OCR_UNAVAILABLE':503,'OCR_LIMITED':429,
            'CATALOG_CHANGED':409,'REQUEST_KEY_CONFLICT':409,'JOB_EXPIRED':410,
            'JOB_NOT_FOUND':404,'JOB_FORBIDDEN':403,'RECOGNITION_SERVER_DISABLED':403,
            'INVALID_QUERY':400,'TRUSTED_PROXY_REQUIRED':400}
        status=statuses.get(error.code,503)
        code=error.code if error.code in statuses else 'OCR_UNAVAILABLE'
        raise MiniError(status,code,'识图服务暂不可用或请求绑定无效，请保留草稿并按原编号恢复',5 if status in (429,503) else None) from None

    def catalog(self,server):
        if server!='cn':raise MiniError(403,'RECOGNITION_SERVER_DISABLED','国际服识图尚未开放')
        result=self.call('catalog')
        if result!=self.fixed_catalog:raise MiniError(409,'CATALOG_CHANGED','识图目录与固定快照不同')
        self.ready=True
        return result

    def health(self):return 'ready' if self.ready else 'unavailable'

    def preflight(self,owner,key,ip):return self.call('preflight',owner,key=key,ip=ip)
    def recover(self,owner,key):return self.call('recover',owner,key=key)
    def get(self,owner,job):return self.call('get',owner,id=job)
    def cancel(self,owner,job):return self.call('cancel',owner,id=job)
    def submit(self,owner,key,ip,image,mime):
        # Keep binary image out of the JSON header.
        message={'op':'create','owner':owner,'server':'cn','catalog_version':self.fixed_catalog['version'],
                 'key':key,'ip':ip,'mime':mime}
        try:return self.client.request(message,image)
        except SafetyError as error:self.error(error)
        except (OSError,ValueError,KeyError,TypeError):
            raise MiniError(503,'OCR_UNAVAILABLE','上传响应不确定，请按原编号恢复',5) from None
