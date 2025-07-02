from vanna.base import VannaBase
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType
from sentence_transformers import SentenceTransformer
import pandas as pd
import uuid

class MilvusVectorDB(VannaBase):
    """
    Vector database implementation using Milvus for Vanna AI
    Lưu trữ và tìm kiếm vector cho cơ sở kiến thức của Vanna
    """
    def __init__(self, config=None):
        # Khởi tạo kết nối và collection
        self.collection_name = "vanna_knowledge"
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")  # Model tạo embedding
        connections.connect(host="localhost", port="19530")

        # Định nghĩa schema cho collection
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=36),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=1000),  # Nội dung văn bản
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384)  # Vector embedding
        ]
        schema = CollectionSchema(fields, description="Vanna knowledge base")
        self.collection = Collection(self.collection_name, schema=schema, using="default", consistency_level="Strong")

        # Tạo index cho vector search nếu chưa có
        if not self.collection.has_index():
            self.collection.create_index(field_name="embedding", index_params={"metric_type": "L2", "index_type": "IVF_FLAT", "params": {"nlist": 128}})
        self.collection.load()

    def _embed(self, text: str):
        """Chuyển đổi văn bản thành vector embedding"""
        return self.embedder.encode([text])[0].tolist()

    def add_ddl(self, ddl: str, **kwargs) -> str:
        """Thêm DDL (Data Definition Language) vào knowledge base"""
        return self._add_entry(ddl)

    def add_documentation(self, doc: str, **kwargs) -> str:
        """Thêm tài liệu vào knowledge base"""
        return self._add_entry(doc)

    def add_question_sql(self, question: str, sql: str, **kwargs) -> str:
        """Thêm cặp câu hỏi-SQL vào knowledge base"""
        return self._add_entry(f"{question} => {sql}")

    def _add_entry(self, text: str) -> str:
        """Thêm entry mới vào vector database"""
        emb = self._embed(text)  # Tạo embedding
        id_str = str(uuid.uuid4())  # Tạo ID duy nhất
        self.collection.insert([[id_str], [text], [emb]])  # Lưu vào collection
        return id_str

    def get_related_ddl(self, question: str, **kwargs) -> list:
        """Tìm DDL liên quan đến câu hỏi"""
        return self._search(question)

    def get_related_documentation(self, question: str, **kwargs) -> list:
        """Tìm tài liệu liên quan đến câu hỏi"""
        return self._search(question)

    def get_similar_question_sql(self, question: str, **kwargs) -> list:
        """Tìm câu hỏi-SQL tương tự"""
        return self._search(question)

    def _search(self, question: str) -> list:
        """Tìm kiếm vector similarity trong database"""
        emb = self._embed(question)  # Tạo embedding cho câu hỏi
        results = self.collection.search(
            data=[emb],
            anns_field="embedding",
            param={"metric_type": "L2", "params": {"nprobe": 10}},
            limit=3,  # Lấy top 3 kết quả
            output_fields=["text"]
        )
        return [hit.entity.value_of_field("text") for hit in results[0]]

    def generate_embedding(self, text: str) -> list:
        return self._embed(text)

    def get_training_data(self) -> pd.DataFrame:
        """Lấy tất cả training data từ vector database"""
        try:
            # Lấy tất cả dữ liệu từ collection
            results = self.collection.query(
                expr="id != ''",  # Lấy tất cả records
                output_fields=["id", "text"]
            )
            
            if results:
                # Chuyển đổi thành DataFrame
                data = []
                for result in results:
                    text = result.get('text', '')
                    # Phân tích text để tách question và sql nếu có
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
            else:
                return pd.DataFrame()
                
        except Exception as e:
            print(f"Error getting training data from Milvus: {e}")
            return pd.DataFrame()

    def remove_training_data(self, id: str) -> bool:
        """Xóa training data theo ID"""
        try:
            self.collection.delete(f"id == '{id}'")
            return True
        except Exception as e:
            print(f"Error removing training data: {e}")
            return False
