from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    Form,
    Request,
    Query,
    Header
)

from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from typing import Optional

from fastapi.responses import JSONResponse


from app.tools.ingest_engine import ingest_file , ingest_document
from app.orchestrator import ask

from app.broadcast_engine import send_broadcast

from app.db import (
    resolve_client_from_group,
    get_cursor
)

from dotenv import load_dotenv

import os
import shutil
import uuid
import requests

from datetime import datetime


load_dotenv()

app = FastAPI(
    title="Multi-Tenant RAG Service"
)

# =============================
# CORS
# =============================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================
# ENV
# =============================

VERIFY_TOKEN = os.getenv(
    "WHATSAPP_VERIFY_TOKEN",
    "mytoken"
)

API_TOKEN = os.getenv("API_TOKEN")

PHONE_NUM_ID = os.getenv("PHONE_NUM_ID")

API_URL = os.getenv(
    "API_URL",
    "https://graph.facebook.com/v18.0"
)

HR_API_KEY = os.getenv(
    "HR_API_KEY",
    "dev-secret"
)

# =============================
# MODELS
# =============================

class AskRequest(BaseModel):

    group_id: str
    question: str
    current_date: Optional[str] = None


class IngestRequest(BaseModel):

    client_id: str

    content: Optional[str] = None

    file_path: Optional[str] = None

    policy_name: Optional[str] = None

    section_title: Optional[str] = None


class AlertRequest(BaseModel):

    group_id: str
    message: str


class EmployeeCreateRequest(BaseModel):

    group_id: str
    name: str
    phone_number: str

    opted_in: Optional[bool] = False

    opt_in_source: Optional[str] = "admin"


class EmployeeDeleteRequest(BaseModel):

    group_id: str
    phone_number: str


# =============================
# HELPERS
# =============================

def get_current_date():

    return datetime.now().strftime(
        "%Y-%m-%d"
    )


def upsert_employee(
    client_id: str,
    name: str,
    phone: str,
    opted_in: bool,
    source: str
):

    with get_cursor(commit=True) as cur:

        cur.execute(
            """
            INSERT INTO employees
            (
                name,
                phone_number,
                client_id,
                opted_in,
                opted_in_at,
                opt_in_source
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                CASE WHEN %s THEN NOW() ELSE NULL END,
                %s
            )

            ON CONFLICT (phone_number)

            DO UPDATE SET
                name = EXCLUDED.name,
                client_id = EXCLUDED.client_id,
                opted_in = EXCLUDED.opted_in,

                opted_in_at =
                    CASE
                        WHEN EXCLUDED.opted_in
                        THEN NOW()
                        ELSE employees.opted_in_at
                    END,

                opt_in_source = EXCLUDED.opt_in_source,
                updated_at = NOW(),
                is_active = TRUE

            RETURNING
                id,
                phone_number,
                opted_in
            """,
            (
                name,
                phone,
                client_id,
                opted_in,
                opted_in,
                source
            )
        )

        return cur.fetchone()


def deactivate_employee(
    client_id: str,
    phone: str
):

    with get_cursor(commit=True) as cur:

        cur.execute(
            """
            UPDATE employees

            SET
                is_active = FALSE,
                updated_at = NOW()

            WHERE client_id = %s
            AND phone_number = %s

            RETURNING
                id,
                phone_number
            """,
            (
                client_id,
                phone
            )
        )

        return cur.fetchone()


# =============================
# HEALTH
# =============================

@app.get("/health")
def health_check():

    return {
        "status": "ok"
    }


# =============================
# CORE
# =============================

@app.post("/ask")
def ask_question(req: AskRequest):

    client_id = resolve_client_from_group(
        req.group_id
    )

    if not client_id:

        raise HTTPException(
            status_code=404,
            detail="Unknown group"
        )

    current_date = (
        req.current_date
        or get_current_date()
    )

    answer = ask(
        client_id,
        req.question,
        current_date
    )

    return {
        "answer": answer
    }


# =============================
# INGEST TEXT
# =============================

@app.post("/ingest")
def ingest(req: IngestRequest):

    # =============================
    # FILE INGEST
    # =============================

    if req.file_path:

        chunks = ingest_file(
            client_id=req.client_id,
            path=req.file_path
        )

        return {
            "chunks_ingested": chunks
        }

    # =============================
    # TEXT INGEST
    # =============================

    if req.content:

        ingest_document(
            client_id=req.client_id,
            content=req.content,
            policy_name=req.policy_name,
            section_title=req.section_title
        )

        return {
            "status": "ok"
        }

    raise HTTPException(
        status_code=400,
        detail="Provide content or file_path"
    )


# =============================
# INGEST FILE UPLOAD
# =============================

@app.post("/ingest/upload")
async def ingest_upload(

    client_id: str = Form(...),

    file: UploadFile = File(...),

    policy_name: Optional[str] = Form(None)

):

    uploads_dir = os.path.join(
        os.getcwd(),
        "uploads"
    )

    os.makedirs(
        uploads_dir,
        exist_ok=True
    )

    safe_name = (
        f"{uuid.uuid4().hex}_{file.filename}"
    )

    dest_path = os.path.join(
        uploads_dir,
        safe_name
    )

    with open(dest_path, "wb") as out:

        shutil.copyfileobj(
            file.file,
            out
        )

    chunks = ingest_file(
        client_id=client_id,
        path=dest_path
    )

    return {
        "chunks_ingested": chunks,
        "policy_name": policy_name
    }


# =============================
# ALERT API
# =============================

@app.post("/alerts/send")
def send_alert(
    req: AlertRequest,
    x_api_key: str = Header(...)
):

    if x_api_key != HR_API_KEY:

        raise HTTPException(
            status_code=403,
            detail="Unauthorized"
        )

    client_id = resolve_client_from_group(
        req.group_id
    )

    if not client_id:

        raise HTTPException(
            status_code=404,
            detail="Unknown group"
        )

    message = req.message.strip()

    if not message:

        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )

    if len(message) > 900:

        raise HTTPException(
            status_code=400,
            detail="Message too long"
        )

    result = send_broadcast(
        client_id=client_id,
        message=message
    )

    return {

        "status": "sent",

        "total_sent":
        result["total_sent"],

        "results":
        result["results"]

    }


# =============================
# EMPLOYEE APIs
# =============================

@app.post("/employees/add")
def add_employee(
    req: EmployeeCreateRequest,
    x_api_key: str = Header(...)
):

    if x_api_key != HR_API_KEY:

        raise HTTPException(
            status_code=403,
            detail="Unauthorized"
        )

    client_id = resolve_client_from_group(
        req.group_id
    )

    if not client_id:

        raise HTTPException(
            status_code=404,
            detail="Unknown group"
        )

    phone = req.phone_number.strip()

    if not phone.isdigit():

        raise HTTPException(
            status_code=400,
            detail="Phone must be digits only"
        )

    if len(phone) < 10 or len(phone) > 15:

        raise HTTPException(
            status_code=400,
            detail="Invalid phone number"
        )

    row = upsert_employee(
        client_id=client_id,
        name=req.name.strip(),
        phone=phone,
        opted_in=bool(req.opted_in),
        source=req.opt_in_source or "admin"
    )

    return {
        "status": "saved",
        "employee": {
            "id": str(row[0]),
            "phone_number": row[1],
            "opted_in": row[2]
        }
    }


@app.post("/employees/remove")
def remove_employee(
    req: EmployeeDeleteRequest,
    x_api_key: str = Header(...)
):

    if x_api_key != HR_API_KEY:

        raise HTTPException(
            status_code=403,
            detail="Unauthorized"
        )

    client_id = resolve_client_from_group(
        req.group_id
    )

    if not client_id:

        raise HTTPException(
            status_code=404,
            detail="Unknown group"
        )

    phone = req.phone_number.strip()

    if not phone.isdigit():

        raise HTTPException(
            status_code=400,
            detail="Phone must be digits only"
        )

    row = deactivate_employee(
        client_id,
        phone
    )

    if not row:

        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    return {
        "status": "removed",
        "employee": {
            "id": str(row[0]),
            "phone_number": row[1]
        }
    }


# =============================
# WHATSAPP SEND
# =============================

def send_whatsapp_message(
    to: str,
    message: str
):

    url = (
        f"{API_URL}/"
        f"{PHONE_NUM_ID}/messages"
    )

    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {
            "body": message
        }
    }

    requests.post(
        url,
        json=payload,
        headers=headers
    )


# =============================
# WEBHOOK VERIFY
# =============================

@app.get("/webhook")
def verify_webhook(

    mode: str = Query(
        None,
        alias="hub.mode"
    ),

    challenge: str = Query(
        None,
        alias="hub.challenge"
    ),

    verify_token: str = Query(
        None,
        alias="hub.verify_token"
    )
):

    if (
        mode == "subscribe"
        and verify_token == VERIFY_TOKEN
    ):

        return int(challenge)

    raise HTTPException(
        status_code=403,
        detail="Verification failed"
    )


# =============================
# WEBHOOK
# =============================

@app.post("/webhook")
async def handle_webhook(req: Request):

    data = await req.json()

    try:

        value = (
            data["entry"][0]
            ["changes"][0]
            ["value"]
        )

        if "messages" not in value:

            return {
                "status": "no_message"
            }

        msg = value["messages"][0]

        sender = msg["from"]

        if msg.get("type") != "text":

            return {
                "status": "ignored"
            }

        text = msg["text"]["body"]

        group_id = "test_group_1"

        client_id = resolve_client_from_group(
            group_id
        )

        answer = ask(
            client_id,
            text,
            get_current_date()
        )

        send_whatsapp_message(
            sender,
            answer
        )

    except Exception as e:

        print("Webhook error:", e)

    return {
        "status": "ok"
    }

# =============================
# DOCUMENT APIs
# =============================

@app.get("/documents/{client_id}")
def get_documents(client_id: str):

    with get_cursor() as cur:

        cur.execute(
            """
            SELECT
                id,
                client_id,
                content,
                policy_name,
                section_title
            FROM documents
            WHERE client_id = %s
            ORDER BY id DESC
            """,
            (client_id,)
        )

        rows = cur.fetchall()

    documents = []

    for row in rows:

        documents.append({
            "id": str(row[0]),
            "client_id": row[1],
            "content": row[2],
            "policy_name": row[3],
            "section_title": row[4]
        })

    return JSONResponse(content=documents)


@app.delete("/documents/{document_id}")
def delete_document(document_id: str):

    with get_cursor(commit=True) as cur:

        cur.execute(
            """
            DELETE FROM documents
            WHERE id = %s
            RETURNING id
            """,
            (document_id,)
        )

        deleted = cur.fetchone()

    if not deleted:

        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    return {
        "status": "deleted",
        "document_id": document_id
    }