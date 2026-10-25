"""New isolated unread+usage demo. All historical distributions are synthetic."""
import io
from contextlib import redirect_stdout
from datetime import datetime, timedelta
import json
from pathlib import Path
import secrets
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from examples.unread_demo import main as prepare_unread
from backend.app import create_app
from backend.usage import BJ


def main():
    with redirect_stdout(io.StringIO()):lab=prepare_unread()
    app=create_app(lab/'accounts',score_version_lab=lab,contributions=True,feedback=True,notifications=True,usage=True)
    with app.state.store.connect() as db:users=[r[0] for r in db.execute('SELECT id FROM users ORDER BY email')]
    actors=['a:'+uid for uid in users]+['v:'+secrets.token_hex(16) for _ in range(6)]
    today=datetime.now(BJ).date();total=0
    for days in range(27,-1,-1):
        for index,actor in enumerate(actors):
            if (days+index)%3==0:continue
            if index>5 and days>8:continue  # New and returning visitor examples.
            hour=(8+index*2+days%4)%24
            stamp=int(datetime.combine(today-timedelta(days=days),datetime.min.time(),tzinfo=BJ).replace(hour=hour,minute=12).timestamp())
            if stamp>datetime.now(BJ).timestamp():continue
            server='global' if (index+days)%2==0 else 'cn';sid=secrets.token_hex(16)
            def event(kind,**extra):return {'id':secrets.token_hex(16),'kind':kind,'page':'home','server':server,**extra}
            events=[event('visit',reason='open'),event('active'),event('feature',feature='generate',result='success')]
            total+=app.state.usage.append(actor,sid,events,now=stamp)
            for minute in range(1,2+(index+days)%5):
                total+=app.state.usage.append(actor,sid,[event('active')],now=stamp+minute*60)
    (lab/'usage-demo.json').write_text(json.dumps({'synthetic_only':True,'seeded_events':total,'days':28,'created_day':today.isoformat(),'port':8017},indent=2),encoding='utf-8')
    print('NEW synthetic usage lab: '+str(lab))
    print('Login details: '+str(lab/'LOGIN.txt'))
    print(f'python -B -X utf8 -m backend.app --port 8017 --data-dir "{lab / "accounts"}" --score-version-lab "{lab}" --contributions --feedback --notifications --usage')
    return lab


if __name__=='__main__':main()
