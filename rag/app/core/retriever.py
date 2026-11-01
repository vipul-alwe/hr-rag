import re

import requests

from app.db import retrieve_similar, get_cursor


# ==========================
# CONFIG
# ==========================

OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
GEN_URL = "http://localhost:11434/api/generate"

EMBED_MODEL = "nomic-embed-text"
GEN_MODEL = "mistral-nemo:latest"

# Retrieve a larger candidate pool from pgvector.
# We will reduce this to the best 8 chunks after
# lexical + semantic ranking.
VECTOR_TOP_K = 50
FINAL_TOP_K = 8

SIMILARITY_THRESHOLD = 0.55


# ==========================
# NORMALIZATION
# ==========================

def normalize_policy(name):
    """
    Normalize policy names so that variations such as:

        Leave Policy
        leave_policy
        leave-policy
        Leave policy

    can be compared safely.
    """

    if not name:
        return ""

    normalized = str(name).lower()

    normalized = normalized.replace("_", " ")
    normalized = normalized.replace("-", " ")

    normalized = normalized.replace("policy", " ")

    return " ".join(normalized.split())


def normalize_text(text):
    if not text:
        return ""

    text = str(text).lower()

    text = text.replace("’", "'")
    text = text.replace("–", "-")
    text = text.replace("—", "-")

    return " ".join(text.split())


# ==========================
# POLICY MATCHING
# ==========================

def policy_matches(focus, policy_name):
    """
    Flexible policy-name comparison.

    Examples:

        leave_policy  <-> Leave Policy
        travel        <-> Travel Policy
        code of conduct <-> Code of Conduct
        posh          <-> POSH
    """

    if not focus or not policy_name:
        return False

    focus_norm = normalize_policy(focus)
    policy_norm = normalize_policy(policy_name)

    if not focus_norm or not policy_norm:
        return False

    if focus_norm == policy_norm:
        return True

    if focus_norm in policy_norm:
        return True

    if policy_norm in focus_norm:
        return True

    focus_tokens = set(focus_norm.split())
    policy_tokens = set(policy_norm.split())

    if focus_tokens & policy_tokens:
        return True

    return False


# ==========================
# POLICY ALIASES
# ==========================

def normalize_policy_focus(focus):
    """
    Convert planner/orchestrator terminology into
    terminology that can reasonably match DB policy names.
    """

    if not focus:
        return None

    normalized = normalize_policy(focus)

    if normalized in {
        "",
        "none",
        "not specified",
        "not specified in the policy",
        "unknown",
        "null",
        "no policy",
    }:
        return None

    aliases = {
        "leave policy": "leave",
        "leave": "leave",

        "travel expenses": "travel",
        "travel expense": "travel",
        "travel": "travel",

        "code of conduct": "code of conduct",
        "coc": "code of conduct",

        "posh": "posh",
        "sexual harassment": "posh",

        "parental": "parental",
        "parental policy": "parental",

        "onboarding": "onboarding",
        "onboarding policy": "onboarding",

        "it": "it",
        "it policy": "it",
    }

    return aliases.get(normalized, normalized)


# ==========================
# ABUSE / SENSITIVE POLICY
# ==========================

def detect_abuse_policy(query: str):
    q = normalize_text(query)

    sexual_terms = [
        "sexual harassment",
        "sexual harassment complaint",
        "sexual misconduct",
        "molest",
        "inappropriate touch",
        "posh",
    ]

    discrimination_terms = [
        "racial",
        "racism",
        "discriminat",
        "bias",
        "unfair treatment",
        "slur",
        "abuse",
        "insult",
        "offensive",
        "derogatory",
        "n word",
        "verbal abuse",
        "called me",
        "threat",
        "threatened",
        "intimidat",
        "unsafe",
        "fear",
    ]

    if any(term in q for term in sexual_terms):
        return "posh"

    if any(term in q for term in discrimination_terms):
        return "code of conduct"

    return None


# ==========================
# EMBEDDINGS
# ==========================

def embed_text(text: str):
    response = requests.post(
        OLLAMA_EMBED_URL,
        json={
            "model": EMBED_MODEL,
            "prompt": text,
        },
        timeout=60,
    )

    response.raise_for_status()

    return response.json()["embedding"]


def embedding_to_pgvector_string(embedding):
    return "[" + ",".join(str(x) for x in embedding) + "]"


# ==========================
# POLICY DISCOVERY
# ==========================

def get_all_policies(client_id: str):

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT policy_name
            FROM documents
            WHERE client_id = %s
              AND policy_name IS NOT NULL
            """,
            (client_id,)
        )

        rows = cur.fetchall()

    return [
        row[0]
        for row in rows
        if row[0]
    ]


def detect_policy_from_db(query: str, policies: list):

    if not policies:
        return None

    prompt = f"""
Pick the single most relevant policy for the query.

Available policies:
{policies}

Query:
{query}

Return ONLY one policy name from the list above.
If none are relevant, return:
none
"""

    try:
        response = requests.post(
            GEN_URL,
            json={
                "model": GEN_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0,
                    "num_predict": 30,
                },
            },
            timeout=60,
        )

        response.raise_for_status()

        answer = response.json()["response"].strip()

        if not answer:
            return None

        answer_norm = normalize_policy(answer)

        if answer_norm == "none":
            return None

        # Never trust an arbitrary LLM-generated policy name.
        # Only return something that actually corresponds
        # to a policy in the database.
        for policy in policies:
            if policy_matches(answer, policy):
                return policy

        return None

    except Exception as exc:
        print("⚠️ POLICY DETECTION ERROR:", exc)
        return None


# ==========================
# HOLIDAY DOCUMENTS
# ==========================

def fetch_holiday_documents(client_id: str):

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT content
            FROM documents
            WHERE client_id = %s
              AND content LIKE %s
            """,
            (
                client_id,
                '%"date"%',
            )
        )

        rows = cur.fetchall()

    return [
        row[0]
        for row in rows
        if row[0]
    ]


# ==========================
# QUERY TERMS
# ==========================

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "be",
    "before",
    "can",
    "do",
    "does",
    "for",
    "have",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "when",
    "where",
    "who",
    "why",
    "with",
    "you",
    "your",
}


def extract_query_terms(query):
    normalized = normalize_text(query)

    words = re.findall(r"[a-z0-9']+", normalized)

    return [
        word
        for word in words
        if word not in STOP_WORDS and len(word) >= 3
    ]


# ==========================
# LEXICAL SCORING
# ==========================

def lexical_score(query, content, policy_name="", section_title=""):
    """
    Lightweight lexical relevance score.

    This does NOT replace embeddings.

    It helps recover cases where the vector search finds
    the correct policy but ranks the exact subsection too low.

    Maximum score is approximately 1.0.
    """

    q = normalize_text(query)
    c = normalize_text(content)
    p = normalize_text(policy_name)
    s = normalize_text(section_title)

    if not q or not c:
        return 0.0

    score = 0.0

    terms = extract_query_terms(query)

    if not terms:
        return 0.0

    # ----------------------------------
    # Individual query terms
    # ----------------------------------

    matched_terms = 0

    for term in terms:

        if term in c:
            matched_terms += 1

            # Slightly stronger reward for exact word presence.
            score += 0.08

    # ----------------------------------
    # Query coverage
    # ----------------------------------

    coverage = matched_terms / max(len(terms), 1)

    score += coverage * 0.20

    # ----------------------------------
    # Exact phrase
    # ----------------------------------

    important_phrases = [
        "sandwich leave",
        "sandwich leave policy",
        "prior approval",
        "approval before",
        "manager approval",
        "taking leave",
        "leave approval",
        "travel expenses",
        "travel expense",
        "expenses reimbursed",
        "expense reimbursement",
        "reimbursed",
        "receipts",
        "onboarding",
        "induction",
        "30 day",
        "60 day",
        "90 day",
        "sexual harassment complaint",
        "file a complaint",
    ]

    for phrase in important_phrases:
        if phrase in q and phrase in c:
            score += 0.35

    # ----------------------------------
    # Policy name relevance
    # ----------------------------------

    normalized_policy = normalize_policy(policy_name)

    if normalized_policy:
        policy_terms = set(normalized_policy.split())

        if any(term in policy_terms for term in terms):
            score += 0.12

    # ----------------------------------
    # Section title relevance
    # ----------------------------------

    if s:
        section_terms = set(re.findall(r"[a-z0-9']+", s))

        matching_section_terms = sum(
            1
            for term in terms
            if term in section_terms
        )

        if matching_section_terms:
            score += min(
                0.20,
                matching_section_terms * 0.07
            )

    return min(score, 1.0)


# ==========================
# CONTENT RELEVANCE BOOSTS
# ==========================

def query_specific_boost(query, content):
    """
    Small deterministic boosts for common HR questions.

    These are intentionally narrow and transparent.
    """

    q = normalize_text(query)
    c = normalize_text(content)

    boost = 0.0

    patterns = [
        (
            [
                "sandwich leave",
                "sandwich leave policy",
            ],
            [
                "sandwich",
            ],
            0.35,
        ),

        (
            [
                "approval before taking leave",
                "approval before leave",
                "need approval",
                "manager approval",
                "leave approval",
            ],
            [
                "prior approval",
                "manager",
                "approval",
                "leave",
            ],
            0.30,
        ),

        (
            [
                "travel expenses reimbursed",
                "travel expense",
                "travel expenses",
                "reimbursement",
            ],
            [
                "reimburs",
                "receipts",
                "expense",
            ],
            0.30,
        ),

        (
            [
                "what happens during onboarding",
                "onboarding",
                "new employee",
            ],
            [
                "onboarding",
                "induction",
                "introduced",
                "30",
                "60",
                "90",
                "mandatory training",
            ],
            0.30,
        ),
    ]

    for query_patterns, content_patterns, boost_value in patterns:

        query_match = any(
            pattern in q
            for pattern in query_patterns
        )

        if not query_match:
            continue

        content_match = any(
            pattern in c
            for pattern in content_patterns
        )

        if content_match:
            boost += boost_value

    return boost


# ==========================
# MAIN RETRIEVAL
# ==========================

def retrieve_context(
    client_id: str,
    query: str,
    top_k=FINAL_TOP_K,
    policy_hint=None,
    entity=None,
    disable_policy_lock=False,
):

    print("\n==============================")
    print("📡 RETRIEVER START")
    print("==============================")

    print("🔍 QUERY:", query)
    print("🎯 POLICY HINT:", policy_hint)
    print("👤 ENTITY:", entity)
    print("🚫 DISABLE POLICY LOCK:", disable_policy_lock)

    q = normalize_text(query)

    # ==================================================
    # HOLIDAY BYPASS
    # ==================================================

    if "holiday" in q:
        docs = fetch_holiday_documents(client_id)

        if docs:
            print("🎯 HOLIDAY BYPASS")
            return docs

    # ==================================================
    # ENTITY MODE
    # ==================================================

    if entity:

        print("👤 ENTITY MODE ENABLED")

        embedding = embed_text(query)

        results = retrieve_similar(
            client_id,
            embedding_to_pgvector_string(embedding),
            VECTOR_TOP_K,
        )

        entity_chunks = []

        for item in results:

            content = item.get("content", "")

            if (
                content
                and entity.lower() in content.lower()
            ):
                entity_chunks.append(content)

        if entity_chunks:

            print(
                "✅ ENTITY MATCHES:",
                len(entity_chunks),
            )

            return entity_chunks[:top_k]

    # ==================================================
    # POLICY DETECTION
    # ==================================================

    if not disable_policy_lock:

        abuse_policy = detect_abuse_policy(query)

    else:

        abuse_policy = None

        print("🟡 POLICY LOCK DISABLED")

    policies = get_all_policies(client_id)

    detected_policy = detect_policy_from_db(
        query,
        policies,
    )

    # ==================================================
    # POLICY PRIORITY
    # ==================================================

    if abuse_policy:

        focus = abuse_policy

        print(
            "🚨 ABUSE POLICY LOCK:",
            focus,
        )

    elif policy_hint:

        focus = policy_hint

        print(
            "🎯 ORCHESTRATOR POLICY:",
            focus,
        )

    else:

        focus = detected_policy

        print(
            "🧠 LLM POLICY:",
            focus,
        )

    # ==================================================
    # HARD OVERRIDES
    # ==================================================

    if any(
        term in q
        for term in [
            "n word",
            "racial",
            "racism",
            "threat",
            "threatened",
        ]
    ):

        focus = "code of conduct"

        print(
            "🚨 HARD OVERRIDE → CODE OF CONDUCT"
        )

    focus = normalize_policy_focus(focus)

    print(
        "🎯 NORMALIZED POLICY FOCUS:",
        focus,
    )

    # ==================================================
    # EMBEDDING
    # ==================================================

    embedding = embed_text(query)

    results = retrieve_similar(
        client_id,
        embedding_to_pgvector_string(embedding),
        VECTOR_TOP_K,
    )

    print(
        "\n📦 VECTOR CANDIDATES:",
        len(results),
    )

    # ==================================================
    # SCORE CANDIDATES
    # ==================================================

    scored_chunks = []

    for item in results:

        try:

            content = item.get("content", "")
            policy_name = item.get("policy_name") or ""
            section_title = item.get("section_title") or ""
            vector_score = float(
                item.get("score", 0.0)
            )

            if not content:
                continue

            # ------------------------------------------
            # Similarity threshold
            # ------------------------------------------

            if vector_score < SIMILARITY_THRESHOLD:
                continue

            # ------------------------------------------
            # Policy filter
            # ------------------------------------------

            if (
                not disable_policy_lock
                and focus
                and not policy_matches(
                    focus,
                    policy_name,
                )
            ):

                continue

            # ------------------------------------------
            # Lexical relevance
            # ------------------------------------------

            lexical = lexical_score(
                query,
                content,
                policy_name,
                section_title,
            )

            specific_boost = query_specific_boost(
                query,
                content,
            )

            # ------------------------------------------
            # Entity boost
            # ------------------------------------------

            entity_boost = 0.0

            if (
                entity
                and entity.lower()
                in content.lower()
            ):

                entity_boost = 0.35

            # ------------------------------------------
            # Final score
            # ------------------------------------------

            final_score = (
                vector_score * 0.60
                + lexical * 0.25
                + specific_boost
                + entity_boost
            )

            scored_chunks.append(
                {
                    "content": content,
                    "policy_name": policy_name,
                    "section_title": section_title,
                    "vector_score": vector_score,
                    "lexical_score": lexical,
                    "specific_boost": specific_boost,
                    "entity_boost": entity_boost,
                    "final_score": final_score,
                }
            )

        except Exception as exc:

            print(
                "❌ RETRIEVAL SCORING ERROR:",
                exc,
            )

    # ==================================================
    # FALLBACK
    # ==================================================

    if not scored_chunks:

        print(
            "⚠️ NO MATCHES AFTER FILTERING → VECTOR FALLBACK"
        )

        fallback = []

        for item in results:

            content = item.get("content", "")

            if not content:
                continue

            fallback.append(
                {
                    "content": content,
                    "policy_name": (
                        item.get("policy_name")
                        or ""
                    ),
                    "section_title": (
                        item.get("section_title")
                        or ""
                    ),
                    "vector_score": float(
                        item.get("score", 0.0)
                    ),
                    "lexical_score": 0.0,
                    "specific_boost": 0.0,
                    "entity_boost": 0.0,
                    "final_score": float(
                        item.get("score", 0.0)
                    ),
                }
            )

        scored_chunks = fallback

    # ==================================================
    # FINAL SORT
    # ==================================================

    scored_chunks.sort(
        key=lambda x: x["final_score"],
        reverse=True,
    )

    final_results = scored_chunks[:top_k]

    print("\n📊 TOP RESULTS:")

    for index, item in enumerate(
        final_results,
        start=1,
    ):

        print(
            f"{index}. "
            f"final={item['final_score']:.3f} "
            f"vector={item['vector_score']:.3f} "
            f"lexical={item['lexical_score']:.3f} "
            f"boost={item['specific_boost']:.3f} "
            f"policy={item['policy_name']}"
        )

    final_chunks = [
        item["content"]
        for item in final_results
    ]

    print(
        "\n✅ FINAL CHUNKS:",
        len(final_chunks),
    )

    print("\n==============================")
    print("📡 RETRIEVER END")
    print("==============================")

    return final_chunks