# HR RAG

### WhatsApp-Powered AI HR Assistant

HR RAG is an AI-powered HR knowledge assistant designed to make organisational information accessible through WhatsApp.

The system combines Retrieval-Augmented Generation (RAG), semantic search, graph-based organisational intelligence and locally hosted Large Language Models to answer employee queries using internal organisational knowledge.

Employees can interact with the assistant through a familiar messaging interface to retrieve HR information, understand company policies and explore organisational structures using natural language.

## Overview

Accessing HR information often involves navigating multiple documents, contacting HR representatives or searching through internal resources.

HR RAG aims to simplify this experience by introducing a conversational AI interface over WhatsApp.

Behind the messaging interface, a hybrid retrieval architecture combines document-based knowledge retrieval with structured employee and organisational relationship data.

## System Architecture

```text
             Employee
                 |
                 v
              WhatsApp
                 |
                 v
          WhatsApp Business API
                 |
                 v
             Webhook
                 |
                 v
            Python Backend
                 |
                 v
           Intent Detection
                 |
          +------+------+
          |             |
          v             v
     HR Knowledge   Employee Engine
       Retrieval         |
          |              |
          v              v
    PostgreSQL         Neo4j
      + pgvector      Graph Data
          |              |
          +------+-------+
                 |
                 v
          Context Assembly
                 |
                 v
             Ollama LLM
                 |
                 v
          Response Generation
                 |
                 v
              WhatsApp
                 |
                 v
              Employee
```

## Core Capabilities

### 1. WhatsApp Integration

WhatsApp serves as the primary employee interaction channel.

The intended integration enables:

- Natural language HR queries.
- Conversational access to organisational knowledge.
- Employee-specific query handling.
- Delivery of AI-generated responses through messaging.

### 2. Retrieval-Augmented Generation

The RAG pipeline retrieves relevant information from internal knowledge sources before generating responses.

Core components:

- Document ingestion.
- Text chunking and preprocessing.
- Embedding generation.
- Semantic similarity search.
- Context retrieval.
- LLM-based response generation.

### 3. Employee & Organisational Intelligence

Neo4j provides a graph-based representation of employees and organisational relationships.

This supports queries involving:

- Employee information.
- Department structures.
- Reporting hierarchies.
- Manager relationships.
- Organisational structure.

### 4. Hybrid Database Architecture

The system separates semantic knowledge retrieval from organisational relationship queries.

| Database | Responsibility |
|---|---|
| PostgreSQL | Employee records and structured data |
| pgvector | Document embeddings and semantic retrieval |
| Neo4j | Employee relationships and organisational hierarchy |

### 5. Local LLM Infrastructure

Ollama provides the local model inference layer.

The development environment has explored:

- Mistral
- Mistral Nemo
- DeepSeek-R1 14B
- nomic-embed-text for embeddings

This architecture explores running enterprise-oriented AI applications using locally hosted models.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python |
| Messaging Interface | WhatsApp Business API |
| Database | PostgreSQL |
| Vector Search | pgvector |
| Graph Database | Neo4j |
| LLM Runtime | Ollama |
| Embeddings | nomic-embed-text |
| Infrastructure | Docker Compose |

## Multi-Tenant Architecture

The system is designed to support multiple organisational environments.

Tenant-specific data separation allows the architecture to be extended across different organisations while maintaining contextual boundaries.

The application also explores short-lived conversational context, with a proposed 30-minute retention window for session information.

## Infrastructure

The local development environment uses Docker Compose.

| Service | Technology |
|---|---|
| Relational Database | pgvector/pgvector:pg16 |
| Graph Database | Neo4j |

Development ports:

- PostgreSQL: 5432
- Neo4j Browser: 7474
- Neo4j Bolt: 7687

## Engineering Focus

The project explores:

- WhatsApp-based conversational AI.
- Enterprise Retrieval-Augmented Generation.
- Hybrid vector and graph retrieval.
- Multi-tenant AI architecture.
- Local LLM inference.
- Employee relationship modelling.
- Conversational context management.
- Natural language interfaces for internal enterprise systems.

## Project Status

An evolving AI engineering project focused on bringing enterprise HR knowledge and organisational intelligence into an accessible WhatsApp-based conversational interface.

## Developer

**Vipul Alwe**

AI & Automation Engineer | Generative AI | RAG Systems | LLM Engineering

[GitHub Profile](https://github.com/vipul-alwe)

---

*HR RAG — Making organisational knowledge accessible through conversation.*
