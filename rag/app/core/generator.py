import requests

OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"
GEN_MODEL = "mistral-nemo:latest"

MAX_CONTEXT_CHARS = 5000


# =============================
# 🧠 CONTEXT PRIORITIZATION
# =============================

def prioritize_context(context_chunks):

    employee = []
    structural = []
    others = []

    for chunk in context_chunks:
        text = chunk.lower()

        if chunk.startswith("Employee Info:"):
            employee.append(chunk)

        elif any(x in text for x in [
            "vice president", "manager", "lead", "head"
        ]):
            structural.append(chunk)

        else:
            others.append(chunk)

    # 🔥 employee first always
    return employee + others + structural


# =============================
# 🧠 GENERATOR
# =============================

def generate_answer(
    query,
    context_chunks,
    history=None,
    current_date=None,
    state=None
):

    print("\n==============================")
    print("🧠 GENERATOR START")
    print("==============================")

    print("\n❓ QUERY:", query)

    intent = state.get("intent") if state else None

    print("🧠 STATE:", state)

    # =============================
    # CONTEXT BUILDING
    # =============================

    context_chunks = prioritize_context(context_chunks)

    employee_block = ""
    additional_block = ""

    for chunk in context_chunks:
        if chunk.startswith("Employee Info:"):
            employee_block += chunk + "\n\n"
        else:
            additional_block += chunk + "\n\n"

    # 🔥 FIX: employee first
    context_text = (employee_block + additional_block)[:MAX_CONTEXT_CHARS]

    print("\n📦 CONTEXT LENGTH:", len(context_text))

    # =============================
    # HISTORY
    # =============================

    history_text = ""

    if history:
        recent = history[-6:]
        history_text = "\n".join(
            f"{m['role'].capitalize()}: {m['content']}"
            for m in recent
        )

    # =============================
    # BEHAVIOR
    # =============================

    if intent == "complaint":
        behavior_block = """
    - Be supportive but factual
    - Provide steps clearly if available
    """

    elif intent in ["KnowWho", "employee", "Informational"]:
        behavior_block = """
    - Provide complete details about the employee
    - Include designation, department, and role context if available
    - Mention contacts only if explicitly present in CONTEXT
    - Do NOT shorten the answer
    """

    else:
        behavior_block = """
    - Be concise but complete
    """

    # =============================
    # PROMPT
    # =============================

    prompt = f"""
You are an internal HR assistant for OML.

Answer ONLY using CONTEXT.

---------------------
CRITICAL RULES
---------------------
- Do NOT invent any information
- Do NOT use external knowledge
- Do NOT mix unrelated policies
- Do NOT answer questions that are not HR related
- Do NOT provide coding related help
- Do NOT make up names, designations, or contacts only return those present in CONTEXT
- Do NOT talk about the CONTEXT itself (e.g. "In the provided context...")

- If not explicitly stated in CONTEXT, say:
  "This is not specified in the policy."

---------------------
ALLOWED INFERENCE (STRICT)
---------------------
- You may ONLY infer hierarchy for ranking (e.g., identifying senior-most)
- You MUST NOT explain roles, responsibilities, or job functions
- You MUST NOT use general knowledge about job titles (CEO, CGO, etc.)

---------------------
PRIORITY
---------------------
1. Employee Info (if present)
2. Then Policy Mentions

---------------------
BEHAVIOR
---------------------
{behavior_block}

---------------------
OUTPUT RULES
---------------------

- Use bullet points if needed
- Include contacts ONLY if present
- Do NOT hallucinate names/emails
- For employee queries:
  Include ONLY information explicitly present in CONTEXT
  Add as much detail as possible from CONTEXT, do NOT shorten
  If role context is missing, DO NOT add explanations

---------------------
CONTEXT
---------------------
{context_text}

---------------------
QUESTION
---------------------
{query}

---------------------
ANSWER
---------------------
"""

    print("\n📏 PROMPT LENGTH:", len(prompt))

    # =============================
    # GENERATION
    # =============================

    res = requests.post(
        OLLAMA_GENERATE_URL,
        json={
            "model": GEN_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0,
                "top_p": 0.9,
                "num_predict": 300
            }
        }
    )

    res.raise_for_status()

    answer = res.json()["response"].strip()

    print("\n🧾 RAW OUTPUT:\n", answer)

    # =============================
    # HALLUCINATION FILTER
    # =============================

    context_lower = context_text.lower()
    answer_lower = answer.lower()

    forbidden_terms = [
        "ethics",
        "eap",
        "legal team",
        "union",
        "compliance department"
    ]

    violations = [
        t for t in forbidden_terms
        if t in answer_lower and t not in context_lower
    ]

    if len(violations) >= 2:
        print("🚨 HALLUCINATION:", violations)
        return "This is not specified in the policy."

    # =============================
    # SMART GROUNDING (FIXED)
    # =============================

    context_words = set(context_lower.split())
    answer_words = set(answer_lower.split())

    overlap = len(answer_words & context_words) / (len(answer_words) + 1)

    print("🔗 OVERLAP:", overlap)

    # 🔥 allow inference queries
    if overlap < 0.08:
        if any(x in query.lower() for x in ["who leads", "leader", "head"]):
            pass
        else:
            return "This is not specified in the policy."

    print("\n✅ FINAL ANSWER:\n", answer)

    print("\n==============================")
    print("🧠 GENERATOR END")
    print("==============================")

    return answer