# app/tests/rag_test.py

from app.core.retriever import (
    embed_text,
    retrieve_context,
    detect_policy_from_db,
)

from app.core.reranker import (
    rerank_results,
)

from app.core.generator import (
    generate_answer,
)


CLIENT_ID = "11111111-1111-1111-1111-111111111111"


PASS = 0
FAIL = 0


# ============================================================
# TEST HELPERS
# ============================================================

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
# 1. OLLAMA EMBEDDINGS
# ============================================================

def test_embeddings():

    section("1. EMBEDDINGS")

    try:

        embedding = embed_text(
            "How many casual leaves do employees get?"
        )

        test(
            "Ollama embedding works",
            isinstance(embedding, list)
            and len(embedding) > 0,
            f"Embedding dimensions: {len(embedding)}"
        )

        test(
            "Embedding contains numeric values",
            all(
                isinstance(x, (int, float))
                for x in embedding[:10]
            )
        )

    except Exception as e:

        test(
            "Ollama embedding works",
            False,
            str(e)
        )


# ============================================================
# 2. POLICY DETECTION
# ============================================================

def test_policy_detection():

    section("2. POLICY DETECTION")

    policies = [
        "code of conduct",
        "holidays",
        "it policy",
        "leave policy",
        "onboarding policy",
        "parental policy",
        "posh",
        "travel policy",
    ]

    cases = [

        (
            "How many casual leaves do employees get?",
            "leave policy",
        ),

        (
            "How long do I have to file a sexual harassment complaint?",
            "posh",
        ),

        (
            "What should I do if I experience verbal abuse?",
            "code of conduct",
        ),

        (
            "Do I need approval for business travel?",
            "travel policy",
        ),

        (
            "What happens during employee onboarding?",
            "onboarding policy",
        ),

    ]

    for query, expected in cases:

        try:

            result = detect_policy_from_db(
                query,
                policies
            )

            test(
                query,
                result is not None
                and expected in result.lower(),
                f"Expected: {expected}, Got: {result}"
            )

        except Exception as e:

            test(
                query,
                False,
                str(e)
            )


# ============================================================
# 3. RETRIEVAL
# ============================================================

def test_retrieval():

    section("3. RETRIEVAL")

    cases = [

        (
            "How many casual leaves do employees get per year?",
            [
                "casual",
                "22",
                "leave",
            ],
        ),

        (
            "Does OML have a sandwich leave policy?",
            [
                "sandwich",
            ],
        ),

        (
            "How long do I have to file a POSH complaint?",
            [
                "three months",
            ],
        ),

        (
            "Who can I contact for a POSH complaint?",
            [
                "pranali",
                "posh",
            ],
        ),

        (
            "Do I need approval before taking leave?",
            [
                "approval",
                "manager",
            ],
        ),

        (
            "Are travel expenses reimbursed?",
            [
                "reimbursable",
                "receipts",
            ],
        ),

        (
            "Does business travel require pre-approval?",
            [
                "pre-approved",
                "travel",
            ],
        ),

        (
            "What happens during onboarding?",
            [
                "onboarding",
                "induction",
            ],
        ),

    ]

    for query, expected_terms in cases:

        try:

            results = retrieve_context(
                CLIENT_ID,
                query,
            )

            combined = "\n".join(
                results
            ).lower()

            matched = [
                term
                for term in expected_terms
                if term.lower() in combined
            ]

            test(
                query,
                len(matched) > 0,
                (
                    f"Matched: {matched}; "
                    f"Chunks: {len(results)}"
                )
            )

        except Exception as e:

            test(
                query,
                False,
                str(e)
            )


# ============================================================
# 4. UNKNOWN INFORMATION
# ============================================================

def test_unknown_retrieval():

    section("4. UNKNOWN INFORMATION")

    cases = [

        "What is the employee annual bonus percentage?",

        "What is the company's medical insurance premium?",

        "What is the work from home salary allowance?",

    ]

    for query in cases:

        try:

            results = retrieve_context(
                CLIENT_ID,
                query,
            )

            test(
                query,
                isinstance(results, list),
                f"Retrieved chunks: {len(results)}"
            )

        except Exception as e:

            test(
                query,
                False,
                str(e)
            )


# ============================================================
# 5. RERANKER
# ============================================================

def test_reranker():

    section("5. RERANKER")

    results = [

        {
            "source": "policy",
            "content": (
                "There are 22 casual leaves per year."
            ),
            "metadata": {
                "policy_name": "Leave Policy",
                "section_title": "Casual Leaves",
                "designation": "",
                "department": "",
            },
            "score": 0.20,
        },

        {
            "source": "policy",
            "content": (
                "International travel includes "
                "visa, insurance, and per diem provisions."
            ),
            "metadata": {
                "policy_name": "Travel Policy",
                "section_title": "International Travel",
                "designation": "",
                "department": "",
            },
            "score": 0.60,
        },

        {
            "source": "policy",
            "content": (
                "Employees are introduced to teams "
                "and systems during onboarding."
            ),
            "metadata": {
                "policy_name": "Onboarding Policy",
                "section_title": "Onboarding",
                "designation": "",
                "department": "",
            },
            "score": 0.50,
        },

    ]

    try:

        reranked = rerank_results(
            "How many casual leaves do employees get?",
            results,
            top_k=3,
        )

        test(
            "Reranker returns results",
            isinstance(reranked, list)
            and len(reranked) > 0,
            f"Results: {len(reranked)}"
        )

        if reranked:

            test(
                "Reranker returns final scores",
                "final_score" in reranked[0],
                f"First result: {reranked[0]}"
            )

            test(
                "Leave policy ranks first",
                "casual leaves"
                in reranked[0]["content"].lower(),
                f"Top result: {reranked[0]['content']}"
            )

    except Exception as e:

        test(
            "Reranker execution",
            False,
            str(e)
        )


# ============================================================
# 6. GENERATOR
# ============================================================

def test_generator():

    section("6. GENERATOR")

    context = [
        (
            "There are 22 casual leaves per year."
        ),
        (
            "Employees must obtain prior approval "
            "from their manager before availing leave, "
            "except in emergencies."
        ),
    ]

    try:

        answer = generate_answer(
            query="How many casual leaves do employees get?",
            context_chunks=context,
            current_date="2026-10-09",
            state={
                "intent": "query",
            },
        )

        test(
            "Generator returns an answer",
            isinstance(answer, str)
            and len(answer.strip()) > 0,
            f"Answer: {answer}"
        )

        test(
            "Generator answer contains grounded information",
            "22" in answer
            or "casual" in answer.lower(),
            f"Answer: {answer}"
        )

    except Exception as e:

        test(
            "Generator execution",
            False,
            str(e)
        )


# ============================================================
# 7. END-TO-END RAG
# ============================================================

def test_end_to_end_rag():

    section("7. END-TO-END RAG")

    cases = [

        (
            "How many casual leaves do employees get per year?",
            [
                "22",
                "casual",
            ],
        ),

        (
            "Does OML have a sandwich leave policy?",
            [
                "no",
                "sandwich",
            ],
        ),

        (
            "How long do I have to file a POSH complaint?",
            [
                "three months",
            ],
        ),

        (
            "Do I need approval before taking leave?",
            [
                "approval",
                "manager",
            ],
        ),

        (
            "Are travel expenses reimbursed?",
            [
                "reimbursable",
                "receipts",
            ],
        ),

    ]

    # Import here to avoid loading the complete orchestrator
    # during component-only tests.
    from app.orchestrator import ask

    for query, expected_terms in cases:

        try:

            answer = ask(
                CLIENT_ID,
                query,
                "2026-10-09",
            )

            answer_lower = answer.lower()

            matched = [
                term
                for term in expected_terms
                if term.lower() in answer_lower
            ]

            test(
                query,
                len(matched) > 0,
                (
                    f"Matched: {matched}; "
                    f"Answer: {answer}"
                )
            )

        except Exception as e:

            test(
                query,
                False,
                str(e)
            )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 60)
    print("HR RAG TEST")
    print("=" * 60)

    test_embeddings()
    test_policy_detection()
    test_retrieval()
    test_unknown_retrieval()
    test_reranker()
    test_generator()
    test_end_to_end_rag()

    print()
    print("=" * 60)
    print("RAG TEST SUMMARY")
    print("=" * 60)

    print(f"PASS: {PASS}")
    print(f"FAIL: {FAIL}")
    print(f"TOTAL: {PASS + FAIL}")

    if FAIL == 0:
        print()
        print("🎉 ALL RAG TESTS PASSED")

    else:
        print()
        print("⚠️ SOME RAG TESTS FAILED")


if __name__ == "__main__":
    main()