# app/tools/gratuity_engine.py

import re


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_number(value):
    """
    Convert common numeric representations into float.

    Examples:
        50000       -> 50000.0
        "50000"     -> 50000.0
        "₹50,000"   -> 50000.0
        "5.5 years" -> 5.5
    """

    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    value = str(value)

    value = value.replace(",", "")
    value = value.replace("₹", "")
    value = value.strip()

    match = re.search(
        r"(\d+(\.\d+)?)",
        value
    )

    if not match:
        return None

    try:
        return float(
            match.group(1)
        )

    except Exception:
        return None


# ============================================================
# GRATUITY FORMULA
# ============================================================

def calculate_gratuity(years, salary):
    """
    India gratuity formula:

        (15 × last drawn salary × years of service) / 26

    Returns the gratuity rounded to the nearest rupee.
    """

    gratuity = (
        15
        * salary
        * years
        / 26
    )

    return round(gratuity)


# ============================================================
# VALIDATION
# ============================================================

def validate_inputs(years, salary):

    if years is None:
        return (
            "Please provide years of service."
        )

    if salary is None:
        return (
            "Please provide last drawn basic salary."
        )

    if years <= 0:
        return (
            "Years of service must be greater than zero."
        )

    if salary <= 0:
        return (
            "Salary must be greater than zero."
        )

    # Prevent unrealistic service periods.
    if years > 60:
        return (
            "Please provide valid years of service."
        )

    # Prevent unrealistic salary values.
    if salary > 10000000:
        return (
            "Please provide valid salary."
        )

    return None


# ============================================================
# ELIGIBILITY
# ============================================================

def check_eligibility(years):
    """
    Current engine rule:
    minimum 5 years of service.
    """

    return years >= 5


# ============================================================
# MAIN ENGINE
# ============================================================

def process_gratuity(data):
    """
    Expected input:

        {
            "years": number,
            "salary": number
        }

    Example:

        {
            "years": 5,
            "salary": 50000
        }
    """

    if not isinstance(data, dict):
        return (
            "Please provide gratuity information."
        )

    raw_years = data.get(
        "years"
    )

    raw_salary = data.get(
        "salary"
    )

    # ========================================================
    # NORMALIZE
    # ========================================================

    years = normalize_number(
        raw_years
    )

    salary = normalize_number(
        raw_salary
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    validation_error = validate_inputs(
        years,
        salary
    )

    if validation_error:
        return validation_error

    # ========================================================
    # ELIGIBILITY
    # ========================================================

    if not check_eligibility(
        years
    ):

        return (
            "You are not eligible for gratuity yet. "
            "Minimum 5 years of service is required."
        )

    # ========================================================
    # CALCULATION
    # ========================================================

    result = calculate_gratuity(
        years,
        salary
    )

    # ========================================================
    # RESPONSE
    # ========================================================

    return (
        f"For {years:.1f} years of service "
        f"and ₹{salary:,.0f} basic salary, "
        f"your estimated gratuity is "
        f"₹{result:,.0f}."
    )