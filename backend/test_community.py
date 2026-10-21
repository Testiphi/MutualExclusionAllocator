import unittest
from backend import test_roles as roles
from backend.roles import set_role
from backend.community import migrate

class CommunityTests(unittest.TestCase):
    setUp=roles.RolesTests.setUp
    tearDown=roles.RolesTests.tearDown
    new_client=roles.RolesTests.new_client
    post=roles.RolesTests.post
    token=roles.RolesTests.token
    signup=roles.RolesTests.signup
    login=roles.RolesTests.login
    owner=roles.RolesTests.owner
    def test_controls_and_retained_profile(self):
        owner=self.owner();other=self.new_client();target=self.signup('target@example.com',other)
        other.put('/api/me/profile',json={'revision':0,'cars':[],'stars':{}})
        url='/api/admin/accounts/'+target['id']+'/control'
        self.assertEqual(other.get('/api/admin/accounts').status_code,403)
        set_role(self.path,'target@example.com','admin');self.login(other,'target@example.com')
        self.assertEqual(other.get('/api/admin/accounts').status_code,403)
        self.assertEqual(other.get('/api/admin/announcements').status_code,403)
        def action(name,rev):return self.client.post(url,json={'action':name,'revision':rev,'reason':'test'})
        self.assertEqual(action('disable',0).status_code,200)
        self.assertEqual(other.get('/api/me/profile').status_code,401)
        anonymous=self.new_client()
        self.assertEqual(self.post('login',{'email':'target@example.com','password':'local-password-12345'},anonymous).status_code,403)
        anonymous.close()
        self.assertEqual(action('restore',0).status_code,409)
        self.assertEqual(action('restore',1).status_code,200)
        self.login(other,'target@example.com')
        self.assertEqual(other.get('/api/me/profile').json()['revision'],1)
        self.assertEqual(action('logout',2).status_code,200)
        self.assertEqual(other.get('/api/me/profile').status_code,401)
        for name in ['disable','restore','logout']:
            self.assertEqual(self.client.post('/api/admin/accounts/'+owner['id']+'/control',json={'action':name,'revision':0,'reason':'test'}).status_code,403)
        rows=self.client.get('/api/admin/accounts?q=target&status=active').json()
        self.assertEqual(rows['total'],1);self.assertNotIn('password_hash',str(rows))
        self.assertEqual(len(self.client.get('/api/admin/accounts/'+target['id']+'/events').json()['items']),3)
        other.close()
    def test_announcements_preferences_and_isolation(self):
        self.owner();other=self.new_client();self.signup('reader@example.com',other)
        draft=self.client.post('/api/admin/announcements',json={'title':'Update','body':'<script>plain text</script>'}).json();aid=draft['id']
        self.assertEqual(other.get('/api/announcements').json()['total'],0)
        self.assertEqual(other.post('/api/admin/announcements',json={'title':'x','body':'y'}).status_code,403)
        endpoint='/api/admin/announcements/'+aid+'/state'
        self.assertEqual(self.client.post(endpoint,json={'action':'publish','revision':1}).status_code,200)
        self.assertEqual(other.get('/api/announcements').json()['total'],1)
        self.assertEqual(other.post('/api/me/announcements/'+aid+'/dismiss',json={}).status_code,200)
        self.assertEqual(other.get('/api/me/announcement-preferences').json()['ignored'],[aid])
        self.assertEqual(self.client.get('/api/me/announcement-preferences').json()['ignored'],[])
        self.assertEqual(other.put('/api/me/announcement-preferences',json={'muted':True,'revision':0}).status_code,200)
        self.assertEqual(other.put('/api/me/announcement-preferences',json={'muted':False,'revision':0}).status_code,409)
        self.assertEqual(other.put('/api/me/announcement-preferences',json={'muted':False,'revision':1}).status_code,200)
        self.assertEqual(self.client.post(endpoint,json={'action':'withdraw','revision':2}).status_code,200)
        self.assertEqual(other.get('/api/announcements').json()['total'],0)
        other.close()
    def test_old_autosave_is_blocked_and_migration_idempotent(self):
        self.signup();del self.client.headers['X-Profile-Save']
        self.assertEqual(self.client.put('/api/me/profile',json={'revision':0,'cars':[],'stars':{}}).status_code,409)
        self.assertIsNone(self.client.get('/api/me/profile').json()['profile'])
        with self.app.state.store.connect() as db:
            before=[tuple(r) for r in db.execute('SELECT * FROM users')];migrate(db)
            self.assertEqual(before,[tuple(r) for r in db.execute('SELECT * FROM users')])

    def test_old_metadata_migration_preserves_accounts_and_requires_explicit_upgrade(self):
        from backend.production import initialize,require_database
        import sqlite3
        from contextlib import closing
        from backend.community import TABLES
        config={'origin':'https://racepick.cn','data_dir':str(self.path/'production'),'owner_email':'owner@example.com','mail_daily_limit':100}
        initialize(config)
        with closing(sqlite3.connect(self.path/'production/accounts.sqlite3')) as db,db:
            for statement in reversed(TABLES):db.execute('DROP TABLE '+statement.split('CREATE TABLE ')[1].split('(')[0])
        with self.assertRaises(ValueError):require_database(config)
        require_database(config,require_community=False)
        with closing(sqlite3.connect(self.path/'production/accounts.sqlite3')) as db,db:migrate(db)
        require_database(config)

if __name__=='__main__':unittest.main()
