# app/tests/rag_debug.py

import os

from app.core.retriever import (
    embed_text,
    detect_policy_from_db,
    retrieve_context,
    OLLAMA_EMBED_URL,
    EMBED_MODEL,
)

from app.db import get_cursor


CLIENT_ID = "11111111-1111-1111-1111-111111111111"

QUERIES = [
    {
        "name": "Sandwich Leave",
        "query": "Does OML have a sandwich leave policy?",
    },
    {
        "name": "Leave Approval",
        "query": "Do I need approval before taking leave?",
    },
    {
        "name": "Travel Reimbursement",
        "query": "Are travel expenses reimbursed?",
    },
    {
        "name": "Onboarding",
        "query": "What happens during onboarding?",
    },
]


# ============================================================
# HELPERS
# ============================================================

def print_separator():
    print()
    print("=" * 80)


def print_chunk(index, content, score=None, metadata=None):
    print()
    print(f"--- RESULT {index} ---")

    if score is not None:
        print(f"Score: {score}")

    if metadata:
        print("Metadata:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")

    print("Content:")
    print(content)


# ============================================================
# DATABASE INSPECTION
# ============================================================

def get_policy_names():

    with get_cursor() as cur:

        cur.execute("""
            SELECT DISTINCT policy_name
            FROM rag_data
            WHERE client_id = %s
            ORDER BY policy_name
        """, (CLIENT_ID,))

        rows = cur.fetchall()

    return [
        row[0]
        for row in rows
        if row[0]
    ]


def get_raw_vector_results(query, limit=20):

    embedding = embed_text(query)

    with get_cursor() as cur:

        cur.execute("""
            SELECT
                content,
                policy_name,
                section_title,
                designation,
                department,
                source,
                1 - (embedding <=> %s::vector) AS similarity
            FROM rag_data
            WHERE client_id = %s
              AND embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (
            embedding,
            CLIENT_ID,
            embedding,
            limit,
        ))

        rows = cur.fetchall()

    results = []

    for row in rows:

        results.append({
            "content": row[0],
            "policy_name": row[1],
            "section_title": row[2],
            "designation": row[3],
            "department": row[4],
            "source": row[5],
            "similarity": row[6],
        })

    return results


# ============================================================
# QUERY DIAGNOSTIC
# ============================================================

def debug_query(name, query):

    print_separator()

    print(f"QUERY: {query}")
    print(f"CLIENT: {CLIENT_ID}")

    # --------------------------------------------------------
    # EMBEDDING
    # --------------------------------------------------------

    print_separator()
    print("1. EMBEDDING")

    try:

        embedding = embed_text(query)

        print("✅ Embedding generated")
        print(f"Embedding dimensions: {len(embedding)}")
        print(f"First 5 values: {embedding[:5]}")

    except Exception as e:

        print("❌ Embedding failed")
        print(e)
        return

    # --------------------------------------------------------
    # POLICY LIST
    # --------------------------------------------------------

    print_separator()
    print("2. AVAILABLE POLICIES")

    try:

        policies = get_policy_names()

        for policy in policies:
            print(f"- {policy}")

        print(f"\nTotal policies: {len(policies)}")

    except Exception as e:

        print("❌ Could not load policies")
        print(e)

        policies = []

    # --------------------------------------------------------
    # LLM POLICY DETECTION
    # --------------------------------------------------------

    print_separator()
    print("3. LLM POLICY DETECTION")

    try:

        detected_policy = detect_policy_from_db(
            query,
            policies,
        )

        print(f"Detected policy: {detected_policy}")

    except Exception as e:

        print("❌ Policy detection failed")
        print(e)
        detected_policy = None

    # --------------------------------------------------------
    # RAW VECTOR SEARCH
    # --------------------------------------------------------

    print_separator()
    print("4. RAW VECTOR SEARCH")

    try:

        raw_results = get_raw_vector_results(
            query,
            limit=20,
        )

        print(
            f"Raw vector results: {len(raw_results)}"
        )

        for index, result in enumerate(
            raw_results,
            start=1,
        ):

            print_chunk(
                index=index,
                content=result["content"],
                score=result["similarity"],
                metadata={
                    "policy_name": result["policy_name"],
                    "section_title": result["section_title"],
                    "designation": result["designation"],
                    "department": result["department"],
                    "source": result["source"],
                },
            )

    except Exception as e:

        print("❌ Raw vector search failed")
        print(e)
        raw_results = []

    # --------------------------------------------------------
    # POLICY MATCHING ANALYSIS
    # --------------------------------------------------------

    print_separator()
    print("5. POLICY MATCHING ANALYSIS")

    if detected_policy:

        detected = detected_policy.lower().strip()

        print(
            f"Detected policy: {detected}"
        )

        matching = []

        for index, result in enumerate(
            raw_results,
            start=1,
        ):

            policy_name = (
                result["policy_name"] or ""
            ).lower()

            section_title = (
                result["section_title"] or ""
            ).lower()

            if (
                detected in policy_name
                or policy_name in detected
                or detected in section_title
            ):

                matching.append(
                    (index, result)
                )

        print(
            f"Policy-matching raw results: "
            f"{len(matching)}"
        )

        for index, result in matching:

            print(
                f"  Result {index}: "
                f"{result['policy_name']} "
                f"/ {result['section_title']}"
            )

    else:

        print(
            "No policy detected by LLM."
        )

    # --------------------------------------------------------
    # ACTUAL RETRIEVER
    # --------------------------------------------------------

    print_separator()
    print("6. ACTUAL RETRIEVER")

    try:

        final_chunks = retrieve_context(
            CLIENT_ID,
            query,
        )

        print(
            f"Final retrieved chunks: "
            f"{len(final_chunks)}"
        )

        for index, chunk in enumerate(
            final_chunks,
            start=1,
        ):

            print_chunk(
                index=index,
                content=chunk,
            )

    except Exception as e:

        print("❌ Retriever failed")
        print(e)
        final_chunks = []

    # --------------------------------------------------------
    # KEYWORD CHECK
    # --------------------------------------------------------

    print_separator()
    print("7. KEYWORD CHECK")

    keyword_groups = {
        "sandwich": [
            "sandwich",
            "leave",
        ],

        "leave approval": [
            "approval",
            "manager",
            "leave",
        ],

        "travel reimbursement": [
            "reimburs",
            "receipt",
            "expense",
            "travel",
        ],

        "onboarding": [
            "onboarding",
            "induction",
            "30",
            "60",
            "90",
        ],
    }

    query_lower = query.lower()

    selected_keywords = []

    for group_name, keywords in keyword_groups.items():

        if any(
            keyword in query_lower
            for keyword in keywords
        ):

            selected_keywords.extend(
                keywords
            )

    combined_context = "\n".join(
        final_chunks
    ).lower()

    if selected_keywords:

        print("Keywords checked:")

        for keyword in selected_keywords:

            found = keyword.lower() in combined_context

            status = "FOUND" if found else "MISSING"

            print(
                f"  {status}: {keyword}"
            )

    else:

        print(
            "No keyword group selected."
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 80)
    print("RAG RETRIEVAL DEBUGGER")
    print("=" * 80)

    print()
    print(f"Client ID: {CLIENT_ID}")
    print(f"Embedding model: {EMBED_MODEL}")
    print(f"Embedding endpoint: {OLLAMA_EMBED_URL}")

    for item in QUERIES:

        debug_query(
            item["name"],
            item["query"],
        )

    print_separator()

    print("DEBUG COMPLETE")
    print()


if __name__ == "__main__":
    main()