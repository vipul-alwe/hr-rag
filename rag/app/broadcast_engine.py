# app/broadcast_engine.py

import os
import requests

from app.db import get_cursor


# =============================
# ENV CONFIG
# =============================

API_TOKEN = os.getenv(
    "API_TOKEN"
)

API_URL = os.getenv(
    "API_URL"
)

PHONE_NUMBER_ID = os.getenv(
    "PHONE_NUMBER_ID"
)

TEMPLATE_NAME = "hr_broadcast_update"


# =============================
# SEND TEMPLATE MESSAGE
# =============================

def send_template_message(
    phone_number: str,
    employee_name: str,
    message: str
):

    url = (
        f"{API_URL}/"
        f"{PHONE_NUMBER_ID}/messages"
    )

    headers = {

        "Authorization":
        f"Bearer {API_TOKEN}",

        "Content-Type":
        "application/json"

    }

    payload = {

        "messaging_product": "whatsapp",

        "to": phone_number,

        "type": "template",

        "template": {

            "name": TEMPLATE_NAME,

            "language": {
                "code": "en"
            },

            "components": [

                {
                    "type": "body",

                    "parameters": [

                        {
                            "type": "text",
                            "text": employee_name
                        },

                        {
                            "type": "text",
                            "text": message
                        }

                    ]
                }

            ]
        }
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload
    )

    return response.json()


# =============================
# SEND BROADCAST
# =============================

def send_broadcast(
    client_id: str,
    message: str
):

    with get_cursor() as cur:

        cur.execute(
            """
            SELECT
                employee_name,
                phone_number
            FROM employees
            WHERE client_id = %s
            AND phone_number IS NOT NULL
            """,
            (client_id,)
        )

        rows = cur.fetchall()

    results = []

    for row in rows:

        employee_name = row[0]
        phone_number = row[1]

        try:

            result = send_template_message(
                phone_number=phone_number,
                employee_name=employee_name,
                message=message
            )

            results.append({

                "employee_name":
                employee_name,

                "phone_number":
                phone_number,

                "status":
                "success",

                "response":
                result

            })

        except Exception as e:

            results.append({

                "employee_name":
                employee_name,

                "phone_number":
                phone_number,

                "status":
                "failed",

                "error":
                str(e)

            })

    return {

        "success": True,

        "total_sent":
        len(results),

        "results":
        results

    }