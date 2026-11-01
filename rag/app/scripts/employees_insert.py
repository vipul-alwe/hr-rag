import pandas as pd
import psycopg2
import uuid

conn = psycopg2.connect(
    host="localhost",
    database="ragdb",
    user="postgres",
    password="postgres",
    port=5432
)

cur = conn.cursor()

df = pd.read_excel("employees.xlsx")

# normalize column names
df.columns = [
    c.strip().lower()
    for c in df.columns
]

for _, row in df.iterrows():

    employee_name = row.get("emp name")
    designation = row.get("designation")
    department = row.get("department")
    email = row.get("email id")

    # convert NA to NULL
    if pd.isna(email) or email == "NA":
        email = None

    # optional AI / manual summaries
    employee_context = None

    cur.execute(
        """
        INSERT INTO employeesdata
        (
            id,
            client_id,
            employee_name,
            designation,
            department,
            email,
            employee_context
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
        """,
        (
            str(uuid.uuid4()),
            "oml",
            employee_name,
            designation,
            department,
            email,
            employee_context
        )
    )

conn.commit()

cur.close()
conn.close()

print("Employees imported successfully.")