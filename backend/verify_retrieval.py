import sys
sys.path.insert(0, '.')
from app.retrieval.metrics.collector import MetricsCollector
from app.retrieval.retrieval.multi_index import MultiIndexRetriever

metrics = MetricsCollector()
metrics.record('latency.retrieval', 12.5)
metrics.record('latency.retrieval', 27.5)
print(metrics.summarize())
retriever = MultiIndexRetriever(vector_store=None, embedding_provider=None)
print(retriever._select_aliases(['government','research']))
print(retriever._select_aliases(['krishios-gov-docs']))
