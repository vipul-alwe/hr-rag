"""
OML HR ASSISTANT — REAL WORLD BRUTE FORCE TEST

136 independent questions:

- Organisation / Neo4j
- HR policy / PostgreSQL + pgvector + Ollama
- Boundary questions where the assistant should avoid hallucinating

Run from:

    ~/development/ai/rag

    python -m app.tests.real_world_test

The script also writes:

    real_world_test_results.txt
    real_world_test_results.json
"""

import json
import time
from pathlib import Path

import app.orchestrator as orchestrator
from app.planner import plan_query


CLIENT_ID = "11111111-1111-1111-1111-111111111111"
CURRENT_DATE = "2026-10-09"


QUESTIONS = [

    # ============================================================
    # NEO4J / ORGANISATION
    # ============================================================

    (1, "NEO4J", "Who is Roycin D’Souza?"),
    (2, "NEO4J", "Who is Manav Parekh?"),
    (3, "NEO4J", "Who is Soumen Nath?"),
    (4, "NEO4J", "Who is Devarshi Shah?"),
    (5, "NEO4J", "Who is Ambarish Sengupta?"),
    (6, "NEO4J", "Who is Santosh Raut?"),
    (7, "NEO4J", "Who is Sudhakar Jadhav?"),
    (8, "NEO4J", "Who is Tusharr Kumar?"),
    (9, "NEO4J", "Who is Aiswarya Parameshwar?"),
    (10, "NEO4J", "Who is Anshu Choudhary?"),
    (11, "NEO4J", "Who is Gibson Sequeira?"),
    (12, "NEO4J", "Who is Krishi Shukla?"),

    (13, "NEO4J", "Who does Roycin D’Souza report to?"),
    (14, "NEO4J", "Who does Manav Parekh report to?"),
    (15, "NEO4J", "Who does Soumen Nath report to?"),
    (16, "NEO4J", "Who does Devarshi Shah report to?"),
    (17, "NEO4J", "Who does Ambarish Sengupta report to?"),
    (18, "NEO4J", "Who does Santosh Raut report to?"),
    (19, "NEO4J", "Who does Sudhakar Jadhav report to?"),
    (20, "NEO4J", "Who does Aiswarya Parameshwar report to?"),
    (21, "NEO4J", "Who does Anshu Choudhary report to?"),

    (22, "NEO4J", "Who reports to Roycin D’Souza?"),
    (23, "NEO4J", "Who reports to Manav Parekh?"),
    (24, "NEO4J", "Who reports to Soumen Nath?"),
    (25, "NEO4J", "Who reports to Devarshi Shah?"),
    (26, "NEO4J", "Who reports to Ambarish Sengupta?"),
    (27, "NEO4J", "Who reports to Santosh Raut?"),
    (28, "NEO4J", "Who reports to Sudhakar Jadhav?"),
    (29, "NEO4J", "Who reports to Tusharr Kumar?"),

    (30, "NEO4J", "Who is on Roycin D’Souza’s team?"),
    (31, "NEO4J", "Who is on Manav Parekh’s team?"),
    (32, "NEO4J", "Who is on Soumen Nath’s team?"),
    (33, "NEO4J", "Who is on Ambarish Sengupta’s team?"),

    (34, "NEO4J", "Who works with Roycin D’Souza?"),
    (35, "NEO4J", "Who works with Manav Parekh?"),
    (36, "NEO4J", "Who works with Soumen Nath?"),
    (37, "NEO4J", "Who works with Ambarish Sengupta?"),

    (38, "NEO4J", "What is Roycin D’Souza’s management chain?"),
    (39, "NEO4J", "What is Manav Parekh’s management chain?"),
    (40, "NEO4J", "What is Soumen Nath’s management chain?"),
    (41, "NEO4J", "What is Ambarish Sengupta’s management chain?"),
    (42, "NEO4J", "What is Santosh Raut’s management chain?"),
    (43, "NEO4J", "What is Aiswarya Parameshwar’s management chain?"),

    (44, "NEO4J", "Who is above Roycin D’Souza in the hierarchy?"),
    (45, "NEO4J", "Who is above Manav Parekh in the hierarchy?"),
    (46, "NEO4J", "Who is above Ambarish Sengupta in the hierarchy?"),
    (47, "NEO4J", "Who is above Santosh Raut in the hierarchy?"),

    (48, "NEO4J", "Who is under Roycin D’Souza?"),
    (49, "NEO4J", "Who is under Manav Parekh?"),
    (50, "NEO4J", "Who is under Ambarish Sengupta?"),
    (51, "NEO4J", "Who is under Santosh Raut?"),

    (52, "NEO4J", "Show everyone under Devarshi Shah."),
    (53, "NEO4J", "Show everyone under Tusharr Kumar."),

    (54, "NEO4J", "Who are the direct reports of Roycin D’Souza?"),
    (55, "NEO4J", "Who are the direct reports of Manav Parekh?"),
    (56, "NEO4J", "Who are the direct reports of Soumen Nath?"),
    (57, "NEO4J", "Who are the direct reports of Santosh Raut?"),
    (58, "NEO4J", "Who are the direct reports of Ambarish Sengupta?"),

    (59, "NEO4J", "Who is the manager of Roycin D’Souza?"),

    # ============================================================
    # LLM / RAG
    # ============================================================

    (60, "LLM", "How many casual leaves do employees get per year?"),
    (61, "LLM", "Can unused annual leave be carried forward?"),
    (62, "LLM", "Can employees encash unused leave?"),
    (63, "LLM", "Do I need manager approval before taking leave?"),
    (64, "LLM", "How do I apply for leave?"),
    (65, "LLM", "Is there a sandwich leave policy?"),
    (66, "LLM", "What exactly is sandwich leave?"),
    (67, "LLM", "Are weekends counted as leave under the sandwich rule?"),
    (68, "LLM", "Are holidays between leave days counted as leave?"),
    (69, "LLM", "What types of leave are available?"),

    (70, "LLM", "How long is maternity leave?"),
    (71, "LLM", "Who is eligible for parental leave?"),
    (72, "LLM", "Does the parental policy apply to all genders?"),
    (73, "LLM", "Does the parental policy cover adoption?"),
    (74, "LLM", "Does the parental policy cover surrogacy?"),
    (75, "LLM", "Is flexible work available under the parental policy?"),
    (76, "LLM", "Is childcare reimbursement available?"),

    (77, "LLM", "How long do I have to file a POSH complaint?"),
    (78, "LLM", "Can the POSH complaint deadline be extended?"),
    (79, "LLM", "How long does a POSH investigation take?"),
    (80, "LLM", "How quickly must management act after a POSH investigation?"),
    (81, "LLM", "What counts as sexual harassment under the POSH policy?"),
    (82, "LLM", "Who is on the POSH committee?"),
    (83, "LLM", "Who can I contact for a POSH complaint?"),
    (84, "LLM", "Is confidentiality maintained during a POSH complaint?"),
    (85, "LLM", "Does the POSH policy protect employees from retaliation?"),
    (86, "LLM", "What happens after a POSH complaint is filed?"),

    (87, "LLM", "What should I do if I experience verbal abuse at work?"),
    (88, "LLM", "How do I report racial abuse?"),
    (89, "LLM", "What should I do if someone threatens me at work?"),
    (90, "LLM", "Where can I report workplace intimidation?"),
    (91, "LLM", "Can I report non-sexual harassment under the Code of Conduct?"),
    (92, "LLM", "What are the reporting channels for Code of Conduct complaints?"),
    (93, "LLM", "What is the Code of Conduct committee?"),
    (94, "LLM", "Who are the Code of Conduct committee members?"),
    (95, "LLM", "What is the Code of Conduct complaint timeline?"),
    (96, "LLM", "Are anonymous Code of Conduct complaints accepted?"),

    (97, "LLM", "Are business trips required to be pre-approved?"),
    (98, "LLM", "Are travel expenses reimbursed?"),
    (99, "LLM", "Do I need receipts for travel reimbursement?"),
    (100, "LLM", "Are personal expenses reimbursed during business travel?"),
    (101, "LLM", "How far in advance should I request business travel?"),
    (102, "LLM", "What is the standard class of travel?"),
    (103, "LLM", "Are international travel expenses covered?"),
    (104, "LLM", "Are visa and insurance costs covered for international travel?"),
    (105, "LLM", "Can I use any hotel or transport vendor for business travel?"),
    (106, "LLM", "Are cash advances available for business travel?"),

    (107, "LLM", "What happens during employee onboarding?"),
    (108, "LLM", "What documentation is required during onboarding?"),
    (109, "LLM", "Is induction part of onboarding?"),
    (110, "LLM", "Are there 30-day onboarding check-ins?"),
    (111, "LLM", "Are there 60-day onboarding check-ins?"),
    (112, "LLM", "Are there 90-day onboarding check-ins?"),
    (113, "LLM", "Is POSH training mandatory for new employees?"),

    (114, "LLM", "What happens if company IT equipment is damaged?"),
    (115, "LLM", "What should I do if a company device is stolen?"),
    (116, "LLM", "Can employees install software on company devices?"),
    (117, "LLM", "Can employees modify company IT systems?"),
    (118, "LLM", "Are company IT systems monitored?"),
    (119, "LLM", "What happens to company assets when an employee leaves?"),

    (120, "LLM", "What are OML's core workplace conduct expectations?"),
    (121, "LLM", "What does the Code of Conduct say about confidentiality?"),
    (122, "LLM", "Are gifts or bribes allowed?"),
    (123, "LLM", "What does the policy say about conflicts of interest?"),
    (124, "LLM", "Is retaliation against someone who raises a complaint prohibited?"),
    (125, "LLM", "What happens after a Code of Conduct complaint is submitted?"),
    (126, "LLM", "What matters are excluded from the Code of Conduct grievance process?"),

    # ============================================================
    # BOUNDARY / HALLUCINATION
    # ============================================================

    (127, "LLM-BOUNDARY", "What is the employee annual bonus percentage?"),
    (128, "LLM-BOUNDARY", "What is the company's medical insurance premium?"),
    (129, "LLM-BOUNDARY", "What is the work from home salary allowance?"),
    (130, "LLM-BOUNDARY", "What is the promotion policy at OML?"),
    (131, "LLM-BOUNDARY", "How many sick leaves do employees get?"),
    (132, "LLM-BOUNDARY", "Does OML provide a performance bonus?"),
    (133, "LLM-BOUNDARY", "What is the notice period for employees?"),
    (134, "LLM-BOUNDARY", "What is the employee PF contribution percentage?"),
    (135, "LLM-BOUNDARY", "Does OML have a stock option policy?"),
    (136, "LLM-BOUNDARY", "What is the salary increment percentage this year?"),
]


assert len(QUESTIONS) == 136


# ================================================================
# ISOLATE EVERY QUESTION
# ================================================================

# These monkey patches prevent one test question from inheriting
# conversation history/state from another question.
#
# IMPORTANT:
# Neo4j, PostgreSQL, pgvector and Ollama are NOT mocked.
# Every question still exercises the real system.

def _empty_history(*args, **kwargs):
    return []


def _noop(*args, **kwargs):
    return None


def _empty_state(*args, **kwargs):
    return {}


def _fresh_state(client_id, thought):
    return thought or {}


orchestrator.get_history = _empty_history
orchestrator.add_message = _noop
orchestrator.get_state = _empty_state
orchestrator.update_state = _fresh_state

orchestrator.get_flow = _empty_state
orchestrator.set_flow = _noop
orchestrator.clear_flow = _noop
orchestrator.set_entity = _noop


# ================================================================
# TEST RUNNER
# ================================================================

def run_test():

    results = []

    total = len(QUESTIONS)

    print("\n" + "=" * 90)
    print("OML HR ASSISTANT — REAL WORLD BRUTE FORCE TEST")
    print("=" * 90)
    print(f"Questions: {total}")
    print("Neo4j + PostgreSQL/pgvector + Ollama: LIVE")
    print("Conversation history/state isolation: ENABLED")
    print("=" * 90)

    for number, category, question in QUESTIONS:

        print("\n" + "-" * 90)
        print(f"[{number}/{total}] {category}")
        print(f"Q: {question}")
        print("-" * 90)

        try:
            planned = plan_query(question)
        except Exception as exc:
            planned = {
                "intent": "planner_error",
                "error": str(exc),
            }

        started = time.perf_counter()

        try:
            answer = orchestrator.ask(
                CLIENT_ID,
                question,
                CURRENT_DATE,
            )

            elapsed = time.perf_counter() - started

            answer = "" if answer is None else str(answer).strip()

            status = "OK" if answer else "EMPTY"

            print("\nANSWER:")
            print(answer)

            print("\nPLAN:")
            print(planned)

            print(f"\nTIME: {elapsed:.2f}s")
            print(f"STATUS: {status}")

            results.append(
                {
                    "number": number,
                    "category": category,
                    "question": question,
                    "plan": planned,
                    "answer": answer,
                    "elapsed_seconds": round(elapsed, 3),
                    "status": status,
                    "error": None,
                }
            )

        except Exception as exc:

            elapsed = time.perf_counter() - started

            error_message = (
                f"{type(exc).__name__}: {exc}"
            )

            print("\nERROR:")
            print(error_message)

            print("\nPLAN:")
            print(planned)

            print(f"\nTIME: {elapsed:.2f}s")

            results.append(
                {
                    "number": number,
                    "category": category,
                    "question": question,
                    "plan": planned,
                    "answer": "",
                    "elapsed_seconds": round(elapsed, 3),
                    "status": "ERROR",
                    "error": error_message,
                }
            )

    # ============================================================
    # SUMMARY
    # ============================================================

    ok = sum(
        r["status"] == "OK"
        for r in results
    )

    empty = sum(
        r["status"] == "EMPTY"
        for r in results
    )

    errors = sum(
        r["status"] == "ERROR"
        for r in results
    )

    neo4j = sum(
        r["category"] == "NEO4J"
        for r in results
    )

    llm = sum(
        r["category"] == "LLM"
        for r in results
    )

    boundary = sum(
        r["category"] == "LLM-BOUNDARY"
        for r in results
    )

    average_time = (
        sum(r["elapsed_seconds"] for r in results)
        / len(results)
        if results
        else 0
    )

    print("\n" + "=" * 90)
    print("FINAL SUMMARY")
    print("=" * 90)
    print(f"TOTAL:    {len(results)}")
    print(f"OK:       {ok}")
    print(f"EMPTY:    {empty}")
    print(f"ERRORS:   {errors}")
    print(f"NEO4J:    {neo4j}")
    print(f"LLM/RAG:  {llm}")
    print(f"BOUNDARY: {boundary}")
    print(f"AVG TIME: {average_time:.2f}s")
    print("=" * 90)

    # ============================================================
    # WRITE TEXT RESULTS
    # ============================================================

    text_lines = [
        "OML HR ASSISTANT — REAL WORLD BRUTE FORCE TEST",
        "=" * 90,
        f"TOTAL: {len(results)}",
        f"OK: {ok}",
        f"EMPTY: {empty}",
        f"ERRORS: {errors}",
        f"NEO4J: {neo4j}",
        f"LLM/RAG: {llm}",
        f"BOUNDARY: {boundary}",
        f"AVERAGE TIME: {average_time:.2f}s",
        "",
        "=" * 90,
        "ANSWERS",
        "=" * 90,
    ]

    for result in results:

        text_lines.extend(
            [
                "",
                f"[{result['number']}] {result['category']}",
                f"Q: {result['question']}",
                f"PLAN: {result['plan']}",
                f"STATUS: {result['status']}",
                f"TIME: {result['elapsed_seconds']:.3f}s",
                f"ANSWER: {result['answer']}",
            ]
        )

        if result["error"]:
            text_lines.append(
                f"ERROR: {result['error']}"
            )

    Path(
        "real_world_test_results.txt"
    ).write_text(
        "\n".join(text_lines),
        encoding="utf-8",
    )

    # ============================================================
    # WRITE JSON RESULTS
    # ============================================================

    summary = {
        "total": len(results),
        "ok": ok,
        "empty": empty,
        "errors": errors,
        "neo4j": neo4j,
        "llm_rag": llm,
        "boundary": boundary,
        "average_seconds": round(
            average_time,
            3,
        ),
    }

    Path(
        "real_world_test_results.json"
    ).write_text(
        json.dumps(
            {
                "summary": summary,
                "results": results,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("\nWrote real_world_test_results.txt")
    print("Wrote real_world_test_results.json")

    return results


if __name__ == "__main__":
    run_test()