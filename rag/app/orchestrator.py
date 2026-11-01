from app.planner import plan_query
from app.core.retriever import retrieve_context
from app.core.generator import generate_answer
from app.tools.employee_engine import process_employee_query
from app.tools.holiday_engine import process_holiday_question
from app.tools.org_hierarchy_engine import (
    find_employee,
    get_manager,
    get_direct_reports,
    get_team_members,
    get_management_chain,
    get_org_subtree,
    format_org_result,
)
from app.memory import add_message, get_history
from app.state_manager import (
    get_state,
    update_state,
    set_flow,
    get_flow,
    clear_flow,
)

import requests
import json
import re


# =============================
# THINK
# =============================

def think(query: str, history):

    history_text = ""

    if history:
        recent = history[-6:]

        history_text = "\n".join(
            f"{m['role']}: {m['content']}"
            for m in recent
        )

    prompt = f"""
Analyze conversation and return STRICT JSON:

Fields:
- intent
- policy
- entity (ONLY if explicitly mentioned, else null)
- topic
- use_history (none | partial | full)
- confidence (0-1)

Conversation:
{history_text}

Query:
{query}

Return JSON only.
"""

    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "mistral-nemo:latest",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0
                }
            }
        )

        return json.loads(
            res.json()["response"]
        )

    except Exception:
        return {
            "intent": None,
            "policy": None,
            "entity": None,
            "topic": None,
            "use_history": "none",
            "confidence": 0.0
        }


# =============================
# SMALL TALK
# =============================

def handle_small_talk(query: str):

    q = query.lower().strip()

    greetings = {
        "hi",
        "hello",
        "hey",
        "hui",
        "good morning",
        "good afternoon",
        "good evening",
        "bello",
        "hey girly",
        "hey man",
        "hey buddy",
        "hey there"
    }

    if q in greetings:
        return True, None

    for g in greetings:

        if q.startswith(g):

            remaining = q[len(g):].strip()

            if remaining:
                return False, remaining

            return True, None

    return False, None


# =============================
# EMPLOYEE DETECTION
# =============================

def is_employee_query(query: str):

    q = query.lower()

    return any([
        q.startswith("who is"),
        q.startswith("who leads"),
        q.startswith("who lead"),
        "team" in q,
        "department" in q
    ])


# =============================
# FOLLOW-UP
# =============================

def resolve_followup(query, state):

    q = query.lower()
    topic = state.get("topic")

    if not topic:
        return query

    if "that team" in q or "this team" in q:

        return (
            q.replace("that team", topic)
             .replace("this team", topic)
        )

    if any(
        x in q
        for x in [
            "after that",
            "then",
            "next",
            "after this"
        ]
    ):

        if topic and "holiday" in topic.lower():
            return "next holiday after previous holiday"

    return query


# =============================
# GRATUITY INPUT
# =============================

def extract_gratuity_inputs(query: str):

    q = query.lower()

    years = None
    salary = None

    y = re.search(
        r'(\d+)\s*year',
        q
    )

    if y:
        years = y.group(1)

    s = re.search(
        r'(\d{4,7})',
        q
    )

    if s:
        salary = s.group(1)

    return years, salary


# =============================
# ORG ENTITY EXTRACTION
# =============================

def extract_org_employee_name(
    query: str,
    entity: str | None = None
):
    """
    Try to resolve an employee mentioned in an
    organizational question.

    First tries the entity produced by THINK.

    If that fails, searches all Employee nodes and
    checks whether a known employee name appears
    in the query.
    """

    if entity:

        employee = find_employee(entity)

        if employee:
            return employee

    # Ask Neo4j for all employee names.

    from app.tools.org_hierarchy_engine import _run_query

    results = _run_query("""
        MATCH (e:Employee)
        RETURN e.name AS name
        ORDER BY size(e.name) DESC
    """)

    query_normalized = query.lower()

    for row in results:

        name = row["name"]

        if name.lower() in query_normalized:
            employee = find_employee(name)

            if employee:
                return employee

    return None


# =============================
# ORG QUERY HANDLER
# =============================

def process_org_query(
    query: str,
    intent: str,
    entity: str | None
):
    """
    Execute the appropriate deterministic Neo4j
    operation.
    """

    employee = extract_org_employee_name(
        query,
        entity
    )

    if not employee:

        return (
            "I couldn't identify the employee you're "
            "asking about."
        )

    employee_name = employee["name"]

    print(
        "🏢 ORG EMPLOYEE:",
        employee_name
    )

    if intent == "org_manager":

        result = get_manager(
            employee_name
        )

        return format_org_result(
            "org_manager",
            employee_name,
            result
        )

    if intent == "org_reports":

        result = get_direct_reports(
            employee_name
        )

        return format_org_result(
            "org_reports",
            employee_name,
            result
        )

    if intent == "org_team":

        result = get_team_members(
            employee_name
        )

        return format_org_result(
            "org_team",
            employee_name,
            result
        )

    if intent == "org_chain":

        result = get_management_chain(
            employee_name
        )

        return format_org_result(
            "org_chain",
            employee_name,
            result
        )

    if intent == "org_subtree":

        result = get_org_subtree(
            employee_name
        )

        return format_org_result(
            "org_subtree",
            employee_name,
            result
        )

    return "No organizational information was found."


# =============================
# MAIN
# =============================

def ask(
    client_id: str,
    query: str,
    current_date: str
):

    print("\n==============================")
    print("🚀 NEW REQUEST")
    print("==============================")

    print("\n--- RAW QUERY ---")
    print(query)

    # =============================
    # SMALL TALK
    # =============================

    is_greeting, stripped = handle_small_talk(
        query
    )

    if is_greeting:
        return "Hello, how can I help you today?"

    if stripped:
        query = stripped

    add_message(
        client_id,
        "user",
        query
    )

    history = get_history(
        client_id
    )

    state = get_state(
        client_id
    )

    # =============================
    # GRATUITY FLOW
    # =============================

    flow = get_flow(
        client_id
    )

    if flow and flow["type"] == "gratuity":

        from app.tools.gratuity_engine import (
            process_gratuity
        )

        data = flow["data"]

        if not data.get("years"):

            data["years"] = query

            set_flow(
                client_id,
                flow
            )

            return (
                "Please provide last drawn "
                "basic salary."
            )

        if not data.get("salary"):

            data["salary"] = query

            answer = process_gratuity(
                data
            )

            clear_flow(
                client_id
            )

            add_message(
                client_id,
                "assistant",
                answer
            )

            return answer

    # =============================
    # THINK
    # =============================

    thought = think(
        query,
        history
    )

    state = update_state(
        client_id,
        thought
    )

    topic = state.get(
        "topic"
    )

    policy = state.get(
        "policy"
    )

    # =============================
    # FOLLOW-UP
    # =============================

    final_query = resolve_followup(
        query,
        state
    )

    print(
        "🎯 FINAL QUERY:",
        final_query
    )

    # =============================
    # ENTITY FALLBACK
    # =============================

    entity = state.get(
        "entity"
    )

    print(
        "🧠 STATE ENTITY (before):",
        entity
    )

    if not entity:

        q = final_query.lower()

        if q.startswith("who is"):

            entity = (
                final_query
                .replace(
                    "who is",
                    "",
                    1
                )
                .strip()
            )

        elif q.startswith("who leads"):

            entity = (
                final_query
                .replace(
                    "who leads",
                    "",
                    1
                )
                .strip()
            )

        elif q.startswith("who lead"):

            entity = (
                final_query
                .replace(
                    "who lead",
                    "",
                    1
                )
                .strip()
            )

        if entity:

            print(
                "🔁 ENTITY FALLBACK:",
                entity
            )

            state["entity"] = entity

    print(
        "🚨 FINAL ENTITY:",
        entity
    )

    # =============================
    # PLANNER
    # =============================

    plan = plan_query(
        final_query
    )

    print(
        "🧭 PLAN:",
        plan
    )

    # =============================
    # HOLIDAY
    # =============================

    if plan["intent"] == "holiday":

        context = retrieve_context(
            client_id,
            final_query
        )

        answer = process_holiday_question(
            documents=context,
            query=final_query,
            current_date=current_date
        )

        add_message(
            client_id,
            "assistant",
            answer
        )

        return answer

    # =============================
    # GRATUITY
    # =============================

    if plan["intent"] == "gratuity":

        years, salary = (
            extract_gratuity_inputs(
                final_query
            )
        )

        from app.tools.gratuity_engine import (
            process_gratuity
        )

        if years and salary:

            answer = process_gratuity({
                "years": years,
                "salary": salary
            })

            add_message(
                client_id,
                "assistant",
                answer
            )

            return answer

        set_flow(
            client_id,
            {
                "type": "gratuity",
                "data": {}
            }
        )

        return "Please provide years of service."

    # =============================
    # ORG HIERARCHY / NEO4J
    # =============================

    if plan["intent"] in {
        "org_manager",
        "org_reports",
        "org_team",
        "org_chain",
        "org_subtree",
    }:

        org_context = process_org_query(
            final_query,
            plan["intent"],
            entity
        )

        context_chunks = [
            "Organizational Information:\n"
            + org_context
        ]

        answer = generate_answer(
            query=final_query,
            context_chunks=context_chunks,
            history=history,
            current_date=current_date,
            state=state
        )

        add_message(
            client_id,
            "assistant",
            answer
        )

        return answer

    # =============================
    # EMPLOYEE CONTEXT
    # =============================

    employee_chunks = []

    if is_employee_query(
        final_query
    ):

        try:

            employee_data = (
                process_employee_query(
                    client_id,
                    final_query
                )
            )

            if employee_data:

                print(
                    "👤 EMPLOYEE DATA FOUND"
                )

                if (
                    "PRIMARY ROLE CONTEXT:"
                    in employee_data
                ):

                    basic, context = (
                        employee_data.split(
                            "PRIMARY ROLE CONTEXT:",
                            1
                        )
                    )

                else:

                    basic = employee_data
                    context = ""

                employee_chunks = [
                    f"Employee Basic Info:\n{basic}",
                    f"Employee Role Context:\n{context}"
                ]

        except Exception as e:

            print(
                "Employee error:",
                e
            )

    # =============================
    # RETRIEVER
    # =============================

    policy_hint = (
        policy.lower()
        if policy
        else None
    )

    print(
        "📡 CALLING RETRIEVER WITH ENTITY:",
        entity
    )

    rag_context = retrieve_context(
        client_id,
        final_query,
        policy_hint=policy_hint,
        entity=entity
    )

    # =============================
    # CONTEXT MERGE
    # =============================

    context_chunks = []

    if employee_chunks:

        context_chunks.extend(
            employee_chunks
        )

    if rag_context:

        context_chunks.append(
            "Additional Context:\n"
            + "\n\n".join(
                rag_context[:6]
            )
        )

    if not context_chunks:

        return (
            "This is not specified in the "
            "available information."
        )

    # =============================
    # GENERATE
    # =============================

    answer = generate_answer(
        query=final_query,
        context_chunks=context_chunks,
        history=history,
        current_date=current_date,
        state=state
    )

    add_message(
        client_id,
        "assistant",
        answer
    )

    return answer