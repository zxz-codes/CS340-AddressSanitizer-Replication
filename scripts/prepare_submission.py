"""Prepare a bounded, explicit submission allowlist for review/upload.
This does not publish anything or read credentials.
"""
import base64
import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
dest=root/'tmp/submission'
dest.mkdir(parents=True,exist_ok=True)
files=[]
for name in ('.gitignore','.gitattributes','LICENSE','README.md','requirements-report.txt'):
    files.append(root/name)
for folder in ('config','examples','scripts','vendor','reports','output/pdf','records'):
    files.extend(p for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
files=sorted(set(files))
text_entries=[]
binary_entries=[]
manifest=[]
for file in files:
    relative=file.relative_to(root).as_posix()
    assert file.stat().st_size<50*1024*1024,relative
    data=file.read_bytes()
    manifest.append({'path':relative,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    if file.suffix=='.pdf':
        binary_entries.append({'path':relative,'base64':base64.b64encode(data).decode('ascii')})
    else:
        text=data.decode('utf-8-sig').replace('\r\n','\n')
        text_entries.append({'path':relative,'mode':'100644','type':'blob','content':text})
batches=[]
batch=[]
length=0
for entry in text_entries:
    n=len(json.dumps(entry,ensure_ascii=False))
    if batch and length+n>100000:
        batches.append(batch);batch=[];length=0
    batch.append(entry);length+=n
if batch:batches.append(batch)
for i,batch in enumerate(batches):
    (dest/f'batch-{i:03d}.json').write_text(json.dumps(batch,ensure_ascii=False),encoding='utf-8')
(dest/'binary.json').write_text(json.dumps(binary_entries,ensure_ascii=False),encoding='utf-8')
(dest/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
index={'files':len(files),'bytes':sum(f['bytes'] for f in manifest),'text_batches':len(batches),
       'pdf_count':len(binary_entries),'largest_text_batch':max((dest/f'batch-{i:03d}.json').stat().st_size for i in range(len(batches)))}
(dest/'index.json').write_text(json.dumps(index,indent=2),encoding='utf-8')
print(json.dumps(index,indent=2))
