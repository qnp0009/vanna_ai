from core.my_agent import MyVanna
from config.config import vn
vn.connect_to_sqlite("db/DIEM.db")

# 1. Get DDL from SQLite DB (automatic)
print("\n=== Getting DDL statements ===")
df_ddl = vn.run_sql("SELECT type, sql FROM sqlite_master WHERE sql IS NOT NULL")
print("DDL statements found:", len(df_ddl))
for idx, row in df_ddl.iterrows():
    print(f"Type: {row['type']}, SQL: {row['sql'][:100]}...")
# 1. Training from DDL
for ddl in df_ddl['sql'].to_list():
    vn.train(ddl=ddl)

# 2. Training from sample Q&A in English using actual column names
vn.train(question="List all students and their grades", sql="SELECT `ID`, `Grade` FROM DIEM")
vn.train(question="Who has the highest grade?", sql="SELECT `ID`, `Grade` FROM DIEM ORDER BY `Grade` DESC LIMIT 1")
vn.train(question="How many students are there?", sql="SELECT COUNT(*) FROM DIEM")
vn.train(question="What is the average grade?", sql="SELECT AVG(`Grade`) FROM DIEM")
vn.train(question="Which students scored below 5?", sql="SELECT `ID`, `Grade` FROM DIEM WHERE `Grade` < 5")
vn.train(question="Number of students per exam room", sql="SELECT `Room`, COUNT(*) as `Number of Students` FROM DIEM GROUP BY `Room`")
vn.train(question="Number of students per location", sql="SELECT `Location`, COUNT(*) FROM DIEM GROUP BY `Location`")
vn.train(question="Average number of correct answers", sql="SELECT AVG(`Correct`) FROM DIEM")
vn.train(question="List students who got more than 20 wrong answers", sql="SELECT `ID`, `Wrong` FROM DIEM WHERE `Wrong` > 20")
vn.train(question="List students who took exam with ID_EXAM 209", sql="SELECT `ID`, `ID_EXAM` FROM DIEM WHERE `ID_EXAM` = 209")


# 3. Add documentation (doc)
vn.train(documentation="""
The DIEM table stores exam results of students with the following columns:
- Full Name: Name of the student
- Date of Birth: Student's birth date
- Room: Exam room number
- Location: Exam center location
- ID: Student's unique exam number
- ID_EXAM: Exam paper code
- Grade: Final exam score
- Note: Additional notes
- Correct: Number of correct answers
- Wrong: Number of wrong answers
- M HS: Internal student code

Typical queries involve analyzing grades, listing top/bottom students, or aggregating data by room or location.
""")


# 4. Check training data
print("\n=== Training data summary ===")
print("Training data in memory:", len(vn.training_data))
print("Training data content:", vn.training_data[:3] if vn.training_data else "Empty")

df = vn.get_training_data()
print("get_training_data result:", df)

vn.save_training_data()
