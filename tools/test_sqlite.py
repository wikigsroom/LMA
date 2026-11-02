"""Execute the production v1→v2 upgrade and paging SQL on real SQLite; no Android claim."""
import json, sqlite3
from evidence import ROOT, fingerprint, current
from test_conversation import sqlite_checks

def main():
    out=ROOT/'build/sqlite-tests';out.mkdir(parents=True,exist_ok=True)
    inputs=fingerprint('app/src/main/java/com/lma/app/Chats.java','tools/test_sqlite.py','tools/test_conversation.py')
    checks=sqlite_checks();current(inputs)
    record=dict(passed=len(checks),checks=checks,sqlite_version=sqlite3.sqlite_version,android_framework_tested=False,input_fingerprint=inputs)
    (out/'results.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in record.items() if k in ['passed','sqlite_version','android_framework_tested']}))

if __name__=='__main__':main()
