# app/tools/holiday_engine.py

import json
import re
from datetime import datetime, timedelta


LAST_HOLIDAY_RESULTS = {}


# ============================================================
# PARSING
# ============================================================

def parse_holiday_json(content: str) -> list:
    """
    Parse a JSON holiday list.

    Supports:
    1. A clean JSON array
    2. A JSON array embedded inside surrounding text
    """

    if not content:
        return []

    try:
        data = json.loads(content)

        if isinstance(data, list):
            return data

    except Exception:
        pass

    try:
        match = re.search(
            r"\[.*?\]",
            content,
            re.DOTALL
        )

        if match:
            data = json.loads(match.group())

            if isinstance(data, list):
                return data

    except Exception as e:
        print("JSON parse error:", e)

    return []


# ============================================================
# DATE HELPERS
# ============================================================

def parse_date(date_str: str):
    try:
        return datetime.strptime(
            date_str,
            "%Y-%m-%d"
        )

    except Exception:
        return None


def format_date_human(date_str: str):

    dt = parse_date(date_str)

    if not dt:
        return date_str

    return dt.strftime("%d %b %Y")


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text: str):

    if not text:
        return ""

    text = text.lower().strip()

    text = re.sub(
        r"[^\w\s]",
        "",
        text
    )

    replacements = {
        "leaves": "leave",
        "holidays": "holiday",
        "festivals": "festival",
    }

    for old, new in replacements.items():
        text = text.replace(
            old,
            new
        )

    return text


# ============================================================
# QUERY PLANNER
# ============================================================

def infer_holiday_plan(query: str):

    q = normalize_text(query)

    plan = {
        "query_type": None,
        "holiday_name": None,
        "month": None,
        "date": None,
    }

    holiday_names = [
        "diwali",
        "holi",
        "eid",
        "bakri eid",
        "christmas",
        "new year",
        "ganesh chaturthi",
        "dussehra",
        "navratri",
        "mahashivratri",
        "ram navami",
        "janmashtami",
        "onam",
        "raksha bandhan",
        "guru nanak",
        "muharram",
        "christmas eve",
        "unplugged leave",
        "extended block leave",
        "optional holiday",
        "mandatory holiday",
        "optional",
        "mandatory",
    ]

    months = {
        "january": "01",
        "february": "02",
        "march": "03",
        "april": "04",
        "may": "05",
        "june": "06",
        "july": "07",
        "august": "08",
        "september": "09",
        "october": "10",
        "november": "11",
        "december": "12",
    }

    # --------------------------------------------------------
    # MONTH
    # --------------------------------------------------------

    for month_name, month_num in months.items():

        if re.search(
            rf"\b{month_name}\b",
            q
        ):
            plan["month"] = month_num
            break

    # --------------------------------------------------------
    # HOLIDAY NAME
    # --------------------------------------------------------

    for holiday in holiday_names:

        normalized_holiday = normalize_text(
            holiday
        )

        pattern = (
            rf"\b{re.escape(normalized_holiday)}\b"
        )

        if re.search(pattern, q):

            plan["holiday_name"] = holiday

            break

    # --------------------------------------------------------
    # FOLLOW-UP
    # --------------------------------------------------------

    followup_patterns = [
        "on what dates",
        "what dates",
        "which dates",
        "those holiday",
        "these holiday",
        "them",
        "those",
        "these",
    ]

    for pattern in followup_patterns:

        if pattern in q:

            plan["query_type"] = "followup_dates"

            return plan

    # --------------------------------------------------------
    # COUNT
    # --------------------------------------------------------

    if (
        "how many" in q
        or "count" in q
        or "number of" in q
    ):

        plan["query_type"] = "count"

    # --------------------------------------------------------
    # NEXT
    # --------------------------------------------------------

    elif (
        "next holiday" in q
        or "upcoming holiday" in q
        or "next unplugged leave" in q
        or "upcoming unplugged leave" in q
        or "next extended block leave" in q
        or "upcoming extended block leave" in q
    ):

        plan["query_type"] = "next"

    # --------------------------------------------------------
    # TODAY
    # --------------------------------------------------------

    elif (
        "today holiday" in q
        or "holiday today" in q
    ):

        plan["query_type"] = "today"

    # --------------------------------------------------------
    # LIST
    # --------------------------------------------------------

    elif (
        "holiday" in q
        and (
            "all" in q
            or "list" in q
            or "show" in q
        )
    ):

        plan["query_type"] = "list"

    # --------------------------------------------------------
    # EXISTS
    # --------------------------------------------------------

    elif re.search(
        r"\bis there\b",
        q
    ):

        plan["query_type"] = "exists"

    # --------------------------------------------------------
    # LOOKUP
    # --------------------------------------------------------

    elif plan["holiday_name"]:

        plan["query_type"] = "lookup"

    return plan


# ============================================================
# HOLIDAY SEARCH
# ============================================================

def find_by_name(data, name):

    if not name:
        return []

    normalized_query = normalize_text(
        name
    )

    query_tokens = set(
        normalized_query.split()
    )

    matches = []

    for holiday in data:

        holiday_name = normalize_text(
            holiday["name"]
        )

        holiday_tokens = set(
            holiday_name.split()
        )

        if query_tokens.intersection(
            holiday_tokens
        ):
            matches.append(holiday)

    return matches


# ============================================================
# FORMATTING
# ============================================================

def format_holiday(h):

    return (
        f"{h['name']} on "
        f"{format_date_human(h['date'])}"
    )


def format_holiday_list(data):

    return "\n".join(
        [
            f"- {h['name']} on "
            f"{format_date_human(h['date'])}"
            for h in data
        ]
    )


# ============================================================
# MAIN HOLIDAY ENGINE
# ============================================================

def process_holiday_question(
    documents,
    query,
    current_date,
    plan=None,
):

    global LAST_HOLIDAY_RESULTS

    print("\n==============================")
    print("🎉 HOLIDAY ENGINE START")
    print("==============================")

    print("QUERY:", query)
    print("CURRENT DATE:", current_date)
    print("DOCUMENT COUNT:", len(documents))

    # --------------------------------------------------------
    # PARSE DOCUMENTS
    # --------------------------------------------------------

    all_holidays = []

    for idx, doc in enumerate(documents):

        print(f"\n📄 DOCUMENT {idx}")

        print(
            doc[:500]
            if doc
            else "(empty document)"
        )

        parsed = parse_holiday_json(
            doc
        )

        print(
            "PARSED COUNT:",
            len(parsed)
        )

        if parsed:
            all_holidays.extend(
                parsed
            )

    print(
        "\n🎯 TOTAL HOLIDAYS FOUND:",
        len(all_holidays)
    )

    if all_holidays[:5]:

        print("\nSAMPLE HOLIDAYS:")

        for holiday in all_holidays[:5]:
            print(holiday)

    if not all_holidays:

        print(
            "❌ NO HOLIDAYS PARSED"
        )

        return None

    # --------------------------------------------------------
    # CURRENT DATE
    # --------------------------------------------------------

    try:

        today = datetime.strptime(
            current_date,
            "%Y-%m-%d"
        )

    except Exception:

        return "Invalid date"

    # --------------------------------------------------------
    # QUERY PLAN
    # --------------------------------------------------------

    inferred = infer_holiday_plan(
        query
    )

    print(
        "\n🧠 INFERRED PLAN:",
        inferred
    )

    query_type = inferred.get(
        "query_type"
    )

    holiday_name = inferred.get(
        "holiday_name"
    )

    # ========================================================
    # LIST
    # ========================================================

    if query_type == "list":

        holidays = sorted(
            all_holidays,
            key=lambda x: x["date"]
        )

        LAST_HOLIDAY_RESULTS[
            "last_matches"
        ] = holidays

        answer = format_holiday_list(
            holidays
        )

        print(
            "✅ ANSWER:",
            answer
        )

        return answer

    # ========================================================
    # COUNT
    # ========================================================

    if query_type == "count":

        answer = (
            f"There are "
            f"{len(all_holidays)} holidays."
        )

        print(
            "✅ ANSWER:",
            answer
        )

        return answer

    # ========================================================
    # TODAY
    # ========================================================

    if query_type == "today":

        matches = [
            holiday
            for holiday in all_holidays
            if holiday["date"]
            == current_date
        ]

        if matches:

            LAST_HOLIDAY_RESULTS[
                "last_matches"
            ] = matches

            answer = format_holiday_list(
                matches
            )

            print(
                "✅ ANSWER:",
                answer
            )

            return answer

        return "No holiday today."

    # ========================================================
    # EXISTS
    # ========================================================

    if query_type == "exists":

        target_date = today

        q = normalize_text(
            query
        )

        if "tomorrow" in q:

            target_date = (
                today + timedelta(days=1)
            )

        matches = [
            holiday
            for holiday in all_holidays
            if holiday["date"]
            == target_date.strftime(
                "%Y-%m-%d"
            )
        ]

        if matches:

            LAST_HOLIDAY_RESULTS[
                "last_matches"
            ] = matches

            answer = (
                "Yes.\n"
                + format_holiday_list(
                    matches
                )
            )

            print(
                "✅ ANSWER:",
                answer
            )

            return answer

        return "No holiday."

    # ========================================================
    # NEXT
    # ========================================================

    if query_type == "next":

        valid = [
            holiday
            for holiday in all_holidays
            if parse_date(
                holiday["date"]
            )
        ]

        print(
            "VALID HOLIDAYS:",
            len(valid)
        )

        valid = sorted(
            valid,
            key=lambda x: x["date"]
        )

        future = [
            holiday
            for holiday in valid
            if parse_date(
                holiday["date"]
            ) >= today
        ]

        print(
            "FUTURE HOLIDAYS:",
            len(future)
        )

        if not future:

            print(
                "⚠️ NO FUTURE HOLIDAYS "
                "→ USING FALLBACK"
            )

            future = valid

        if holiday_name:

            future = find_by_name(
                future,
                holiday_name
            )

        if not future:

            print(
                "❌ NO MATCHES"
            )

            return "No upcoming holidays."

        next_holiday = future[0]

        LAST_HOLIDAY_RESULTS[
            "last_matches"
        ] = [next_holiday]

        answer = format_holiday(
            next_holiday
        )

        print(
            "✅ ANSWER:",
            answer
        )

        return answer

    # ========================================================
    # LOOKUP
    # ========================================================

    if query_type == "lookup":

        matches = find_by_name(
            all_holidays,
            holiday_name
        )

        print(
            "MATCHES:",
            len(matches)
        )

        if matches:

            LAST_HOLIDAY_RESULTS[
                "last_matches"
            ] = matches

            if len(matches) == 1:

                answer = format_holiday(
                    matches[0]
                )

            else:

                answer = format_holiday_list(
                    matches
                )

            print(
                "✅ ANSWER:",
                answer
            )

            return answer

        return "Holiday not found."

    # ========================================================
    # FOLLOW-UP DATES
    # ========================================================

    if query_type == "followup_dates":

        matches = LAST_HOLIDAY_RESULTS.get(
            "last_matches",
            []
        )

        if not matches:

            return (
                "I don't know which holidays "
                "you're referring to."
            )

        answer = format_holiday_list(
            matches
        )

        print(
            "✅ ANSWER:",
            answer
        )

        return answer

    # ========================================================
    # UNKNOWN QUERY
    # ========================================================

    print(
        "❌ UNKNOWN QUERY TYPE:",
        query_type
    )

    return (
        "I could not understand "
        "the holiday query."
    )