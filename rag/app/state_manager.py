# app/state_manager.py

from collections import defaultdict
import time


# =============================
# 🧠 GLOBAL STATE STORE
# =============================

_state_store = defaultdict(dict)


# =============================
# CONFIG
# =============================

MEMORY_DECAY = 0.85
MAX_MEMORY = 5


# =============================
# 🧠 INIT STATE
# =============================

def init_state(client_id: str):

    if client_id not in _state_store:

        _state_store[client_id] = {
            "intent": None,
            "policy": None,
            "entity": None,
            "topic": None,
            "use_history": "none",
            "confidence": 0.0,
            "flow": None,
            "memory": [],
            "last_updated": time.time()
        }

    return _state_store[client_id]


# =============================
# 🧠 GET STATE
# =============================

def get_state(client_id: str):
    return init_state(client_id)


# =============================
# 🔄 UPDATE STATE
# =============================

def update_state(client_id: str, thought: dict):

    state = init_state(client_id)

    # decay memory weights
    for item in state["memory"]:
        item["weight"] *= MEMORY_DECAY

    # update fields from thought
    state["intent"] = thought.get("intent", state["intent"])
    state["policy"] = thought.get("policy", state["policy"])
    state["entity"] = thought.get("entity", state["entity"])
    state["topic"] = thought.get("topic", state["topic"])
    state["use_history"] = thought.get("use_history", "none")
    state["confidence"] = thought.get("confidence", 0.0)

    # push new memory snapshot
    state["memory"].append({
        "intent": state["intent"],
        "policy": state["policy"],
        "entity": state["entity"],
        "topic": state["topic"],
        "weight": 1.0
    })

    # trim memory
    state["memory"] = sorted(
        state["memory"],
        key=lambda x: x["weight"],
        reverse=True
    )[:MAX_MEMORY]

    state["last_updated"] = time.time()

    return state


# =============================
# 🔄 FLOW CONTROL
# =============================

def set_flow(client_id: str, flow: dict):
    state = init_state(client_id)
    state["flow"] = flow


def get_flow(client_id: str):
    state = init_state(client_id)
    return state.get("flow")


def clear_flow(client_id: str):
    state = init_state(client_id)
    state["flow"] = None


# =============================
# 🧠 ENTITY HANDLING
# =============================

def set_entity(client_id: str, entity: str):
    state = init_state(client_id)
    state["entity"] = entity


def get_entity(client_id: str):
    state = init_state(client_id)
    return state.get("entity")


# =============================
# 🧠 MEMORY ACCESS
# =============================

def get_dominant_context(client_id: str):

    state = init_state(client_id)

    if not state["memory"]:
        return None

    top = max(state["memory"], key=lambda x: x["weight"])

    return {
        "intent": top["intent"],
        "policy": top["policy"],
        "entity": top["entity"],
        "topic": top["topic"]
    }


# =============================
# 🧹 RESET STATE (OPTIONAL)
# =============================

def reset_state(client_id: str):
    if client_id in _state_store:
        del _state_store[client_id]