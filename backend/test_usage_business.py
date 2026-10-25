"""Successful business operations record minimal metadata after commit, never replay writes."""
import secrets
import sqlite3
import unittest
from unittest.mock import patch
from backend import test_feedback as fixtures
from backend import test_contributions as contributions
from backend.app import create_app


class UsageBusinessTests(unittest.TestCase):
    new_client=fixtures.FeedbackTests.new_client
    login=fixtures.FeedbackTests.login
    signup=fixtures.FeedbackTests.signup
    post=fixtures.FeedbackTests.post
    token=fixtures.FeedbackTests.token
    payload=fixtures.FeedbackTests.payload
    tearDown=fixtures.FeedbackTests.tearDown

    def setUp(self):
        fixtures.FeedbackTests.setUp(self);self.client.close();self.player.close()
        self.app=create_app(self.path,score_version_lab=self.lab,contributions=True,feedback=True,usage=True)
        self.client=self.new_client();self.login(self.client,'owner@example.com')
        self.player=self.new_client();self.login(self.player,'player@example.com')
        for client in (self.client,self.player):
            r=client.post('/api/usage/session',json={'visitor_id':secrets.token_hex(16),'session_id':secrets.token_hex(16)})
            self.assertEqual(r.status_code,200);client.headers['X-Usage-Token']=r.json()['token']

    def test_feedback_idempotency_no_content_and_failure_does_not_fail_business(self):
        body=self.payload(description='PRIVATE_INPUT_DO_NOT_COLLECT')
        first=self.player.post('/api/feedback',json=body);self.assertEqual(first.status_code,200,first.text)
        self.assertEqual(self.player.post('/api/feedback',json=body).json(),first.json())
        with self.app.state.usage.connect() as db:
            self.assertEqual(db.execute("SELECT uses FROM usage_features WHERE server='all' AND feature='feedback_submit'").fetchone()[0],1)
            self.assertNotIn('PRIVATE_INPUT_DO_NOT_COLLECT','\n'.join(db.iterdump()))
            self.assertEqual(db.execute('SELECT count(*) FROM usage_minutes').fetchone()[0],0)
        with patch.object(self.app.state.usage,'append',side_effect=sqlite3.OperationalError('test locked')):
            self.assertEqual(self.player.post('/api/feedback',json=self.payload()).status_code,200)
        with self.app.state.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM feedback_tickets').fetchone()[0],2)

    def test_submission_success_and_resubmission_are_counted_but_drafts_are_not(self):
        sid=contributions.ContributionTests.submission(self)
        with self.app.state.usage.connect() as db:self.assertEqual(db.execute("SELECT uses FROM usage_features WHERE server='all' AND feature='submission_submit'").fetchone()[0],1)
        revision=self.client.get('/api/submissions/'+sid).json()['revision']
        r=self.client.post('/api/admin/submissions/'+sid+'/review',json={'revision':revision,'action':'needs_info','reason':'请补充证据'})
        self.assertEqual(r.status_code,200,r.text)
        revision=self.player.get('/api/submissions/'+sid).json()['revision']
        self.assertEqual(self.player.post('/api/submissions/'+sid+'/submit',json={'revision':revision}).status_code,200)
        self.assertEqual(self.player.post('/api/submissions/'+sid+'/submit',json={'revision':revision}).status_code,409)
        with self.app.state.usage.connect() as db:self.assertEqual(db.execute("SELECT uses FROM usage_features WHERE server='all' AND feature='submission_submit'").fetchone()[0],2)

    def test_wrong_analytics_context_does_not_misattribute_or_block_feedback(self):
        self.player.headers['X-Usage-Token']=self.client.headers['X-Usage-Token']
        self.assertEqual(self.player.post('/api/feedback',json=self.payload()).status_code,200)
        with self.app.state.usage.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM usage_events').fetchone()[0],0)


if __name__=='__main__':unittest.main()
