"""Export unchanged CSS design values; --check rejects stale generated artifacts."""
from pathlib import Path
import argparse
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[1]
SOURCES=('theme.css','styles.css','ui.css','accounts.css','map_recognition.css')


def blocks(text,conditions=()):
    text=re.sub(r'/\*.*?\*/','',text,flags=re.S);position=0;out=[]
    while position<len(text):
        start=text.find('{',position)
        if start<0:break
        header=text[position:start].strip();depth=1;quote=None;i=start+1
        while i<len(text) and depth:
            c=text[i]
            if quote:
                if c==quote and text[i-1]!='\\':quote=None
            elif c in ('"',"'"):quote=c
            elif c=='{':depth+=1
            elif c=='}':depth-=1
            i+=1
        if depth:raise ValueError('CSS block structure changed')
        body=text[start+1:i-1].strip()
        if header.startswith('@'):out.extend(blocks(body,(*conditions,header)))
        else:out.append({'selector':header,'conditions':list(conditions),'declarations':body})
        position=i
    return out


def generate():
    sources={};rules=[];tokens={}
    for name in SOURCES:
        text=(ROOT/name).read_text('utf-8')
        raw=text.encode('utf-8')
        sources[name]={'sha256_utf8_lf':hashlib.sha256(raw).hexdigest(),'bytes_utf8_lf':len(raw),'text':text}
        rules.extend({'source':name,**rule} for rule in blocks(text))
        for rule in rules:
            if rule['source']==name and rule['selector']==':root':tokens.update(re.findall(r'(--[\w-]+)\s*:\s*([^;]+);',rule['declarations']))
    for selector in ('.card','.car-grid','.car-tag','.garage-btn'):
        if not any(r['selector']==selector for r in rules):raise ValueError('Required website selector changed: '+selector)
    return {'schema_version':1,'hash_basis':'UTF-8 with LF; no design-value transformations','tokens':tokens,'sources':sources,'rules':rules}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args()
    target=ROOT/'home_theme.json';raw=(json.dumps(generate(),ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    if args.check:
        if target.read_bytes()!=raw:raise SystemExit('home_theme.json is stale; regenerate from current CSS')
    else:target.write_bytes(raw)


if __name__=='__main__':main()
