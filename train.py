from my_agent import MyVanna, vn

vn.connect_to_sqlite("db/sales.db")

# 1. Lấy DDL từ DB SQLite (tự động)
df_ddl = vn.run_sql("SELECT type, sql FROM sqlite_master WHERE sql IS NOT NULL")
for ddl in df_ddl['sql'].to_list():
    vn.train(ddl=ddl)

# 2. Huấn luyện với câu hỏi mẫu + SQL
# Tổng doanh thu của từng sản phẩm
vn.train(sql="""
SELECT product, SUM(revenue) as total_revenue
FROM sales
GROUP BY product
ORDER BY total_revenue DESC
""")

# Số lượng sản phẩm đã bán (tổng quantity) theo ngày
vn.train(sql="""
SELECT date, SUM(quantity) as total_quantity
FROM sales
GROUP BY date
ORDER BY date
""")

# Sản phẩm có doanh thu trung bình cao nhất
vn.train(sql="""
SELECT product, AVG(revenue) as avg_revenue
FROM sales
GROUP BY product
ORDER BY avg_revenue DESC
LIMIT 1
""")

# Tổng doanh thu trong tháng 5 năm 2024
vn.train(sql="""
SELECT SUM(revenue) as total_may_revenue
FROM sales
WHERE strftime('%Y-%m', date) = '2024-05'
""")

# Tổng số giao dịch trong hệ thống
vn.train(sql="""
SELECT COUNT(*) as total_transactions
FROM sales
""")


# 3. Thêm giải thích (doc)
vn.train(documentation="""
- Mỗi hàng trong bảng sales là một giao dịch bán hàng.
- Cột 'quantity' là số lượng sản phẩm bán được trong mỗi giao dịch.
- Cột 'revenue' là doanh thu tương ứng cho giao dịch đó.
- Cột 'date' có định dạng YYYY-MM-DD.
- 'Doanh thu trung bình' nghĩa là trung bình của revenue theo nhóm.
- 'Tổng doanh thu' là tổng cộng của cột revenue.
""")

# 4. Kiểm tra dữ liệu huấn luyện
df = vn.get_training_data()
print(df)

# 5. Xoá nếu cần
vn.remove_training_data(id='1-ddl')

