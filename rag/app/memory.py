# app/memory.py

from collections import defaultdict

# =============================
# CHAT HISTORY
# =============================

conversation_history = defaultdict(list)

# =============================
# CONVERSATION STATE
# =============================

conversation_states = {}


# =============================
# HISTORY
# =============================

def add_message(client_id, role, content):

    conversation_history[client_id].append({
        "role": role,
        "content": content
    })

    # keep memory small
    if len(conversation_history[client_id]) > 20:

        conversation_history[client_id] = (
            conversation_history[client_id][-20:]
        )


def get_history(client_id):

    return conversation_history.get(
        client_id,
        []
    )


def clear_history(client_id):

    if client_id in conversation_history:

        del conversation_history[client_id]


# =============================
# STATE
# =============================

def get_state(client_id):

    return conversation_states.get(
        client_id,
        {}
    )


def save_state(client_id, state):

    conversation_states[client_id] = state


def clear_state(client_id):

    if client_id in conversation_states:

        del conversation_states[client_id]