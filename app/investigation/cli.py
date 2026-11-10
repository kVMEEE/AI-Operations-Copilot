import argparse,json
from app.investigation.settings import InvestigationSettings
from app.investigation.retrieval import KnowledgeStore

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['index','init-db']);p.add_argument('--semantic',action='store_true');p.add_argument('--reindex',action='store_true');a=p.parse_args();s=InvestigationSettings()
    if a.command=='init-db':
        from app.investigation.persistence import Store
        Store(s.database_url).initialize(); print('Database schema v1 initialized');return
    embedder=None
    if a.semantic:
        if not s.key(): p.error('Semantic indexing requires AIOPS_API_KEY or OPENAI_API_KEY')
        from app.llm.client import embeddings
        embedder=embeddings(s)
    print(json.dumps(KnowledgeStore(s.knowledge_db).index(s.knowledge_dir,embedder,s.embedding_model,s.embedding_dimensions,a.reindex)))
if __name__=='__main__':main()
