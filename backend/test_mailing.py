import io
import json
from pathlib import Path
import re
import smtplib
import ssl
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit,parse_qs
from fastapi.testclient import TestClient
from backend.app import create_app, Store
from backend.mailing import MailConfig, read_password

ORIGIN='http://127.0.0.1:8002'
EMAIL='recipient@example.com'
PASSWORD='test-account-password'
SMTP_SECRET='smtp-test-secret-only'

class MailTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)
        self.patch=patch('backend.mailing.smtplib.SMTP_SSL');self.factory=self.patch.start()
        self.smtp=self.factory.return_value;self.messages=[]
        self.config=MailConfig('smtp',EMAIL,SMTP_SECRET)
        self.app=create_app(self.path,ORIGIN,mail_config=self.config)
        self.client=TestClient(self.app,base_url=ORIGIN)
        self.refresh_session()
        def accept(message,**kwargs):
            self.assertEqual(kwargs['to_addrs'],[EMAIL])
            # Network send is after commit and without an open SQLite write transaction.
            with self.app.state.store.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                self.assertTrue(db.execute('SELECT 1 FROM auth_tokens').fetchone())
            self.messages.append(message)
            return {}
        self.smtp.send_message.side_effect=accept
    def tearDown(self):
        self.client.close();self.patch.stop();self.temp.cleanup()
    def refresh_session(self):
        me=self.client.get('/api/auth/me').json();self.client.headers.update({'Origin':ORIGIN,'X-CSRF-Token':me['csrf']})
        self.assertEqual(me['mail_mode'],'smtp')
    def post(self,path,body):return self.client.post('/api/auth/'+path,json=body)
    def register(self):return self.post('register',{'email':EMAIL,'password':PASSWORD})
    def token(self):
        url=re.search(r'http://127\.0\.0\.1:8002/#[^\s]+',self.messages[-1].get_content()).group()
        return parse_qs(urlsplit(url).fragment)['token'][0]
    def age_mail(self):
        with self.app.state.store.connect() as db:db.execute('UPDATE mail_deliveries SET created_at=created_at-61')
    def test_smtp_registration_verification_reset_and_single_use(self):
        response=self.register();self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(len(self.messages),1)
        token=self.token()
        self.assertFalse((self.path/'outbox').exists())
        self.assertEqual(self.post('login',{'email':EMAIL,'password':PASSWORD}).status_code,403)
        self.assertEqual(self.post('verify-email',{'token':token}).status_code,200)
        self.assertEqual(self.post('verify-email',{'token':token}).status_code,400)
        login=self.post('login',{'email':EMAIL,'password':PASSWORD});self.assertEqual(login.status_code,200)
        self.client.headers['X-CSRF-Token']=login.json()['csrf']
        self.assertEqual(self.post('forgot-password',{'email':EMAIL}).status_code,200)
        reset=self.token();self.assertNotEqual(reset,token)
        self.assertEqual(self.post('reset-password',{'token':reset,'password':'new-test-password'}).status_code,200)
        self.refresh_session()
        self.assertEqual(self.post('reset-password',{'token':reset,'password':PASSWORD}).status_code,400)
        self.assertEqual(self.post('login',{'email':EMAIL,'password':PASSWORD}).status_code,401)
        self.assertEqual(self.post('login',{'email':EMAIL,'password':'new-test-password'}).status_code,200)
        context=self.factory.call_args.kwargs['context'];self.assertTrue(context.check_hostname);self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED)
        with self.app.state.store.connect() as db:
            rows=db.execute('SELECT * FROM mail_deliveries').fetchall()
            self.assertEqual([row['status'] for row in rows],['accepted','accepted'])
            text=repr([tuple(row) for row in rows]);self.assertNotIn(token,text);self.assertNotIn(reset,text);self.assertNotIn(SMTP_SECRET,text)
    def test_allowlist_blocks_all_three_mail_operations_without_sending(self):
        for route,body in [('register',{'email':'other@example.com','password':PASSWORD}),('resend-verification',{'email':'other@example.com'}),('forgot-password',{'email':'other@example.com'})]:
            self.assertEqual(self.post(route,body).status_code,403)
        self.factory.assert_not_called()
        with self.app.state.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM users').fetchone()[0],0)
    def test_cooldown_resend_invalidates_previous_link_and_survives_restart(self):
        self.register();old=self.token()
        self.assertEqual(self.post('resend-verification',{'email':EMAIL}).status_code,429)
        self.assertEqual(len(self.messages),1)
        restarted=create_app(self.path,ORIGIN,mail_config=self.config)
        with TestClient(restarted,base_url=ORIGIN) as c:
            me=c.get('/api/auth/me').json();c.headers.update({'Origin':ORIGIN,'X-CSRF-Token':me['csrf']})
            self.assertEqual(c.post('/api/auth/resend-verification',json={'email':EMAIL}).status_code,429)
        self.age_mail();self.assertEqual(self.post('resend-verification',{'email':EMAIL}).status_code,200)
        new=self.token();self.assertNotEqual(new,old)
        self.assertEqual(self.post('verify-email',{'token':old}).status_code,400)
        self.assertEqual(self.post('verify-email',{'token':new}).status_code,200)
    def test_failure_keeps_unverified_account_and_can_resend(self):
        self.smtp.login.side_effect=smtplib.SMTPAuthenticationError(535,SMTP_SECRET.encode())
        response=self.register();self.assertEqual(response.status_code,503)
        self.assertNotIn(SMTP_SECRET,response.text);self.smtp.send_message.assert_not_called()
        with self.app.state.store.connect() as db:
            self.assertEqual(db.execute('SELECT verified FROM users').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT status FROM mail_deliveries').fetchone()[0],'failed')
        self.smtp.login.side_effect=None;self.age_mail()
        self.assertEqual(self.post('resend-verification',{'email':EMAIL}).status_code,200)
        self.assertEqual(self.post('verify-email',{'token':self.token()}).status_code,200)
    def test_timeout_does_not_retry_or_invalidate_potentially_delivered_link(self):
        def timeout(message,**kwargs):self.messages.append(message);raise TimeoutError(SMTP_SECRET)
        self.smtp.send_message.side_effect=timeout
        result=self.register();self.assertEqual(result.status_code,503);self.assertIn('不确定',result.json()['detail'])
        self.assertNotIn(SMTP_SECRET,result.text);self.smtp.send_message.assert_called_once()
        with self.app.state.store.connect() as db:self.assertEqual(db.execute('SELECT status FROM mail_deliveries').fetchone()[0],'unknown')
        self.assertEqual(self.post('verify-email',{'token':self.token()}).status_code,200)
        self.assertFalse((self.path/'outbox').exists())
    def test_daily_budget_blocks_reset_without_invalidating_prior_token(self):
        self.register();token=self.token();self.age_mail()
        with self.app.state.store.connect() as db:
            uid=db.execute('SELECT id FROM users').fetchone()[0]
            now=__import__('time').time()
            for i in range(19):
                db.execute('INSERT INTO mail_deliveries VALUES (?,?,?,?,?,?,?,?,?)',(str(i),uid,'reset','smtp','failed','test',int(now)-70,int(now),'connection'))
        self.assertEqual(self.post('forgot-password',{'email':EMAIL}).status_code,429)
        self.assertEqual(len(self.messages),1)
        self.assertEqual(self.post('verify-email',{'token':token}).status_code,200)
    def test_file_mode_stays_offline_and_config_never_reveals_secret(self):
        self.assertNotIn(SMTP_SECRET,repr(self.config))
        with TestClient(create_app(self.path/'file'),base_url='http://127.0.0.1:8000') as c:
            me=c.get('/api/auth/me').json();self.assertEqual(me['mail_mode'],'file')
            c.headers.update({'Origin':'http://127.0.0.1:8000','X-CSRF-Token':me['csrf']})
            self.assertEqual(c.post('/api/auth/register',json={'email':EMAIL,'password':PASSWORD}).status_code,200)
        self.factory.assert_not_called();self.assertEqual(len(list((self.path/'file'/'outbox').glob('*.json'))),1)
        with patch('backend.mailing.sys.stdin.isatty',return_value=False):
            with self.assertRaises(ValueError):read_password()
    def test_v3_migration_preserves_existing_accounts(self):
        self.register()
        with self.app.state.store.connect() as db:
            before=[tuple(r) for r in db.execute('SELECT * FROM users')]
            db.execute('DROP TABLE mail_deliveries');db.execute('DELETE FROM schema_version WHERE version>=4')
        restored=Store(self.path)
        with restored.connect() as db:
            self.assertEqual(before,[tuple(r) for r in db.execute('SELECT * FROM users')])
            self.assertEqual(db.execute('SELECT max(version) FROM schema_version').fetchone()[0],6)

if __name__=='__main__':unittest.main()
