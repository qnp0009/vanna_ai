from core.my_agent import MyVanna
from config.config import vn
vn.connect_to_sqlite("db/DIEM.db")

# 1. Lấy DDL từ DB SQLite (tự động)
df_ddl = vn.run_sql("SELECT type, sql FROM sqlite_master WHERE sql IS NOT NULL")
for ddl in df_ddl['sql'].to_list():
    vn.train(ddl=ddl)

# 2. Huấn luyện với câu hỏi mẫu + SQL (có thêm Số BD khi liệt kê)
vn.train(question="Danh sách tất cả học sinh và điểm của họ", sql="SELECT `Số BD`, `Điểm` FROM DIEM")
vn.train(question="Ai có điểm cao nhất?", sql="SELECT `Số BD`, `Điểm` FROM DIEM ORDER BY `Điểm` DESC LIMIT 1")
vn.train(question="Có bao nhiêu học sinh?", sql="SELECT COUNT(*) FROM DIEM")
vn.train(question="Trung bình điểm là bao nhiêu?", sql="SELECT AVG(`Điểm`) FROM DIEM")
vn.train(question="Những học sinh nào có điểm dưới 5?", sql="SELECT `Số BD`, `Điểm` FROM DIEM WHERE `Điểm` < 5")
vn.train(question="Thống kê số học sinh theo từng phòng thi", sql="SELECT `Phòng thi`, COUNT(*) as `Số học sinh` FROM DIEM GROUP BY `Phòng thi`")
vn.train(question="Số học sinh thi tại mỗi địa điểm", sql="SELECT `Địa điểm thi`, COUNT(*) FROM DIEM GROUP BY `Địa điểm thi`")
vn.train(question="Tổng số câu đúng trung bình của học sinh", sql="SELECT AVG(`ĐÚNG`) FROM DIEM")
vn.train(question="Liệt kê học sinh sai trên 20 câu", sql="SELECT `Số BD`, `SAI` FROM DIEM WHERE `SAI` > 20")
vn.train(question="Danh sách học sinh cùng mã đề 209", sql="SELECT `Số BD`, `Mã đề` FROM DIEM WHERE `Mã đề` = 209")



# 3. Thêm giải thích (doc)
vn.train(documentation="""
Bảng DIEM lưu trữ thông tin kết quả thi của học sinh, với các cột:
- Họ và tên: Tên học sinh
- Ngày sinh: Ngày sinh của học sinh
- Phòng thi: Số phòng thi
- Địa điểm thi: Nơi học sinh thi
- Số BD: Số báo danh
- Mã đề: Mã đề thi
- Điểm: Số điểm đạt được
- Ghi chú: Các ghi chú thêm (nếu có)
- ĐÚNG: Số câu đúng
- SAI: Số câu sai
- M HS: Mã học sinh (nội bộ)

Các câu hỏi thường liên quan đến thống kê điểm, phân tích kết quả theo phòng thi hoặc địa điểm, và tìm học sinh có điểm cao/thấp.
""")


# 4. Kiểm tra dữ liệu huấn luyện
df = vn.get_training_data()
print(df)

