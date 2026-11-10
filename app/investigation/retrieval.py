"""SQLite provenance/vector storage, heading-aware chunks and reciprocal rank fusion."""
import hashlib, json, math, re, sqlite3
from pathlib import Path
from typing import Any
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from app.investigation.contracts import Chunk
from app.investigation.security import redact

HASH=lambda s:hashlib.sha256(s.encode()).hexdigest()
def tokens(text): return set(re.findall(r'[a-z][a-z0-9_]+',text.lower()))
def cosine(a,b):
    if len(a)!=len(b): raise ValueError('Embedding dimensions mismatch')
    den=math.sqrt(sum(x*x for x in a)*sum(x*x for x in b))
    return sum(x*y for x,y in zip(a,b))/den if den else 0

class KnowledgeStore:
    def __init__(self,path,root=None): self.path=Path(path); self.root=Path(root) if root else None
    def connect(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        db=sqlite3.connect(self.path,timeout=20)
        db.execute('CREATE TABLE IF NOT EXISTS chunks (id TEXT PRIMARY KEY, doc TEXT, source TEXT, heading TEXT, version TEXT, hash TEXT, content TEXT, vector TEXT, model TEXT, dimensions INTEGER)')
        return db
    def index(self,root,embedder=None,model=None,dimensions=None,reindex=False):
        records=[]
        for path in sorted(Path(root).rglob('*.md')):
            if path.is_symlink(): continue
            source=path.relative_to(root).as_posix(); text=redact(path.read_text()); version=HASH(text)
            heading='Overview'; content=[]; sections=[]
            for line in text.splitlines():
                if re.match(r'^#{1,6} ',line):
                    if content: sections.append((heading,'\n'.join(content)))
                    heading=line.lstrip('# ').strip(); content=[]
                else: content.append(line)
            if content: sections.append((heading,'\n'.join(content)))
            for section,(heading,body) in enumerate(sections):
                for offset in range(0,len(body),1800):
                    chunk=body[offset:offset+1800].strip()
                    if chunk:
                        identity=HASH(source+':'+str(section)+':'+str(offset))[:24]
                        records.append((identity,HASH(source)[:24],source,heading,version,HASH(chunk),chunk))
        with self.connect() as db:
            existing={r[0]:r[1:] for r in db.execute('SELECT id,hash,model,dimensions,vector FROM chunks')}
            changed=[]
            for row in records:
                old=existing.get(row[0]); needs=reindex or not old or old[0]!=row[5] or (embedder and (old[1]!=model or old[2]!=dimensions or not old[3]))
                if needs: changed.append(row)
            vectors=embedder.embed_documents([r[3]+'\n'+r[6] for r in changed]) if embedder and changed else [None]*len(changed)
            if len(vectors)!=len(changed): raise ValueError('Embedding count mismatch')
            for row,vector in zip(changed,vectors):
                if vector is not None and (len(vector)!=dimensions or not all(math.isfinite(v) for v in vector)): raise ValueError('Invalid embedding vector')
                db.execute('INSERT OR REPLACE INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?)',(*row,json.dumps(vector) if vector is not None else None,model if vector is not None else None,dimensions if vector is not None else None))
            keep={r[0] for r in records}
            for identity in existing:
                if identity not in keep: db.execute('DELETE FROM chunks WHERE id=?',(identity,))
        return {'chunks':len(records),'updated':len(changed),'embedded':sum(v is not None for v in vectors)}
    def retrieve(self,query,k=4,budget=12000,embedder=None,model=None,dimensions=None):
        if not self.path.exists(): return [],'unavailable'
        with self.connect() as db: rows=db.execute('SELECT * FROM chunks ORDER BY id').fetchall()
        if not rows:return [],'unavailable'
        stale=False
        if self.root:
            for row in rows:
                source=self.root/row[2]
                if not source.is_file() or source.is_symlink() or HASH(redact(source.read_text()))!=row[4]:
                    stale=True;break
        qt=tokens(query)
        lexical=sorted(((len(qt & tokens(r[3]+' '+r[6])),r[0]) for r in rows),key=lambda t:(-t[0],t[1]))
        lexical=[i for score,i in lexical if score>0]
        rankings=[lexical]; mode='lexical_fallback'
        if embedder:
            compatible=all(r[7] and r[8]==model and r[9]==dimensions for r in rows)
            if compatible:
                vector=embedder.embed_query(redact(query)); semantic=sorted(((cosine(vector,json.loads(r[7])),r[0]) for r in rows),key=lambda t:(-t[0],t[1]))
                rankings.append([i for score,i in semantic if score>0]); mode='hybrid' if lexical else 'semantic'
            else: mode='lexical_fallback_incompatible_index'
        scores={}
        for ranking in rankings:
            for rank,identity in enumerate(ranking): scores[identity]=scores.get(identity,0)+1/(60+rank+1)
        by_id={r[0]:r for r in rows}; result=[]; used=0
        for identity in sorted(scores,key=lambda i:(-scores[i],i))[:k]:
            r=by_id[identity]
            if used+len(r[6])>budget: continue
            used+=len(r[6]); result.append(Chunk(id=r[0],document_id=r[1],source=r[2],heading=r[3],version=r[4],content_hash=r[5],content=r[6],score=scores[identity]))
        return result,mode+('_stale_documents' if stale else '')

class OperationalRetriever(BaseRetriever):
    store: Any
    embedder: Any = None
    model: str | None = None
    dimensions: int | None = None
    top_k: int = 4
    budget: int = 12000
    mode: str = 'unavailable'
    def _get_relevant_documents(self,query,*,run_manager):
        chunks,self.mode=self.store.retrieve(query,self.top_k,self.budget,self.embedder,self.model,self.dimensions)
        return [Document(page_content=c.content,metadata=c.model_dump(exclude={'content'})) for c in chunks]
    def chunks(self,query):
        return [Chunk(content=d.page_content,**d.metadata) for d in self.invoke(query)]
