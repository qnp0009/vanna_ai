from core.my_agent import MyVanna
from config.config import vn

# Kết nối đến database
vn.connect_to_sqlite("db/DIEM.db")

# Lấy training data dưới dạng DataFrame
df = vn.get_training_data()

# Xoá từng dòng bằng id
for _, row in df.iterrows():
    vn.remove_training_data(row['id'])

# Kiểm tra lại
df = vn.get_training_data()
print(df)  # nên rỗng
