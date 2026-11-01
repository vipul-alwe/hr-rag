# app/planner.py


def normalize(text: str):
    return text.lower().strip()


def contains_any(q, terms):
    return any(x in q for x in terms)


def plan_query(query: str):

    q = normalize(query)

    # ============================================================
    # SMALL TALK
    # ============================================================

    SMALL_TALK = [
        "hi",
        "hello",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
        "how are you",
        "thanks",
        "thank you",
    ]

    if any(
        q == x or q.startswith(x)
        for x in SMALL_TALK
    ):
        return {
            "intent": "small_talk",
            "mode": "direct",
        }

    # ============================================================
    # GRATUITY
    # ============================================================

    if "gratuity" in q:
        return {
            "intent": "gratuity",
            "mode": "flow",
        }

    # ============================================================
    # HOLIDAYS / FESTIVALS
    # ============================================================

    holiday_terms = [
        "holiday",
        "holidays",
        "festival",
        "leave calendar",
        "next holiday",
        "upcoming holiday",
    ]

    festival_terms = [
        "diwali",
        "holi",
        "eid",
        "christmas",
        "dussehra",
        "ganesh",
        "raksha",
        "navratri",
        "pongal",
        "onam",
        "bihu",
    ]

    if (
        contains_any(q, holiday_terms)
        or contains_any(q, festival_terms)
    ):
        return {
            "intent": "holiday",
            "mode": "direct",
        }

    # ============================================================
    # DIRECT REPORTS
    #
    # These MUST come before manager_terms because:
    #
    # "Who reports to Roycin?"
    #
    # contains "reports to", but means the opposite of:
    #
    # "Who does Roycin report to?"
    # ============================================================

    reports_terms = [
        "who reports to",
        "who report to",
        "who reports under",
        "who report under",
        "who works under",
        "who work under",
        "who is under",
        "who are under",
        "direct reports",
        "people reporting to",
        "employees reporting to",
    ]

    if contains_any(q, reports_terms):
        return {
            "intent": "org_reports",
            "mode": "neo4j",
        }

    # ============================================================
    # MANAGER
    # ============================================================

    manager_terms = [
        "reports to",
        "report to",
        "reporting to",
        "who is the manager",
        "who's the manager",
        "who manages",
        "manager of",
        "who is the boss",
        "who's the boss",
        "boss of",

        # Possessive forms
        "'s manager",
        "'s boss",
    ]

    if contains_any(q, manager_terms):
        return {
            "intent": "org_manager",
            "mode": "neo4j",
        }

    # ============================================================
    # MANAGEMENT CHAIN / HIERARCHY
    # ============================================================

    chain_terms = [
        "management chain",
        "reporting chain",
        "hierarchy",
        "org hierarchy",
        "organizational hierarchy",
        "who is above",
        "who are above",
        "who is senior to",
        "who are senior to",
    ]

    if contains_any(q, chain_terms):
        return {
            "intent": "org_chain",
            "mode": "neo4j",
        }

    # ============================================================
    # TEAM
    # ============================================================

    team_terms = [
        "team members",
        "who is in",
        "who are in",
        "members of the team",
        "team of",
        "who works with",
        "who work with",

        # Team phrasing
        "on my team",
        "on his team",
        "on her team",
        "'s team",
    ]

    if contains_any(q, team_terms):
        return {
            "intent": "org_team",
            "mode": "neo4j",
        }

    # ============================================================
    # ORGANIZATIONAL SUBTREE
    # ============================================================

    subtree_terms = [
        "everyone under",
        "all employees under",
        "all people under",
        "organization under",
        "org under",
        "subtree under",
        "everyone reporting under",
        "all reports under",
    ]

    if contains_any(q, subtree_terms):
        return {
            "intent": "org_subtree",
            "mode": "neo4j",
        }

    # ============================================================
    # GENERAL LLM
    # ============================================================

    return {
        "intent": "general",
        "mode": "llm",
    }