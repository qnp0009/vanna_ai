from core.my_agent import MyVanna
from config.config import vn

vn.connect_to_sqlite("db/DIEM.db")
vn.load_training_data()

while True:
    prompt = input("Nhập câu hỏi của bạn: ")
    if prompt.lower() in ("exit", "quit"):
        break

    # Gọi Vanna trả lời
    sql, df, question = vn.ask(prompt)
    
    print("\n=== KẾT QUẢ ===")
    if sql is None:
        print("❌ Không thể tạo SQL do lỗi server LLM")
        print("💡 Hãy thử lại sau hoặc đổi sang LLM service khác")
    else:
        print(f"📝 SQL được tạo: {sql}")
        
        if df is not None and not df.empty:
            print(f"📊 Kết quả ({len(df)} dòng):")
            print(df.head(10))  # Hiển thị 10 dòng đầu
        elif df is not None and df.empty:
            print("📊 Không có dữ liệu trả về")
        else:
            print("❌ Không thể thực thi SQL")
    
    print("\n" + "="*50 + "\n")
