# app/tests/system_test.py

from app.planner import plan_query
from app.neo4j_db import test_neo4j_connection
from app.tools.org_hierarchy_engine import (
    find_employee,
    get_manager,
    get_direct_reports,
    get_team_members,
    get_management_chain,
)


PASS = 0
FAIL = 0


def test(name, condition, details=""):
    global PASS, FAIL

    if condition:
        PASS += 1
        print(f"✅ PASS — {name}")
    else:
        FAIL += 1
        print(f"❌ FAIL — {name}")

        if details:
            print(f"   {details}")


def section(title):
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


# ============================================================
# 1. INFRASTRUCTURE
# ============================================================

def test_infrastructure():

    section("1. INFRASTRUCTURE")

    try:
        result = test_neo4j_connection()

        test(
            "Neo4j connection",
            result == "Neo4j connected",
            f"Returned: {result}"
        )

    except Exception as e:
        test(
            "Neo4j connection",
            False,
            str(e)
        )


# ============================================================
# 2. PLANNER
# ============================================================

def test_planner():

    section("2. PLANNER")

    cases = [
        (
            "Who does Roycin D’Souza report to?",
            "org_manager",
            "neo4j",
        ),
        (
            "Who reports to Roycin D’Souza?",
            "org_reports",
            "neo4j",
        ),
        (
            "Who is Roycin D’Souza's manager?",
            "org_manager",
            "neo4j",
        ),
        (
            "Who works under Roycin D’Souza?",
            "org_reports",
            "neo4j",
        ),
        (
            "Who is on Roycin D’Souza's team?",
            "org_team",
            "neo4j",
        ),
        (
            "What is Roycin D’Souza's management chain?",
            "org_chain",
            "neo4j",
        ),
        (
            "Who is above Roycin D’Souza?",
            "org_chain",
            "neo4j",
        ),
        (
            "What are the holidays in 2026?",
            "holiday",
            "direct",
        ),
        (
            "When is Diwali?",
            "holiday",
            "direct",
        ),
        (
            "Calculate gratuity",
            "gratuity",
            "flow",
        ),
        (
            "Hello",
            "small_talk",
            "direct",
        ),
    ]

    for query, expected_intent, expected_mode in cases:

        try:
            result = plan_query(query)

            test(
                query,
                result["intent"] == expected_intent
                and result["mode"] == expected_mode,
                f"Expected: "
                f"{expected_intent}/{expected_mode}, "
                f"Got: "
                f"{result.get('intent')}/{result.get('mode')}"
            )

        except Exception as e:

            test(
                query,
                False,
                str(e)
            )


# ============================================================
# 3. EMPLOYEE LOOKUP
# ============================================================

def test_employee_lookup():

    section("3. EMPLOYEE LOOKUP")

    try:

        employee = find_employee("Roycin D’Souza")

        test(
            "Find Roycin D’Souza",
            employee is not None
            and employee["name"] == "Roycin D’Souza",
            f"Result: {employee}"
        )

    except Exception as e:

        test(
            "Find Roycin D’Souza",
            False,
            str(e)
        )

    try:

        employee = find_employee("roycin d’souza")

        test(
            "Case-insensitive employee lookup",
            employee is not None
            and employee["name"] == "Roycin D’Souza",
            f"Result: {employee}"
        )

    except Exception as e:

        test(
            "Case-insensitive employee lookup",
            False,
            str(e)
        )

    try:

        employee = find_employee("Does Not Exist")

        test(
            "Unknown employee returns None",
            employee is None,
            f"Result: {employee}"
        )

    except Exception as e:

        test(
            "Unknown employee returns None",
            False,
            str(e)
        )


# ============================================================
# 4. MANAGER RELATIONSHIPS
# ============================================================

def test_manager_relationships():

    section("4. MANAGER RELATIONSHIPS")

    try:

        manager = get_manager("Roycin D’Souza")

        test(
            "Roycin's manager is Devarshi Shah",
            manager is not None
            and manager["name"] == "Devarshi Shah",
            f"Result: {manager}"
        )

    except Exception as e:

        test(
            "Roycin's manager is Devarshi Shah",
            False,
            str(e)
        )


# ============================================================
# 5. DIRECT REPORTS
# ============================================================

def test_direct_reports():

    section("5. DIRECT REPORTS")

    expected = {
        "Aiswarya Parameshwar",
        "Anshu Choudhary",
        "Gibson Sequeira",
        "Krishi Shukla",
        "Loma Sisodia",
        "Natasha Kharadi",
        "Navvya Bhutani",
        "Roshni Shah",
        "Sakshi Chugh",
        "Zainab Arif",
        "Zeel Desai",
    }

    try:

        reports = get_direct_reports("Roycin D’Souza")

        actual = {
            employee["name"]
            for employee in reports
        }

        test(
            "Roycin has 11 direct reports",
            len(reports) == 11,
            f"Found: {len(reports)}"
        )

        test(
            "Roycin's direct reports are correct",
            actual == expected,
            f"Actual: {sorted(actual)}"
        )

    except Exception as e:

        test(
            "Roycin direct reports query",
            False,
            str(e)
        )


# ============================================================
# 6. TEAM MEMBERS
# ============================================================

def test_team_members():

    section("6. TEAM MEMBERS")

    try:

        members = get_team_members("Manav Parekh")

        test(
            "Manav's team contains employees",
            len(members) > 0,
            f"Found: {len(members)}"
        )

        test(
            "Manav's team is Move Over / Creative",
            all(
                employee["department"] == "Move Over"
                and employee["team"] == "Creative"
                for employee in members
            ),
            f"Teams found: "
            f"{set((x['department'], x['team']) for x in members)}"
        )

    except Exception as e:

        test(
            "Manav team query",
            False,
            str(e)
        )


# ============================================================
# 7. MANAGEMENT CHAIN
# ============================================================

def test_management_chain():

    section("7. MANAGEMENT CHAIN")

    try:

        chain = get_management_chain(
            "Roycin D’Souza"
        )

        names = [
            manager["name"]
            for manager in chain
        ]

        test(
            "Roycin management chain",
            names == [
                "Devarshi Shah",
                "Tusharr Kumar",
            ],
            f"Actual chain: {names}"
        )

    except Exception as e:

        test(
            "Roycin management chain",
            False,
            str(e)
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("============================================================")
    print("HR RAG SYSTEM TEST")
    print("============================================================")

    test_infrastructure()
    test_planner()
    test_employee_lookup()
    test_manager_relationships()
    test_direct_reports()
    test_team_members()
    test_management_chain()

    print()
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    print(f"PASS: {PASS}")
    print(f"FAIL: {FAIL}")
    print(f"TOTAL: {PASS + FAIL}")

    if FAIL == 0:
        print()
        print("🎉 ALL TESTS PASSED")
    else:
        print()
        print("⚠️ SOME TESTS FAILED")


if __name__ == "__main__":
    main()
    