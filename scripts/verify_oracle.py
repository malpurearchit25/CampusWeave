"""Submit ONLY generated Oracle lab scripts to db<>fiddle under CC0, with explicit user approval.
Do not run this helper without understanding that the submitted SQL becomes public-domain material.
"""
import argparse,json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--accept-cc0',action='store_true');args=p.parse_args()
if not args.accept_cc0:raise SystemExit('Explicit --accept-cc0 is required to submit these generated scripts.')

def batches(text):
    buf=[];block=False
    for line in text.splitlines():
        stripped=line.strip()
        if not stripped or stripped.startswith('--') or stripped.upper().startswith('SET SERVEROUTPUT'):continue
        if not buf:block=bool(re.match(r'(?i)(CREATE OR REPLACE (PROCEDURE|FUNCTION|TRIGGER)|DECLARE\b|BEGIN\b)',stripped))
        if stripped=='/':
            if buf:yield '\n'.join(buf)+'\n/';buf=[];block=False
            continue
        buf.append(line)
        if not block and stripped.endswith(';'):
            yield '\n'.join(buf);buf=[]
    if buf:yield '\n'.join(buf)

sql=[]
for file in ['plsql_lab.sql','advanced_plsql.sql']:sql.extend(batches((ROOT/'sql/oracle'/file).read_text()))
request=urllib.request.Request('https://dbfiddle.uk/run?engine=oracle&version=21',data=json.dumps(sql).encode(),headers={'Content-Type':'application/json','User-Agent':'CampusWeave-course-project'})
with urllib.request.urlopen(request,timeout=120) as response:code=response.read().decode().strip()
if not re.fullmatch(r'[A-Za-z0-9_-]+',code):raise RuntimeError(code)
url='https://dbfiddle.uk/'+code
request=urllib.request.Request(url,headers={'Accept':'text/markdown','User-Agent':'CampusWeave-course-project'})
with urllib.request.urlopen(request,timeout=60) as response:result=response.read().decode()
(ROOT/'docs/oracle_execution.md').write_text('# Oracle 21c execution evidence\n\n'+url+'\n\n'+result,encoding='utf-8')
errors=re.findall(r'^> ``` error\n(.*?)^> ```',result,re.M|re.S)
(ROOT/'docs/oracle_evidence.json').write_text(json.dumps({'url':url,'engine':'Oracle 21c','batches':len(sql),'license':'CC0','errors':errors,'expected_capacity_rejection':'Expected capacity rejection: ORA-20001' in result,'cursor_trace_present':all('| '+kind+' |' in result for kind in ['IMPLICIT','EXPLICIT','PARAMETERIZED FOR LOOP','WEAK REF CURSOR','STRONG REF CURSOR','FOR UPDATE CURRENT OF'])},indent=2))
print(url);print('Submitted batches:',len(sql));print('Unhandled Oracle error batches:',len(errors))
