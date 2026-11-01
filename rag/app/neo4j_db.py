from neo4j import GraphDatabase
import os


# ==========================
# CONFIG
# ==========================

NEO4J_URI = os.getenv(
    "NEO4J_URI",
    "bolt://localhost:7687"
)

NEO4J_USER = os.getenv(
    "NEO4J_USER",
    "neo4j"
)

NEO4J_PASSWORD = os.getenv(
    "NEO4J_PASSWORD",
    "password"
)


# ==========================
# DRIVER
# ==========================

driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(
        NEO4J_USER,
        NEO4J_PASSWORD
    )
)


# ==========================
# CONNECTION TEST
# ==========================

def test_neo4j_connection():

    with driver.session() as session:

        result = session.run(
            "RETURN 'Neo4j connected' AS message"
        )

        return result.single()["message"]