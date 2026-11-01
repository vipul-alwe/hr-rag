from app.neo4j_db import driver


def _run_query(query, **params):
    with driver.session() as session:
        result = session.run(query, **params)
        return [record.data() for record in result]


# ============================================================
# EMPLOYEE LOOKUP
# ============================================================

def find_employee(employee_name):
    query = """
    MATCH (e:Employee)
    WHERE toLower(e.name) = toLower($employee_name)
    RETURN
        e.id AS id,
        e.name AS name,
        e.designation AS designation,
        e.department AS department,
        e.team AS team,
        e.email AS email
    """

    results = _run_query(
        query,
        employee_name=employee_name
    )

    return results[0] if results else None


# ============================================================
# DIRECT MANAGER
# ============================================================

def get_manager(employee_name):
    query = """
    MATCH (e:Employee)-[:REPORTS_TO]->(m:Employee)
    WHERE toLower(e.name) = toLower($employee_name)
    RETURN
        m.id AS id,
        m.name AS name,
        m.designation AS designation,
        m.department AS department,
        m.team AS team
    """

    results = _run_query(
        query,
        employee_name=employee_name
    )

    return results[0] if results else None


# ============================================================
# DIRECT REPORTS
# ============================================================

def get_direct_reports(employee_name):
    query = """
    MATCH (e:Employee)-[:REPORTS_TO]->(m:Employee)
    WHERE toLower(m.name) = toLower($employee_name)
    RETURN
        e.id AS id,
        e.name AS name,
        e.designation AS designation,
        e.department AS department,
        e.team AS team
    ORDER BY e.name
    """

    return _run_query(
        query,
        employee_name=employee_name
    )


# ============================================================
# MANAGEMENT CHAIN
# ============================================================

def get_management_chain(employee_name):
    query = """
    MATCH path =
        (e:Employee)-[:REPORTS_TO*1..]->(manager:Employee)

    WHERE toLower(e.name) = toLower($employee_name)

    WITH manager, length(path) AS level

    RETURN
        manager.id AS id,
        manager.name AS name,
        manager.designation AS designation,
        manager.department AS department,
        manager.team AS team,
        level

    ORDER BY level
    """

    return _run_query(
        query,
        employee_name=employee_name
    )


# ============================================================
# TEAM MEMBERS
# ============================================================

def get_team_members(employee_name):
    query = """
    MATCH (e:Employee)
    WHERE toLower(e.name) = toLower($employee_name)

    MATCH (member:Employee)
    WHERE member.client_id = e.client_id
      AND member.department = e.department
      AND member.team = e.team

    RETURN
        member.id AS id,
        member.name AS name,
        member.designation AS designation,
        member.department AS department,
        member.team AS team
    ORDER BY member.name
    """

    return _run_query(
        query,
        employee_name=employee_name
    )


# ============================================================
# DEPARTMENT MEMBERS
# ============================================================

def get_department_members(department):
    query = """
    MATCH (e:Employee)
    WHERE toLower(e.department) = toLower($department)

    RETURN
        e.id AS id,
        e.name AS name,
        e.designation AS designation,
        e.department AS department,
        e.team AS team
    ORDER BY e.team, e.name
    """

    return _run_query(
        query,
        department=department
    )


# ============================================================
# ORG SUBTREE
# ============================================================

def get_org_subtree(employee_name):
    query = """
    MATCH path =
        (employee:Employee)-[:REPORTS_TO*1..]->(manager:Employee)

    WHERE toLower(manager.name) = toLower($employee_name)

    WITH employee, length(path) AS level

    RETURN DISTINCT
        employee.id AS id,
        employee.name AS name,
        employee.designation AS designation,
        employee.department AS department,
        employee.team AS team,
        level

    ORDER BY level, employee.name
    """

    return _run_query(
        query,
        employee_name=employee_name
    )


# ============================================================
# FORMAT ORG RESULTS
# ============================================================

def format_org_result(intent, employee_name, result):

    if intent == "org_manager":

        if not result:
            return (
                f"No manager information was found for "
                f"{employee_name}."
            )

        return (
            f"Employee: {employee_name}\n"
            f"Direct Manager: {result['name']}\n"
            f"Manager Designation: {result['designation']}\n"
            f"Manager Department: {result['department']}"
        )

    if intent == "org_reports":

        if not result:
            return (
                f"No direct reports were found for "
                f"{employee_name}."
            )

        lines = [
            f"Direct reports to {employee_name}:"
        ]

        for employee in result:
            team = employee["team"]

            team_text = (
                f", {team}"
                if team
                else ""
            )

            lines.append(
                f"- {employee['name']} — "
                f"{employee['designation']} "
                f"({employee['department']}{team_text})"
            )

        return "\n".join(lines)

    if intent == "org_team":

        if not result:
            return (
                f"No team members were found for "
                f"{employee_name}."
            )

        lines = [
            f"Team members of {employee_name}:"
        ]

        for employee in result:
            lines.append(
                f"- {employee['name']} — "
                f"{employee['designation']}"
            )

        return "\n".join(lines)

    if intent == "org_chain":

        if not result:
            return (
                f"No management chain was found for "
                f"{employee_name}."
            )

        lines = [
            f"Management chain for {employee_name}:"
        ]

        for manager in result:
            lines.append(
                f"- Level {manager['level']}: "
                f"{manager['name']} — "
                f"{manager['designation']}"
            )

        return "\n".join(lines)

    if intent == "org_subtree":

        if not result:
            return (
                f"No employees were found underneath "
                f"{employee_name}."
            )

        lines = [
            f"Organizational subtree under {employee_name}:"
        ]

        for employee in result:
            lines.append(
                f"- Level {employee['level']}: "
                f"{employee['name']} — "
                f"{employee['designation']}"
            )

        return "\n".join(lines)

    return "No organizational information was found."