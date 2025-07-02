import os
import requests

class VannaBase:
    def __init__(self):
        self.training_data = []
    
    # Xử lý SQL đầu ra nếu cần làm sạch
    def generate_sql(self, question: str, **kwargs) -> str:
        raise NotImplementedError("Subclasses should implement generate_sql")
    
    # Huấn luyện từ SQL mẫu hoặc DDL
    def train(self, **kwargs):
        if "question" in kwargs and "sql" in kwargs:
            # Huấn luyện bằng câu hỏi và câu SQL
            self.add_training_pair(question=kwargs["question"], sql=kwargs["sql"])
        elif "ddl" in kwargs:
            # Huấn luyện bằng DDL (câu lệnh CREATE TABLE)
            self.add_ddl(kwargs["ddl"])
        elif "documentation" in kwargs:
            self.add_documentation(kwargs["documentation"])
        else:
            raise ValueError("train() requires either (question + sql), ddl, or documentation")

    # Thêm tài liệu mô tả
    def add_documentation(self, doc: str):
        self.add_text(doc)
    
    def add_training_pair(self, question, sql):
        # lưu cặp câu hỏi - câu SQL vào training_data
        self.training_data.append({"question": question, "sql": sql})

    def add_ddl(self, ddl):
        # Dummy implementation
        pass

    def add_text(self, text):
        # Dummy implementation
        pass
