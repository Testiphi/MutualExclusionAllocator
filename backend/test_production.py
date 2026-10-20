"""Production HTTPS/SMTP/owner boundaries tested entirely with temporary databases."""
import json
import tempfile
import unittest
import re
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit,parse_qs
from fastapi.testclient import TestClient
from backend.production import initialize,make_app,bootstrap,require_database,settings
from backend.mailing import MailConfig
from backend.app import create_app

class ProductionTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'state'
  self.config={'origin':'https://racepick.cn','data_dir':str(self.path),'owner_email':'owner@example.com','mail_daily_limit':100}
  initialize(self.config);self.messages=[]
  self.patch=patch('backend.mailing.smtplib.SMTP_SSL');factory=self.patch.start();self.smtp=factory.return_value
  self.smtp.send_message.side_effect=lambda message,**kw:self.messages.append(message) or {}
  self.app=make_app(self.config,'mock-smtp-password');self.client=TestClient(self.app,base_url=self.config['origin'],client=('127.0.0.1',50000))
  self.client.headers.update({'X-Forwarded-Proto':'https','X-Real-IP':'192.0.2.10','Origin':self.config['origin']})
  self.client.headers['X-CSRF-Token']=self.client.get('/api/auth/me').json()['csrf']
 def tearDown(self):self.client.close();self.patch.stop();self.temp.cleanup()
 def post(self,path,body):return self.client.post('/api/auth/'+path,json=body)
 def token(self):return parse_qs(urlsplit(re.search(r'https://racepick.cn/#[^\s]+',self.messages[-1].get_content()).group()).fragment)['token'][0]
 def test_public_smtp_register_reset_and_owner_bootstrap(self):
  password='Production-test-12345'
  r=self.post('register',{'email':self.config['owner_email'],'password':password});self.assertEqual(r.status_code,200,r.text)
  self.assertNotIn('本地测试',str(self.messages[-1]));self.assertFalse((self.path/'outbox').exists())
  with self.assertRaises(ValueError):bootstrap(self.config)
  self.assertEqual(self.post('verify-email',{'token':self.token()}).status_code,200);bootstrap(self.config)
  r=self.post('login',{'email':self.config['owner_email'],'password':password});self.assertEqual(r.json()['user']['role'],'superadmin')
  cookies=r.headers['set-cookie'];self.assertIn('__Host-racepick_session',cookies);self.assertIn('Secure',cookies);self.assertIn('HttpOnly',cookies)
  csrf=r.json()['csrf'];self.client.headers.update({'X-CSRF-Token':csrf,'X-Account-ID':r.json()['user']['id']})
  self.assertEqual(self.client.get('/api/admin/invitations').status_code,200)
  old=self.client.cookies.get('__Host-racepick_session')
  self.assertEqual(self.post('forgot-password',{'email':self.config['owner_email']}).status_code,200)
  self.assertEqual(self.post('reset-password',{'token':self.token(),'password':'Production-new-12345'}).status_code,200)
  self.assertEqual(self.client.get('/api/me/profile').status_code,401)
  self.client.cookies.clear();self.client.headers['X-CSRF-Token']=self.client.get('/api/auth/me').json()['csrf']
  self.assertEqual(self.post('login',{'email':self.config['owner_email'],'password':password}).status_code,401)
  self.assertEqual(self.post('login',{'email':self.config['owner_email'],'password':'Production-new-12345'}).status_code,200)
  self.assertTrue(list((self.path/'backups').glob('*.sqlite3')))
 def test_no_local_writeback_preview_or_private_files(self):
  for path in ('/writeback-lab','/data-previews','/api/admin/previews','/api/admin/writeback','/backend/production.py','/production.json','/.local-accounts/accounts.sqlite3','/data_previews.js'):
   self.assertEqual(self.client.get(path).status_code,404,path)
  me=self.client.get('/api/auth/me').json();self.assertFalse(me['readonly_previews']);self.assertFalse(me['writeback_lab']);self.assertEqual(me['mail_mode'],'production')
  self.assertNotIn('本地开发版',self.client.get('/submissions').text)
  self.assertNotIn('本地开发版',self.client.get('/admin-access').text)
 def test_proxy_host_csrf_and_recipient_validation(self):
  self.assertEqual(self.client.get('/api/health').status_code,200)
  self.assertEqual(self.client.head('/').status_code,200)
  for headers in ({'Host':'evil.example'},{'X-Forwarded-Proto':'http'},{'X-Real-IP':'bad'}):self.assertEqual(self.client.get('/api/health',headers=headers).status_code,400)
  self.assertEqual(self.client.post('/api/auth/register',json={'email':'a@example.com','password':'Production-test-12345'},headers={'Origin':'https://evil.example'}).status_code,403)
  self.assertEqual(self.post('forgot-password',{'email':'x\r\nBcc:a@example.com'}).status_code,422)
  r=self.post('register',{'email':'another@example.com','password':'Production-test-12345'});self.assertEqual(r.status_code,200)
  self.assertEqual(str(self.messages[-1]['To']),'another@example.com')
  with self.app.state.store.connect() as db:self.assertTrue(db.execute("select 1 from attempts where bucket='register:192.0.2.10'").fetchone())
 def test_init_never_overwrites_and_production_rejects_local_modes(self):
  before=(self.path/'accounts.sqlite3').read_bytes()
  with self.assertRaises(ValueError):initialize(self.config)
  self.assertEqual(before,(self.path/'accounts.sqlite3').read_bytes())
  with self.assertRaises(ValueError):create_app(self.path,'https://racepick.cn',production=True,mail_config=MailConfig())
  with self.assertRaises(ValueError):create_app(self.path,'https://racepick.cn',production=True,mail_config=MailConfig('smtp','','x',production=True),preview_source=self.path)
  with self.app.state.store.connect() as db:db.execute('CREATE TABLE write_batches(id TEXT)')
  with self.assertRaises(ValueError):require_database(self.config)
 def test_production_mail_budget(self):
  self.app.state.mail_service.config=MailConfig('smtp','','mock',production=True,daily_limit=1)
  self.assertEqual(self.post('register',{'email':'one@example.com','password':'Production-test-12345'}).status_code,200)
  self.assertEqual(self.post('register',{'email':'two@example.com','password':'Production-test-12345'}).status_code,429)
  self.assertEqual(len(self.messages),1)

 def test_backup_restore_revokes_sessions_and_preserves_previous_copy(self):
  from backend.production import backup,restore
  from contextlib import nullcontext
  saved=backup(self.config)
  with self.app.state.store.connect() as db:
   db.execute("INSERT INTO sessions VALUES('test-session',NULL,'test-csrf',9999999999)")
  with patch('backend.production.service_lock',lambda path:nullcontext()):restore(self.config,saved)
  with self.app.state.store.connect() as db:
   self.assertEqual(db.execute('SELECT count(*) FROM sessions').fetchone()[0],0)
   self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
  self.assertEqual(len(list((self.path/'backups').glob('*.sqlite3'))),2)

if __name__=='__main__':unittest.main()
