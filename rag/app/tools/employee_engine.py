from app.db import get_cursor
from rapidfuzz import fuzz


# =============================
# NORMALIZATION
# =============================

def normalize(text: str):

    if not text:
        return ""

    return (
        text.lower()
        .strip()
        .replace("&", "and")
    )


# =============================
# FETCH ALL EMPLOYEES
# =============================

def fetch_all_employees(client_id: str):

    with get_cursor() as cur:

        cur.execute(
            """
            SELECT
                employee_name,
                designation,
                department,
                email,
                employee_context
            FROM employees
            WHERE client_id = %s
            """,
            (client_id,)
        )

        rows = cur.fetchall()

    employees = []

    for row in rows:
        employees.append({
            "employee_name": row[0],
            "designation": row[1],
            "department": row[2],
            "email": row[3],
            "employee_context": row[4]
        })

    return employees


# =============================
# FORMAT EMPLOYEE
# =============================

def format_employee(employee):

    lines = []

    lines.append(employee["employee_name"])

    if employee.get("designation"):
        lines.append(f"Designation: {employee['designation']}")

    if employee.get("department"):
        lines.append(f"Department: {employee['department']}")

    if employee.get("email"):
        lines.append(f"Email: {employee['email']}")

    if employee.get("employee_context"):
        lines.append("\n--- ROLE & RESPONSIBILITIES ---")
        lines.append(employee["employee_context"])

    return "\n".join(lines)


# =============================
# NAME MATCHING
# =============================

def search_employee_by_name(employees, query: str):

    q = normalize(query)
    ranked_matches = []

    for emp in employees:

        employee_name = normalize(emp["employee_name"])

        if not employee_name:
            continue

        score = 0

        full_score = fuzz.token_sort_ratio(q, employee_name)
        score += full_score * 3

        query_parts = q.split()
        employee_parts = employee_name.split()

        if employee_parts:
            employee_first = employee_parts[0]

            for qpart in query_parts:
                first_score = fuzz.ratio(qpart, employee_first)
                score += first_score * 5

        if len(employee_parts) > 1:
            employee_last = employee_parts[-1]

            for qpart in query_parts:
                last_score = fuzz.ratio(qpart, employee_last)
                score += last_score * 1

        # leadership boost
        designation = normalize(emp.get("designation", ""))

        leadership_terms = [
            "ceo", "cfo", "cbo", "chief",
            "director", "head", "vp", "vice president"
        ]

        for term in leadership_terms:
            if term in designation:
                score += 120

        ranked_matches.append({
            "employee": emp,
            "score": score
        })

    ranked_matches.sort(key=lambda x: x["score"], reverse=True)

    if not ranked_matches:
        return []

    best_score = ranked_matches[0]["score"]
    final_matches = []

    for item in ranked_matches:

        if item["score"] < 300:
            continue

        if (item["score"] / best_score) < 0.96:
            continue

        final_matches.append(item["employee"])

    return final_matches[:3]


# =============================
# ROLE MATCHING
# =============================

def search_by_role(employees, query: str):

    q = normalize(query)

    designation_aliases = {
        "ceo": ["chief executive officer", "ceo", "founder", "boss"],
        "cfo": ["chief financial officer", "cfo", "finance head", "finance"],
        "cto": ["chief technology officer", "cto", "technology", "tech lead"],
        "cgo": ["chief growth officer", "cgo", "growth"],
        "cbo": ["chief business officer", "cbo", "business head"],
        "hr": ["people team", "human resources", "hr", "people ops"],
        "management": ["management", "leadership", "leaders"]
    }

    role_matches = []

    for _, aliases in designation_aliases.items():

        if not any(alias in q for alias in aliases):
            continue

        for emp in employees:

            searchable = " ".join([
                normalize(emp.get("designation", "")),
                normalize(emp.get("department", "")),
                normalize(emp.get("employee_context", ""))
            ])

            if any(alias in searchable for alias in aliases):
                role_matches.append(emp)

    return role_matches[:5]


# =============================
# DEPARTMENT MATCHING
# =============================

def search_department(employees, query: str):

    q = normalize(query)
    department_matches = []

    for emp in employees:

        department = normalize(emp.get("department"))

        if department and department in q:
            department_matches.append(emp)

    return department_matches


# =============================
# MAIN ENGINE
# =============================

def process_employee_query(client_id: str, query: str):

    q = normalize(query)
    employees = fetch_all_employees(client_id)

    retrievals = []

    # =============================
    # NAME RETRIEVAL
    # =============================

    for emp in search_employee_by_name(employees, query):

        searchable = " ".join([
            normalize(emp.get("employee_name", "")),
            normalize(emp.get("designation", "")),
            normalize(emp.get("department", "")),
            normalize(emp.get("employee_context", ""))
        ])

        retrievals.append({
            "type": "employee",
            "score": fuzz.token_set_ratio(q, searchable),
            "employee": emp
        })

    # =============================
    # ROLE RETRIEVAL (BOOSTED)
    # =============================

    for emp in search_by_role(employees, query):

        searchable = " ".join([
            normalize(emp.get("designation", "")),
            normalize(emp.get("employee_context", ""))
        ])

        retrievals.append({
            "type": "role",
            "score": fuzz.token_set_ratio(q, searchable) + 30,  # 🔥 boost
            "employee": emp
        })

    # =============================
    # DEPARTMENT RETRIEVAL
    # =============================

    dept_matches = search_department(employees, query)

    if dept_matches:

        dept_name = normalize(dept_matches[0]["department"])

        retrievals.append({
            "type": "department",
            "score": fuzz.token_set_ratio(q, dept_name) + 25,
            "employees": dept_matches
        })

    if not retrievals:
        return None

    # =============================
    # FIX: PRIORITIZE ROLE
    # =============================

    retrievals.sort(
        key=lambda x: (
            1 if x["type"] == "role" else 0,
            x["score"]
        ),
        reverse=True
    )

    best = retrievals[0]

    # =============================
    # DEPARTMENT RESPONSE
    # =============================

    if best["type"] == "department":

        unique = {
            emp["employee_name"]: emp
            for emp in best["employees"]
        }

        dept_name = best["employees"][0]["department"]

        lines = [f"{dept_name} Team:"]

        for emp in unique.values():
            lines.append(f"- {emp['employee_name']} ({emp['designation']})")

        return "\n".join(lines)

    # =============================
    # EMPLOYEE / ROLE RESPONSE
    # =============================

    return format_employee(best["employee"])