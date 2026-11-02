"""Execute production conversation foundation contracts and real SQLite migration/query SQL."""
import json,os,re,shutil,sqlite3,subprocess
from pathlib import Path
from evidence import fingerprint,current
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/conversation-tests'

def sqlite_checks():
    OUT.mkdir(parents=True,exist_ok=True)
    source=(ROOT/'app/src/main/java/com/lma/app/Chats.java').read_text(encoding='utf-8')
    statements=re.findall(r'db\.execSQL\("([^"]+)"\)',source)
    base=statements[:3];upgrade=statements[3:];checks=[]
    path=OUT/'migration.sqlite';path.unlink(missing_ok=True)
    with sqlite3.connect(path) as db:
        for sql in base:db.execute(sql)
        for i in range(100):db.execute('INSERT INTO sessions VALUES(?,?,?,?)',(str(i),'old session '+str(i),'m01',i))
        for i in range(1000):db.execute('INSERT INTO messages VALUES(?,?,?,?,?,?,?,?,?,?)',(str(i),str(i//10),'user' if i%2==0 else 'assistant','原文\n'+str(i),'旧思考', 'error' if i%7==0 else 'done','旧错误',i,7,12))
    with sqlite3.connect(path) as db:
        original=db.execute('SELECT * FROM messages ORDER BY rowid').fetchall()
        db.execute('BEGIN')
        try:
            for sql in upgrade:db.execute(sql)
            db.execute('INTENTIONALLY INVALID SQL')
        except sqlite3.Error:db.rollback()
        assert len(db.execute('PRAGMA table_info(messages)').fetchall())==10
        assert db.execute('SELECT * FROM messages ORDER BY rowid').fetchall()==original
        checks.append('Failed upgrade rolls back schema and every original field in real SQLite')
        for sql in upgrade:db.execute(sql)
        assert [row[:10] for row in db.execute('SELECT * FROM messages ORDER BY rowid')]==original
        checks.append('v1→v2 preserves 100 sessions / 1000 messages, exact Unicode, reasoning, errors and order')
        for i in range(1000,1120):db.execute('INSERT INTO messages(id,session,role,content,reasoning,status,error,created,tokens,elapsed) VALUES(?,?,?,?,?,?,?,?,?,?)',(str(i),'long','assistant','body '+str(i),'','done','',i,0,0))
        queries=re.findall(r'rawQuery\("([^"]+)"',source)
        page=next(q for q in queries if 'rowid<?' in q and 'LIMIT ?' in q and 'messages' in q)
        all_ids=[];before=2**63-1
        while True:
            cursor=db.execute(page,('long',before,'60'));names=[c[0] for c in cursor.description];rows=cursor.fetchall()
            if not rows:break
            all_ids=[r[names.index('id')] for r in rows]+all_ids;before=rows[0][names.index('rowid')]
        assert all_ids==[str(i) for i in range(1000,1120)]
        checks.append('Production cursor SQL pages complete history without duplicates or truncation')
        assert db.execute(page,("x' OR 1=1--",str(2**63-1),'60')).fetchall()==[]
        checks.append('Bound cursors and session IDs isolate hostile SQL-like input')
        db.execute("INSERT INTO chat_outbox(id,session,message,request,state,created) VALUES('stable','long','1119','{}','pending',1)")
        db.execute("INSERT INTO chat_refs VALUES('long','1119','artifact_a')")
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT id,state FROM chat_outbox').fetchone()==('stable','pending')
        assert db.execute('SELECT artifact FROM chat_refs').fetchone()[0]=='artifact_a'
        checks.append('Outbox and chat asset references survive real database close/reopen')
    return checks

def main():
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'results.json').unlink(missing_ok=True)
    inputs=fingerprint('app/src/main/java/com/lma/app/core','app/src/main/java/com/lma/app/Chats.java','tests/ConversationFoundationTest.java','tools/test_conversation.py','tests/host/android/util/AtomicFile.java')
    run=OUT/'run'
    if run.exists():assert run.resolve().parent==OUT.resolve();shutil.rmtree(run)
    run.mkdir();classes=OUT/'classes';classes.mkdir(exist_ok=True)
    sources=sorted((ROOT/'app/src/main/java/com/lma/app/core').glob('*.java'))+[ROOT/'tests/ConversationFoundationTest.java',ROOT/'tests/host/android/util/AtomicFile.java']
    rsp=OUT/'sources.rsp';rsp.write_text('\n'.join('"'+p.as_posix()+'"' for p in sources),encoding='utf-8');dep=ROOT/'build/test-deps/json-20250517.jar'
    subprocess.run([shutil.which('javac'),'-encoding','UTF-8','--release','11','-cp',str(dep),'-d',str(classes),'@'+str(rsp)],cwd=ROOT,check=True)
    result=subprocess.run([shutil.which('java'),'-Dfile.encoding=UTF-8','-cp',str(classes)+os.pathsep+str(dep),'com.lma.app.ConversationFoundationTest',str(run)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=60)
    (OUT/'output.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    report=json.loads(result.stdout.strip().splitlines()[-1]);report['sqlite_checks']=sqlite_checks();report['assertions']+=len(report['sqlite_checks']);report['input_fingerprint']=inputs;current(inputs)
    (OUT/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['input_fingerprint','sqlite_checks']}))

if __name__=='__main__':main()
