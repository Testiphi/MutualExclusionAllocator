"""Isolated statistics tests; no existing account data or production traffic."""
from datetime import datetime, timezone
import json
import secrets
import sqlite3
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend import test_accounts as fixtures
from backend.app import create_app
from backend.roles import set_role
from backend.usage import UsageStore, day_at


class UsageTests(unittest.TestCase):
    new_client=fixtures.AccountsTests.new_client
    signup=fixtures.AccountsTests.signup
    post=fixtures.AccountsTests.post
    token=fixtures.AccountsTests.token
    tearDown=fixtures.AccountsTests.tearDown

    def setUp(self):
        fixtures.AccountsTests.setUp(self)
        self.client.close();self.app=create_app(self.path,usage=True);self.client=self.new_client()
        self.visitor=secrets.token_hex(16);self.visit=secrets.token_hex(16)

    def bootstrap(self,client=None,visitor=None,visit=None):
        r=(client or self.client).post('/api/usage/session',json={'visitor_id':visitor or self.visitor,'session_id':visit or self.visit})
        self.assertEqual(r.status_code,200,r.text)
        (client or self.client).headers['X-Usage-Token']=r.json()['token']
        return r.json()

    def event(self,kind='visit',**extra):
        return {'id':secrets.token_hex(16),'kind':kind,'page':'home','server':'cn',**({'reason':'open'} if kind=='visit' else {}),**extra}

    def send(self,events,client=None):
        return (client or self.client).post('/api/usage/events',json={'events':events})

    def owner(self):
        self.user=self.signup('owner@example.com');set_role(self.path,'owner@example.com','superadmin')
        self.client.cookies.clear();self.client.headers['X-CSRF-Token']=self.client.get('/api/auth/me').json()['csrf']
        r=self.post('login',{'email':'owner@example.com','password':fixtures.PASSWORD})
        self.assertEqual(r.status_code,200,r.text)
        self.client.headers.update({'X-CSRF-Token':r.json()['csrf'],'X-Account-ID':self.user['id']})
        return self.user

    def test_anonymous_bootstrap_is_narrow_and_does_not_create_login_session(self):
        guest=TestClient(self.app,base_url=fixtures.ORIGIN,headers={'Origin':fixtures.ORIGIN})
        try:
            with self.app.state.store.connect() as db:before=db.execute('SELECT count(*) FROM sessions').fetchone()[0]
            self.bootstrap(guest)
            self.assertEqual(self.send([self.event()],guest).status_code,200)
            with self.app.state.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM sessions').fetchone()[0],before)
            self.assertEqual(self.send([self.event()],TestClient(self.app,base_url=fixtures.ORIGIN)).status_code,403)
            self.assertEqual(guest.post('/api/usage/session',json={'visitor_id':self.visitor,'session_id':self.visit},headers={'Origin':'https://elsewhere.test'}).status_code,403)
            self.assertEqual(guest.post('/api/usage/events',content='x'*8193,headers={'Content-Type':'application/json'}).status_code,413)
            self.assertEqual(guest.put('/api/me/profile',json={'revision':0,'cars':[],'stars':{}}).status_code,401)
        finally:guest.close()

    def test_identity_is_server_bound_and_client_cannot_send_business_events_or_content(self):
        self.bootstrap();anonymous=self.client.headers['X-Usage-Token'];self.owner()
        self.client.headers['X-Usage-Token']=anonymous
        self.assertEqual(self.send([self.event()]).status_code,409)
        self.bootstrap()
        self.assertEqual(self.send([self.event(user_id='forged')]).status_code,422)
        self.assertEqual(self.send([self.event('feature',feature='submission_submit',result='success')]).status_code,422)
        self.assertEqual(self.send([self.event('active',reason='resume')]).status_code,422)
        self.assertEqual(self.send([self.event(page='admin-usage')]).status_code,422)
        self.assertEqual(self.send([self.event('active')]).status_code,200)
        with self.app.state.usage.connect() as db:self.assertEqual(db.execute('SELECT actor FROM usage_people').fetchone()[0],'a:'+self.user['id'])

    def test_duplicate_requests_minutes_tabs_devices_and_two_servers(self):
        owner=self.owner();self.bootstrap();event=self.event('active')
        self.assertEqual(self.send([event]).json()['accepted'],1)
        self.assertEqual(self.send([event]).json()['accepted'],0)
        second=TestClient(self.app,base_url=fixtures.ORIGIN,headers=dict(self.client.headers))
        try:
            second.cookies.update(self.client.cookies);self.bootstrap(second,visitor=secrets.token_hex(16),visit=secrets.token_hex(16))
            self.assertEqual(self.send([self.event('active'),self.event('active',server='global')],second).status_code,200)
        finally:second.close()
        with self.app.state.usage.connect() as db:
            self.assertEqual(dict(db.execute('SELECT server,active_minutes FROM usage_daily WHERE actor=?',('a:'+owner['id'],))),{'all':1,'cn':1,'global':1})
        data=self.client.get('/api/admin/usage').json()
        self.assertEqual(data['windows']['account']['dau'],1)
        self.assertEqual(sum(sum(r) for r in data['heatmap']['account']),1)
        self.assertEqual(self.client.get('/api/admin/usage?server=global').json()['windows']['account']['dau'],1)

    def test_visits_polls_and_resources_do_not_count_as_actual_activity(self):
        self.owner();self.bootstrap()
        self.send([self.event(),self.event(reason='resume')])
        for url in ('/','/api/auth/me','/api/health','/usage.js','/api/admin/usage'):
            self.assertEqual(self.client.get(url).status_code,200,url)
        data=self.client.get('/api/admin/usage').json();self.assertEqual(data['windows']['account']['dau'],0)
        today=data['daily'][0]['account'];self.assertEqual(today['visitors'],1);self.assertEqual(today['opens'],1);self.assertEqual(today['resumes'],1)
        self.assertEqual(today['minutes'],0)

    def test_beijing_boundaries_first_seen_and_pruning_keep_exact_aggregates(self):
        store=self.app.state.usage
        before=int(datetime(2026,10,23,15,59,tzinfo=timezone.utc).timestamp())
        after=before+120
        self.assertEqual(day_at(before),'2026-10-23');self.assertEqual(day_at(after),'2026-10-24')
        store.append('v:visitor',self.visit,[self.event(),self.event('active')],now=before)
        store.append('v:visitor',self.visit,[self.event(),self.event('active'),self.event('feature',feature='generate',result='success')],now=after)
        data=store.overview('2026-10-23','2026-10-24',now=after)
        self.assertEqual(data['windows']['guest']['dau'],1)
        self.assertEqual(data['daily'][0]['guest']['new'],1);self.assertEqual(data['daily'][1]['guest']['returning'],1)
        self.assertEqual(data['features'][0]['guest']['people'],1)
        self.assertGreater(store.prune(now=after+100*86400)['raw_events'],0)
        store.prune(now=after+100*86400,execute=True)
        self.assertEqual(store.overview('2026-10-23','2026-10-24',now=after),data)
        with store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM usage_events').fetchone()[0],0)

    def test_privileged_queries_require_superadmin_and_dates_are_bounded(self):
        self.assertEqual(self.client.get('/api/admin/usage').status_code,401)
        player=self.signup();self.assertEqual(self.client.get('/api/admin/usage').status_code,403)
        self.client.cookies.clear();self.client.headers['X-CSRF-Token']=self.client.get('/api/auth/me').json()['csrf']
        self.owner()
        self.assertEqual(self.client.get('/api/admin/usage?start=2020-01-01&end=2026-10-01').status_code,422)
        self.assertEqual(self.client.get('/api/admin/usage?start=bad').status_code,422)
        self.assertEqual(self.client.get('/api/admin/usage/accounts?offset=-1').status_code,422)
        data=self.client.get('/api/admin/usage/accounts').json()
        self.assertEqual(data['total'],2);self.assertIsNone(data['items'][0]['last_interaction'])
        self.client.headers['X-Account-ID']=player['id']
        self.assertEqual(self.client.get('/api/admin/usage').status_code,401)

    def test_statistics_failure_does_not_change_existing_account_state(self):
        self.owner();self.bootstrap()
        with patch.object(self.app.state.usage,'append',side_effect=sqlite3.OperationalError('locked')):
            self.assertEqual(self.send([self.event()]).status_code,503)
            self.assertEqual(self.client.put('/api/me/profile',json={'revision':0,'cars':[],'stars':{}}).status_code,200)
        with self.assertRaises(ValueError):create_app(self.path)

    def test_long_range_distinct_people_are_not_sums_of_daily_counts(self):
        store=self.app.state.usage;now=int(datetime(2026,10,25,2,tzinfo=timezone.utc).timestamp())
        for days,actors in [(29,['a:one','v:guest']),(6,['a:one','a:two']),(0,['a:one'])]:
            for actor in actors:
                store.append(actor,self.visit,[self.event(),self.event('active'),self.event('feature',feature='generate',result='success')],now=now-days*86400)
        data=store.overview('2026-09-26','2026-10-25',now=now)
        self.assertEqual(data['windows']['account'],{'dau':1,'wau':2,'mau':2})
        self.assertEqual(data['windows']['guest'],{'dau':0,'wau':0,'mau':1})
        self.assertEqual(data['features'][0]['account'],{'uses':4,'people':2})
        self.assertEqual(data['features'][0]['guest'],{'uses':1,'people':1})
        self.assertEqual(sum(sum(r) for r in data['heatmap']['account']),4)

    def test_account_directory_activity_filters_order_and_privacy(self):
        owner=self.owner();others=[]
        try:
            old=self.new_client();others.append(old);old_user=self.signup('old@example.com',old)
            never=self.new_client();others.append(never);never_user=self.signup('never@example.com',never)
            now=int(datetime.now(timezone.utc).timestamp())
            self.app.state.usage.append('a:'+owner['id'],self.visit,[self.event(),self.event('active')],now=now)
            self.app.state.usage.append('a:'+old_user['id'],self.visit,[self.event('active')],now=now-35*86400)
            self.app.state.usage.append('a:'+never_user['id'],self.visit,[self.event()],now=now)
            recent=self.client.get('/api/admin/accounts?activity=week&order=interaction').json()
            self.assertEqual([r['id'] for r in recent['items']],[owner['id']])
            dormant=self.client.get('/api/admin/accounts?activity=inactive&role=player').json()
            self.assertEqual([r['id'] for r in dormant['items']],[old_user['id']])
            untouched=self.client.get('/api/admin/accounts?activity=never').json()
            self.assertEqual([r['id'] for r in untouched['items']],[never_user['id']])
            self.assertIsNotNone(untouched['items'][0]['last_visit']);self.assertIsNone(untouched['items'][0]['last_interaction'])
            sorted_items=self.client.get('/api/admin/accounts?order=interaction').json()['items']
            self.assertEqual([r['id'] for r in sorted_items],[owner['id'],old_user['id'],never_user['id']])
            self.assertEqual(self.client.get('/api/admin/accounts?activity=week&q=old').json()['total'],0)
            self.assertEqual(old.get('/api/admin/accounts?activity=all').status_code,403)
            self.assertEqual(old.get('/api/admin/usage/accounts/'+owner['id']).status_code,403)
        finally:
            for c in others:c.close()

    def test_account_daily_detail_is_paged_filtered_and_readonly(self):
        owner=self.owner();now=int(datetime.now(timezone.utc).timestamp())
        for days in range(21,-1,-1):
            self.app.state.usage.append('a:'+owner['id'],self.visit,[
                self.event(server='global' if days%2 else 'cn'),
                self.event('active',server='global' if days%2 else 'cn'),
                self.event('feature',server='global' if days%2 else 'cn',feature='generate',result='success')],now=now-days*86400)
        raw=self.app.state.usage.path.read_bytes()
        url='/api/admin/usage/accounts/'+owner['id']
        first=self.client.get(url).json();second=self.client.get(url+'?offset=10').json()
        self.assertEqual(first['total'],22);self.assertEqual(len(first['items']),10);self.assertEqual(first['summary']['active_minutes'],22)
        self.assertEqual(first['summary']['opens'],22);self.assertGreater(first['items'][0]['day'],first['items'][-1]['day'])
        self.assertTrue(set(r['day'] for r in first['items']).isdisjoint(r['day'] for r in second['items']))
        self.assertEqual(first['items'][0]['features'],[{'feature':'generate','result':'success','uses':1}])
        global_only=self.client.get(url+'?server=global').json()
        self.assertEqual(global_only['total'],11);self.assertEqual(global_only['summary']['active_minutes'],11)
        self.assertEqual(self.client.get(url+'?offset=-1').status_code,422)
        self.assertEqual(self.client.get(url+'?start=invalid').status_code,422)
        self.assertEqual(self.client.get('/api/admin/usage/accounts/not-an-account').status_code,404)
        self.assertEqual(self.app.state.usage.path.read_bytes(),raw)
        self.client.headers['X-Account-ID']='other-account'
        self.assertEqual(self.client.get(url).status_code,401)


if __name__=='__main__':unittest.main()
