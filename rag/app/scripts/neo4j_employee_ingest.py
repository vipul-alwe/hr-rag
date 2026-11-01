import os

from app.db import get_cursor
from app.neo4j_db import driver


CLIENT_ID = os.getenv(
    "HR_CLIENT_ID",
    "11111111-1111-1111-1111-111111111111"
)


def fetch_employees():
    with get_cursor() as cur:
        cur.execute("""
            SELECT
                id,
                client_id,
                employee_name,
                designation,
                department,
                email,
                phone_number,
                team,
                reports_to
            FROM employees
            WHERE client_id = %s
            ORDER BY employee_name
        """, (CLIENT_ID,))

        rows = cur.fetchall()

    employees = []

    for row in rows:
        employees.append({
            "id": str(row[0]),
            "client_id": str(row[1]),
            "name": row[2],
            "designation": row[3],
            "department": row[4],
            "email": row[5],
            "phone_number": row[6],
            "team": row[7],
            "reports_to": row[8],
        })

    return employees


def create_employee(tx, employee):
    tx.run("""
        MERGE (e:Employee {id: $id})
        SET
            e.client_id = $client_id,
            e.name = $name,
            e.designation = $designation,
            e.department = $department,
            e.email = $email,
            e.phone_number = $phone_number,
            e.team = $team,
            e.reports_to = $reports_to
    """, **employee)


def create_department(tx, employee):
    department = employee["department"]

    if not department:
        return

    tx.run("""
        MERGE (d:Department {
            key: $department_key
        })
        SET
            d.client_id = $client_id,
            d.name = $department

        WITH d

        MATCH (e:Employee {id: $employee_id})

        MERGE (e)-[:BELONGS_TO]->(d)
    """,
        department_key=f"{employee['client_id']}|{department}",
        client_id=employee["client_id"],
        department=department,
        employee_id=employee["id"],
    )


def clear_reports_to(tx):
    tx.run("""
        MATCH ()-[r:REPORTS_TO]->()
        DELETE r
    """)


def create_reports_to(tx, employee, manager):
    tx.run("""
        MATCH (employee:Employee {id: $employee_id})
        MATCH (manager:Employee {id: $manager_id})

        MERGE (employee)-[:REPORTS_TO]->(manager)
    """,
        employee_id=employee["id"],
        manager_id=manager["id"],
    )


def main():
    print("Fetching employees from PostgreSQL...")

    employees = fetch_employees()

    print(f"Found {len(employees)} employees.")

    if not employees:
        print("No employees found.")
        return

    employees_by_name = {
        employee["name"].strip(): employee
        for employee in employees
    }

    with driver.session() as session:

        print("Clearing existing REPORTS_TO relationships...")
        session.execute_write(clear_reports_to)

        print("Creating Employee nodes...")

        for employee in employees:
            session.execute_write(
                create_employee,
                employee
            )

        print("Creating Department relationships...")

        for employee in employees:
            session.execute_write(
                create_department,
                employee
            )

        print("Creating REPORTS_TO relationships...")

        created_relationships = 0
        unresolved = []

        for employee in employees:

            reports_to = employee["reports_to"]

            if not reports_to:
                continue

            manager = employees_by_name.get(
                reports_to.strip()
            )

            if not manager:
                unresolved.append(
                    (employee["name"], reports_to)
                )
                continue

            session.execute_write(
                create_reports_to,
                employee,
                manager
            )

            created_relationships += 1

    print()
    print("========================================")
    print("Neo4j employee ingestion complete")
    print("========================================")
    print(f"Employees: {len(employees)}")
    print(f"REPORTS_TO relationships: {created_relationships}")

    if unresolved:
        print()
        print("WARNING: Unresolved managers:")

        for employee_name, manager_name in unresolved:
            print(
                f"  {employee_name} -> {manager_name}"
            )


if __name__ == "__main__":
    main()