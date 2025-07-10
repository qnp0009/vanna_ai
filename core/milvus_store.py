from vanna.base import VannaBase
from sentence_transformers import SentenceTransformer
import pandas as pd
import uuid
import json
import os

class MilvusVectorDB(VannaBase):
    """
    Vector database implementation using embedded storage for Vanna AI
    Store and search vectors for Vanna's knowledge base
    """
    def __init__(self, config=None):
        # Initialize embedder
        self.collection_name = "vanna_knowledge"
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")  # Embedding model
        
        # Use simple file-based storage instead of Milvus server
        self.storage_file = "training_data/vector_store.json"
        self.vectors = []
        self._load_vectors()

    def _load_vectors(self):
        """Load vectors from file storage"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    self.vectors = json.load(f)
            except Exception as e:
                print(f"Error loading vectors: {e}")
                self.vectors = []

    def _save_vectors(self):
        """Save vectors to file storage"""
        os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.vectors, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving vectors: {e}")

    def _embed(self, text: str):
        """Convert text to vector embedding"""
        return self.embedder.encode([text])[0].tolist()

    def _cosine_similarity(self, vec1, vec2):
        """Calculate cosine similarity between two vectors"""
        import numpy as np
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    def add_ddl(self, ddl: str, **kwargs) -> str:
        """Add DDL (Data Definition Language) to knowledge base"""
        return self._add_entry(ddl, "ddl")

    def add_documentation(self, doc: str, **kwargs) -> str:
        """Add documentation to knowledge base"""
        return self._add_entry(doc, "documentation")

    def add_question_sql(self, question: str, sql: str, **kwargs) -> str:
        """Add question-SQL pair to knowledge base"""
        return self._add_entry(f"{question} => {sql}", "question_sql")

    def _add_entry(self, text: str, entry_type: str = "text") -> str:
        """Add new entry to vector database"""
        emb = self._embed(text)  # Create embedding
        id_str = str(uuid.uuid4())  # Create unique ID
        
        entry = {
            "id": id_str,
            "text": text,
            "embedding": emb,
            "type": entry_type
        }
        
        self.vectors.append(entry)
        self._save_vectors()
        return id_str

    def get_related_ddl(self, question: str, **kwargs) -> list:
        """Find DDL related to the question"""
        return self._search(question, "ddl")

    def get_related_documentation(self, question: str, **kwargs) -> list:
        """Find documentation related to the question"""
        return self._search(question, "documentation")

    def get_similar_question_sql(self, question: str, **kwargs) -> list:
        """Find similar question-SQL pairs"""
        return self._search(question, "question_sql")

    def _search(self, question: str, entry_type: str | None = None) -> list:
        """Search for vector similarity in the database"""
        if not self.vectors:
            return []
            
        emb = self._embed(question)  # Create embedding for the question
        
        # Calculate similarities
        similarities = []
        for entry in self.vectors:
            if entry_type and entry.get("type") != entry_type:
                continue
            similarity = self._cosine_similarity(emb, entry["embedding"])
            similarities.append((similarity, entry["text"]))
        
        # Sort by similarity and return top 3
        similarities.sort(key=lambda x: x[0], reverse=True)
        return [text for _, text in similarities[:3]]

    def generate_embedding(self, text: str) -> list:
        return self._embed(text)

    def get_training_data(self) -> pd.DataFrame:
        """Get all training data from vector database"""
        try:
            if not self.vectors:
                return pd.DataFrame()
            
            data = []
            for entry in self.vectors:
                text = entry.get('text', '')
                entry_type = entry.get('type', 'text')
                
                # Parse text to split question and sql if present
                if entry_type == 'question_sql' and ' => ' in text:
                    question, sql = text.split(' => ', 1)
                    data.append({
                        'id': entry.get('id', ''),
                        'question': question,
                        'sql': sql,
                        'type': entry_type
                    })
                else:
                    data.append({
                        'id': entry.get('id', ''),
                        'text': text,
                        'type': entry_type
                    })
            
            return pd.DataFrame(data)
                
        except Exception as e:
            print(f"Error getting training data: {e}")
            return pd.DataFrame()

    def remove_training_data(self, id: str) -> bool:
        """Delete training data by ID"""
        try:
            self.vectors = [entry for entry in self.vectors if entry.get('id') != id]
            self._save_vectors()
            return True
        except Exception as e:
            print(f"Error removing training data: {e}")
            return False
