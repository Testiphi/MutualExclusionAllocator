"""One-message Aliyun DirectMail smoke test. Preview by default; no stored credentials."""
import argparse
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
import getpass
import re
import smtplib
import ssl
import sys
import warnings

HOST = 'smtpdm.aliyun.com'
PORT = 465
SENDER = 'no-reply@notify.racepick.cn'


def single_address(value):
    if not re.fullmatch(r'[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,}', value):
        raise argparse.ArgumentTypeError('请填写一个完整邮箱地址，不支持列表或显示名称')
    return value


def build_message(recipient):
    now = datetime.now(timezone(timedelta(hours=8)))
    msg = EmailMessage()
    msg['From'] = f'擂台选车助手 <{SENDER}>'
    msg['To'] = recipient
    msg['Subject'] = '擂台选车助手｜邮件投递测试'
    msg['Date'] = format_datetime(now)
    msg['Message-ID'] = make_msgid(domain='notify.racepick.cn')
    msg.set_content(
        '这是一封由你主动发起的邮件投递测试。\n\n'
        f'发信地址：{SENDER}\n'
        f'发起时间：{now:%Y-%m-%d %H:%M:%S}（北京时间）\n'
        f'测试标识：{msg["Message-ID"]}\n\n'
        '本邮件仅验证阿里云邮件推送到收件邮箱的投递，不是注册验证邮件，'
        '不包含验证码或登录链接，也不会改变账号状态。账号功能仍未上线。\n'
        '请记录邮件出现在收件箱还是垃圾邮件文件夹，以及大致到达时间。\n'
    )
    return msg


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--to', required=True, type=single_address, help='唯一测试收件人')
    parser.add_argument('--send', action='store_true', help='实际发送一封；不指定则仅预览且不联网')
    args = parser.parse_args(argv)
    msg = build_message(args.to)
    print(f'SMTP：{HOST}:{PORT}（TLS，验证服务器证书）')
    print(f'发件人：{SENDER}\n收件人：{args.to}\n主题：{msg["Subject"]}')
    print(f'测试标识：{msg["Message-ID"]}')
    if not args.send:
        print('\n'+msg.get_content())
        print('预览结束：未连接SMTP、未读取密码、未发送邮件。实际发送需加 --send。')
        return 0
    if not sys.stdin.isatty():
        print('请在交互式Windows Terminal/PowerShell中直接运行，禁止用管道传入密码。', file=sys.stderr)
        return 1
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            password = getpass.getpass('请输入该发信地址的SMTP密码（不显示字符），回车发送一封：')
    except (getpass.GetPassWarning, EOFError, KeyboardInterrupt):
        print('\n已取消；无法安全读取密码，未发送。', file=sys.stderr)
        return 1
    if not password:
        print('密码为空，未发送。', file=sys.stderr)
        return 1
    smtp = None
    sending = False
    try:
        smtp = smtplib.SMTP_SSL(HOST, PORT, timeout=30, context=ssl.create_default_context())
        smtp.set_debuglevel(0)
        smtp.login(SENDER, password)
        password = None
        sending = True
        refused = smtp.send_message(msg, from_addr=SENDER, to_addrs=[args.to])
        if refused:
            print('SMTP拒绝了收件人；请检查发信日志。脚本不会自动重试。', file=sys.stderr)
            return 2
        print('阿里云SMTP已接受这一封邮件；这不等于已进入163收件箱。')
        print('请检查163收件箱和垃圾邮件，并在阿里云发信日志核对投递结果。')
        return 0
    except smtplib.SMTPAuthenticationError as error:
        print(f'SMTP认证失败（代码{error.smtp_code}）。请核对发信地址、SMTP专用密码和地域；不要提供密码。', file=sys.stderr)
        return 1
    except (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused, smtplib.SMTPDataError) as error:
        print(f'SMTP拒绝发送（{type(error).__name__}，代码{getattr(error,"smtp_code","见控制台")}），请核对阿里云发信日志；未自动重试。', file=sys.stderr)
        return 2
    except ssl.SSLCertVerificationError:
        print('TLS证书校验失败，已停止；不允许关闭证书校验。', file=sys.stderr)
        return 1
    except Exception as error:
        if sending:
            print(f'发送阶段连接异常（{type(error).__name__}），结果不确定。先检查163邮箱和阿里云发信日志，不要立即重复发送。', file=sys.stderr)
        else:
            print(f'连接或认证阶段失败（{type(error).__name__}），邮件尚未提交。请检查网络、地域和SMTP配置。', file=sys.stderr)
        return 3 if sending else 1
    finally:
        password = None
        if smtp is not None:
            with suppress(Exception): smtp.close()


if __name__ == '__main__':
    raise SystemExit(main())
