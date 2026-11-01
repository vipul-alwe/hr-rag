# app/reranker.py

from rapidfuzz import fuzz


# =============================
# NORMALIZATION
# =============================

def normalize(text: str):

    if not text:
        return ""

    return text.lower().strip()


# =============================
# ROLE BOOST
# =============================

def get_role_boost(
    query: str,
    metadata: dict
):

    q = normalize(query)

    designation = normalize(
        metadata.get(
            "designation",
            ""
        )
    )

    employee_context = normalize(
        metadata.get(
            "employee_context",
            ""
        )
    )

    searchable = (
        designation + " " +
        employee_context
    )

    leadership_terms = [

        "ceo",
        "cfo",
        "cbo",
        "chief",
        "director",
        "head",
        "vp",
        "vice president"

    ]

    boost = 0

    # leadership query boost
    leadership_query_terms = [

        "lead",
        "leader",
        "head",
        "chief",
        "who handles",
        "who manages",
        "who owns",
        "who runs"

    ]

    leadership_query = any(
        term in q
        for term in leadership_query_terms
    )

    if leadership_query:

        for term in leadership_terms:

            if term in searchable:

                boost += 0.20

    return boost


# =============================
# METADATA BOOST
# =============================

def get_metadata_boost(
    query: str,
    metadata: dict
):

    q = normalize(query)

    policy_name = normalize(
        metadata.get(
            "policy_name",
            ""
        )
    )

    section_title = normalize(
        metadata.get(
            "section_title",
            ""
        )
    )

    designation = normalize(
        metadata.get(
            "designation",
            ""
        )
    )

    department = normalize(
        metadata.get(
            "department",
            ""
        )
    )

    combined = " ".join([

        policy_name,
        section_title,
        designation,
        department

    ])

    fuzzy_score = fuzz.token_set_ratio(
        q,
        combined
    ) / 100

    return fuzzy_score * 0.25


# =============================
# CONTENT BOOST
# =============================

def get_content_boost(
    query: str,
    content: str
):

    q = normalize(query)

    c = normalize(content)

    fuzzy_score = fuzz.token_set_ratio(
        q,
        c
    ) / 100

    partial_score = fuzz.partial_ratio(
        q,
        c
    ) / 100

    return (
        fuzzy_score * 0.15 +
        partial_score * 0.15
    )


# =============================
# SOURCE BOOST
# =============================

def get_source_boost(
    source: str
):

    boosts = {

        "employee": 0.12,
        "policy": 0.08,
        "holiday": 0.05,
        "memory": 0.03

    }

    return boosts.get(
        source,
        0
    )


# =============================
# MAIN RERANKER
# =============================

def rerank_results(
    query: str,
    results: list,
    top_k: int = 5
):

    reranked = []

    for result in results:

        try:

            source = result.get(
                "source",
                "unknown"
            )

            content = result.get(
                "content",
                ""
            )

            metadata = result.get(
                "metadata",
                {}
            )

            raw_score = result.get(
                "score",
                1.0
            )

            # =============================
            # VECTOR SCORE
            # pgvector cosine distance:
            # LOWER = BETTER
            # =============================

            vector_score = 1 - min(
                max(raw_score, 0),
                1
            )

            # =============================
            # FUZZY BOOSTS
            # =============================

            metadata_boost = get_metadata_boost(
                query,
                metadata
            )

            content_boost = get_content_boost(
                query,
                content
            )

            role_boost = get_role_boost(
                query,
                metadata
            )

            source_boost = get_source_boost(
                source
            )

            # =============================
            # FINAL SCORE
            # =============================

            final_score = (

                vector_score * 0.50 +

                metadata_boost +

                content_boost +

                role_boost +

                source_boost

            )

            reranked.append({

                "source": source,

                "content": content,

                "metadata": metadata,

                "raw_score": raw_score,

                "final_score": final_score

            })

        except Exception as e:

            print(
                "Reranker error:",
                e
            )

    # =============================
    # SORT BEST FIRST
    # =============================

    reranked.sort(
        key=lambda x: x["final_score"],
        reverse=True
    )

    return reranked[:top_k]