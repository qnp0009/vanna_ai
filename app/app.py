from core.my_agent import MyVanna
from config.config import vn

vn.connect_to_sqlite("db/DIEM.db")

while True:
    prompt = input("Nhập câu hỏi của bạn: ")
    if prompt.lower() in ("exit", "quit"):
        break

    # Gọi Vanna trả lời
    answer = vn.ask(prompt)
    print("Vanna trả lời:", answer)
