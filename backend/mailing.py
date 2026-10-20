"""Local file delivery or explicitly enabled Aliyun SMTP test transport."""
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
import getpass
import hashlib
import json
import re
import secrets
import smtplib
import ssl
import sys
import time
import warnings

SMTP_HOST = 'smtpdm.aliyun.com'
SMTP_PORT = 465
SMTP_SENDER = 'no-reply@notify.racepick.cn'


@dataclass(frozen=True)
class MailConfig:
    mode: str = 'file'
    allowed_recipient: str = ''
    password: str = field(default='', repr=False)
    production: bool = False
    daily_limit: int = 20

    def __post_init__(self):
        if self.mode not in ('file', 'smtp'):
            raise ValueError('邮件模式仅允许file或smtp')
        if not 1 <= self.daily_limit <= 10000:raise ValueError('发信限额无效')
        if self.production and self.mode!='smtp':raise ValueError('生产环境必须使用SMTP')
        if self.mode == 'smtp':
            if not self.production and not re.fullmatch(r'[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', self.allowed_recipient):
                raise ValueError('SMTP测试需要明确指定一个允许收信的邮箱')
            if not self.password:
                raise ValueError('SMTP密码为空，拒绝启动真实邮件模式')


class MailFailure(Exception):
    def __init__(self, code, message, uncertain=False):
        super().__init__(message)
        self.code, self.uncertain = code, uncertain


def read_password():
    if not sys.stdin.isatty():
        raise ValueError('请在交互式PowerShell终端启动SMTP模式，不接受管道密码')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            password = getpass.getpass('SMTP专用密码（隐藏输入，不保存）：')
    except (getpass.GetPassWarning, EOFError):
        raise ValueError('无法安全隐藏密码输入，已停止') from None
    if not password:
        raise ValueError('SMTP密码为空，已停止')
    return password


def migrate_mail(db):
    version = db.execute('SELECT max(version) FROM schema_version').fetchone()[0]
    if version in (4,5,6):
        return
    if version != 3:
        raise RuntimeError('邮件迁移需要数据库v3')
    db.execute('''CREATE TABLE IF NOT EXISTS mail_deliveries(
        id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), purpose TEXT NOT NULL,
        mode TEXT NOT NULL, status TEXT NOT NULL, message_id TEXT NOT NULL,
        created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, error_code TEXT)''')
    db.execute('CREATE INDEX IF NOT EXISTS mail_delivery_time ON mail_deliveries(mode,created_at)')
    db.execute('INSERT INTO schema_version VALUES (4)')


def build_message(payload, production=False):
    purpose = payload['purpose']
    if purpose not in ('verify', 'reset'):
        raise ValueError('不支持的邮件类型')
    title = '验证邮箱' if purpose == 'verify' else '重置密码'
    msg = EmailMessage()
    msg['From'] = f'擂台选车助手 <{SMTP_SENDER}>'
    msg['To'] = payload['to']
    msg['Subject'] = '擂台选车助手｜'+title+('' if production else '（本地测试）')
    msg['Date'] = format_datetime(datetime.now(timezone.utc))
    msg['Message-ID'] = payload['message_id']
    instruction='请用浏览器打开以下链接：' if production else '请在运行本地服务的同一台电脑上，用浏览器打开以下链接：'
    local_note='' if production else '本地链接不能在手机或其他电脑上完成验证。此服务仍未上线。\n'
    msg.set_content(f'你请求了擂台选车助手的{title}操作。\n\n{instruction}\n{payload["url"]}\n\n'
                    '打开后还需要在页面点击确认；链接30分钟有效且只能使用一次。重新申请同类邮件会使旧链接失效。\n'
                    +local_note+'如果不是你发起的请求，请忽略本邮件；不要向任何人提供密码或此链接。\n')
    return msg


def send_smtp(config, payload):
    if not config.production and payload['to'].strip().lower() != config.allowed_recipient.strip().lower():
        raise MailFailure('recipient_blocked', '真实邮件测试仅允许启动时指定的收件人')
    smtp = None
    sending = False
    try:
        msg = build_message(payload,config.production)
        smtp = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15, context=ssl.create_default_context())
        smtp.set_debuglevel(0)
        smtp.login(SMTP_SENDER, config.password)
        sending = True
        if smtp.send_message(msg, from_addr=SMTP_SENDER, to_addrs=[payload['to']]):
            raise MailFailure('recipient_refused', '收件人被SMTP拒绝，请核对发信日志')
    except MailFailure:
        raise
    except smtplib.SMTPAuthenticationError:
        raise MailFailure('authentication', 'SMTP认证失败；账号请求已保留，请核对SMTP专用密码，重启服务后再尝试重发') from None
    except (smtplib.SMTPSenderRefused, smtplib.SMTPRecipientsRefused, smtplib.SMTPDataError):
        raise MailFailure('smtp_refused', 'SMTP拒绝发送，请查看阿里云发信日志；未自动重试') from None
    except ssl.SSLCertVerificationError:
        raise MailFailure('tls_certificate', 'SMTP证书校验失败，已停止发送；不能关闭证书校验') from None
    except Exception:
        message = ('邮件发送结果不确定，链接仍可使用。请先检查收件箱、垃圾邮件和阿里云发信日志，不要立即重复申请。'
                   if sending else 'SMTP连接失败，邮件未提交。请检查网络及发信配置后重试。')
        raise MailFailure('delivery_unknown' if sending else 'connection', message, sending) from None
    finally:
        if smtp is not None:
            with suppress(Exception):
                smtp.close()


class MailService:
    def __init__(self, store, origin, config):
        self.store, self.origin, self.config = store, origin, config

    def check_recipient(self, email):
        if self.config.mode == 'smtp' and not self.config.production and email.strip().lower() != self.config.allowed_recipient.strip().lower():
            from fastapi import HTTPException
            raise HTTPException(403, '当前为受限真实邮件测试，仅允许启动时指定的收件邮箱')

    def prepare(self, db, uid, email, purpose):
        """Prepare and log within caller transaction; never perform network I/O here."""
        from fastapi import HTTPException
        self.check_recipient(email)
        now = int(time.time())
        if self.config.mode == 'smtp':
            if db.execute("SELECT 1 FROM mail_deliveries WHERE user_id=? AND purpose=? AND mode='smtp' AND created_at>?",(uid,purpose,now-60)).fetchone():
                raise HTTPException(429, '同类邮件请等待60秒后再申请，先检查邮箱及垃圾邮件')
            if db.execute("SELECT count(*) FROM mail_deliveries WHERE mode='smtp' AND created_at>?",(now-86400,)).fetchone()[0] >= self.config.daily_limit:
                raise HTTPException(429, '24小时发信总额度已用完，请稍后再试')
        if self.config.production and db.execute('SELECT count(*) FROM mail_deliveries WHERE user_id=? AND created_at>?',(uid,now-86400)).fetchone()[0]>=6:
            raise HTTPException(429,'此账号24小时内发信次数已达上限')
        raw = secrets.token_urlsafe(32)
        db.execute('DELETE FROM auth_tokens WHERE user_id=? AND purpose=?',(uid,purpose))
        db.execute('INSERT INTO auth_tokens VALUES (?,?,?,?)',(hashlib.sha256(raw.encode()).hexdigest(),uid,purpose,now+1800))
        delivery_id = secrets.token_hex(16)
        payload = {'id':delivery_id,'to':email,'purpose':purpose,
                   'url':f'{self.origin}/#action={purpose}&token={raw}', 'expires_in_seconds':1800,
                   'message_id':make_msgid(domain='notify.racepick.cn')}
        db.execute('INSERT INTO mail_deliveries VALUES (?,?,?,?,?,?,?,?,NULL)',
                   (delivery_id,uid,purpose,self.config.mode,'prepared',payload['message_id'],now,now))
        return payload

    def deliver(self, payload):
        """Token is already committed. No implicit retry and no SMTP-to-file fallback."""
        if payload is None:
            return
        failure = None
        try:
            if self.config.mode == 'file':
                directory = self.store.directory/'outbox'
                directory.mkdir(exist_ok=True)
                (directory/f'{time.time_ns()}-{payload["id"]}.json').write_text(
                    json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
                status = 'file'
            else:
                send_smtp(self.config,payload)
                status = 'accepted'
        except MailFailure as error:
            failure = error
            status = 'unknown' if error.uncertain else 'failed'
        except OSError:
            failure = MailFailure('file_write', '本地测试邮件写入失败，请检查目录权限后重发')
            status = 'failed'
        from fastapi import HTTPException
        try:
            with self.store.connect() as db:
                db.execute('UPDATE mail_deliveries SET status=?,updated_at=?,error_code=? WHERE id=?',
                           (status,int(time.time()),failure.code if failure else None,payload['id']))
        except Exception:
            raise HTTPException(503,'发信结果记录失败；请先查邮箱和发信日志，勿立即重复申请') from None
        if failure:
            raise HTTPException(503,str(failure)) from None

    def notice(self, action):
        if self.config.mode == 'file':
            return {'register':'如可注册，验证邮件已写入本地测试收件箱；已有账号请登录或重发验证邮件。',
                    'resend':'如果账号尚未验证，新验证邮件已写入本地测试收件箱。',
                    'reset':'如果账号存在，重置邮件已写入本地测试收件箱。'}[action]
        return {'register':'请求已处理。如邮箱可注册，验证邮件已提交阿里云，请检查收件箱及垃圾邮件；已有账号请登录或重发验证邮件。',
                'resend':'请求已处理。如果账号尚未验证，验证邮件已提交阿里云；请检查收件箱及垃圾邮件。',
                'reset':'请求已处理。如果账号存在，重置邮件已提交阿里云；请检查收件箱及垃圾邮件。'}[action]
