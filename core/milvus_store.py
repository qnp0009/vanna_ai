from vanna.base import VannaBase
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
from sentence_transformers import SentenceTransformer
import pandas as pd
import uuid

class MilvusVectorDB(VannaBase):
    def __init__(self, config=None):
        self.collection_name = "vanna_knowledge"
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        host = (config or {}).get("milvus_host", "localhost")
        port = (config or {}).get("milvus_port", "19530")
        connections.connect(host=host, port=port)

        # Define schema for collection
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=36),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=1000),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384)
        ]
        schema = CollectionSchema(fields, description="Vanna knowledge base")
        if self.collection_name not in utility.list_collections():
            self.collection = Collection(self.collection_name, schema=schema)
            self.collection.create_index(field_name="embedding", index_params={"metric_type": "L2", "index_type": "IVF_FLAT", "params": {"nlist": 128}})
        else:
            self.collection = Collection(self.collection_name)
        self.collection.load()

    def _embed(self, text: str):
        return self.embedder.encode([text])[0].tolist()

    def generate_embedding(self, text: str) -> list:
        return self._embed(text)

    def add_ddl(self, ddl: str, **kwargs) -> str:
        return self._add_entry(ddl)

    def add_documentation(self, doc: str, **kwargs) -> str:
        return self._add_entry(doc)

    def add_question_sql(self, question: str, sql: str, **kwargs) -> str:
        return self._add_entry(f"{question} => {sql}")

    def _add_entry(self, text: str) -> str:
        emb = self._embed(text)
        id_str = str(uuid.uuid4())
        self.collection.insert([[id_str], [text], [emb]])
        return id_str

    def _search(self, question: str) -> list:
        emb = self._embed(question)
        results = self.collection.search(
            data=[emb],
            anns_field="embedding",
            param={"metric_type": "L2", "params": {"nprobe": 10}},
            limit=3,
            output_fields=["text"]
        )
        # Each result in results[0] is a Hit object
        return [hit.get("text", "") for hit in results[0]]

    def get_related_ddl(self, question: str, **kwargs) -> list:
        return self._search(question)

    def get_related_documentation(self, question: str, **kwargs) -> list:
        return self._search(question)

    def get_similar_question_sql(self, question: str, **kwargs) -> list:
        return self._search(question)

    def get_training_data(self) -> pd.DataFrame:
        try:
            results = self.collection.query(
                expr="id != ''",
                output_fields=["id", "text"]
            )
            data = []
            for result in results:
                text = result.get('text', '')
                if ' => ' in text:
                    question, sql = text.split(' => ', 1)
                    data.append({
                        'id': result.get('id', ''),
                        'question': question,
                        'sql': sql,
                        'type': 'question_sql'
                    })
                else:
                    data.append({
                        'id': result.get('id', ''),
                        'text': text,
                        'type': 'documentation'
                    })
            return pd.DataFrame(data)
        except Exception as e:
            print(f"Error getting training data from Milvus: {e}")
            return pd.DataFrame()

    def remove_training_data(self, id: str) -> bool:
        try:
            self.collection.delete(f"id == '{id}'")
            return True
        except Exception as e:
            print(f"Error removing training data: {e}")
            return False
