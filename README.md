# AI Bridge

## Phase 3: Context management and local RAG

The existing generation endpoint is unchanged. Two additional endpoints support
explicit context and a shared in-memory knowledge base.

Ingest already-chunked reference documents (each string is one searchable chunk):

```http
POST /api/v1/rag/ingest
Content-Type: application/json

{"documents": ["Python is a programming language.", "Our support hours are 9am to 5pm."], "metadatas": [{"source": "guide"}, {"source": "policy"}]}
```

Returns HTTP 201 with `{"ids": ["...", "..."], "count": 2}`. Metadata is optional;
when provided, it must contain one dictionary per document. It is retained with
the text but is not searched, returned, or used for filtering. A batch accepts
1?100 nonblank documents, at most 32,000 characters each. Invalid batches are
rejected before any documents are added. Re-ingestion creates new IDs.

```http
POST /api/v1/generate-with-context
Content-Type: application/json

{"query": "What are our support hours?", "explicit_context": "Answer briefly.", "use_rag": true, "k": 3, "max_context_chars": 16000}
```

Returns the same `{"response": "..."}` contract as ordinary generation. Optional
`provider` and `model` fields use the Phase 2 routing rules. `query` is required
and has the same 32,000-character limit as ordinary prompts.

- `explicit_context` is optional (at most 64,000 characters).
- `use_rag` defaults to false; explicit context works without retrieval.
- `k` defaults to 3 and accepts integers from 1 to 20.
- `max_context_chars` defaults to 16,000 and accepts integers from 1 to 64,000.
- When both sources are enabled, explicit context precedes retrieved chunks.
  The combined context is truncated to the character budget; the query is kept.
- Without context or positive search matches, the original query is sent.

The augmented prompt uses:

```text
Context:
{chunks separated by blank lines}

Question: {query}
```

`BaseVectorStore` defines ingestion and retrieval. `InMemoryVectorStore` uses
case-insensitive Unicode word counts and cosine similarity, excluding documents
with zero keyword overlap. Ties retain ingestion order. It needs no database,
embedding model, downloads, or additional runtime packages. It does not provide
semantic matching, stemming, automatic chunking, or metadata filtering.

The store is thread-safe and shared within one application process. It is lost
on restart/reload, and separate server workers have separate stores. Use one
worker for this local-development backend. Documents are shared across callers;
there is no tenant isolation. Use an appropriate persistent store implementation
before depending on durable or multi-worker retrieval. Retrieved/explicit text
is passed as context, not a guarantee that model answers are grounded or that
instructions inside documents will be ignored.

Run verification:

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m pip check
python -m ruff check app tests
python -m ruff format --check app/main.py app/rag/base.py app/rag/memory_store.py app/services/rag_service.py tests/test_rag.py
```

Request bounds and metadata alignment use Pydantic's
[validation facilities](https://pydantic.dev/docs/validation/latest/concepts/validators/).

- [x] Vector store abstraction and local keyword retrieval
- [x] Context augmentation service and bounded prompt assembly
- [x] Ingestion and context generation endpoints
- [x] Store, service, and API regression tests

## Phase 2: Dynamic provider routing

`POST /api/v1/generate` now accepts optional `provider` and `model` fields:

```json
{"prompt": "Explain Python briefly", "provider": "openai", "model": "your-chat-model"}
```

Prompt-only requests remain supported and still return `{"response": "..."}`.
Omitted or null `provider` uses `DEFAULT_PROVIDER` (default: `ollama`). Omitted or
null `model` uses that provider's default: `DEFAULT_MODEL` for Ollama and
`OPENAI_MODEL` for OpenAI-compatible APIs. Explicit overrides apply to one request
only. Provider names are case-insensitive; blank names/models are rejected.

Configure `OPENAI_BASE_URL`, `OPENAI_API_KEY`, and `OPENAI_MODEL` in `.env` before
selecting `openai`. The base URL accepts a server root or a `/v1` suffix, including
trailing slashes. The adapter sends a non-streaming user message to
`/v1/chat/completions` using Bearer authentication. Choose a text/chat-capable
model supported by your backend. For a trusted local server that ignores
credentials, configure a nonempty placeholder key. No OpenAI SDK is required.
Protocol reference: [OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat).

Unknown provider names return 400; blank or non-string selection fields return
422. Missing backend configuration returns 503. Upstream authentication failures
(401/403) raise `ProviderAuthorizationError` and return 502: these are the bridge's
upstream credentials, not authentication failures by its caller. Existing
502/503/504/500 behavior is preserved. Backend response bodies and keys are not
included in error responses. There is no automatic cross-provider retry/failover.

`/health` now validates the configured default provider without making network
calls, and reports its provider/model. An invalid default configuration returns
503. Unused OpenAI configuration does not prevent Ollama requests.

`ProviderFactory.registry` maps names to builders accepting `model_name` and
returning `BaseProvider`. To add a custom backend, implement `BaseProvider` and
register a builder during application setup:

```python
ProviderFactory.registry["custom"] = lambda model: CustomProvider(model=model)
```

No API or `AIService` changes are needed for registered providers. `BaseProvider`
remains unchanged; custom model execution itself is backend-specific.

- [x] OpenAI-compatible HTTP provider
- [x] Registry-based provider factory and configurable default
- [x] Per-request provider/model selection
- [x] Factory, adapter, and API routing regression tests

## Phase 1: HTTP API

Implemented: FastAPI endpoints, request/response validation, provider abstraction,
Ollama generation, typed provider failures, and offline regression tests.
Local RAG is implemented in Phase 3; agents, tools, and ML remain future work.

### Setup (PowerShell)

Use Python 3.10 or later (verified locally with Python 3.13).
Run these commands from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env  # First setup only; preserve an existing .env
```

Install [Ollama](https://ollama.com/download), start its service, and download the
configured model:

```powershell
ollama serve  # Separate terminal; unnecessary if Ollama is already running
ollama pull llama3.2
```

Configuration comes from `.env`; existing process environment variables take
precedence. `APP_ENV` accepts `development` or `production`, `OLLAMA_BASE_URL`
defaults to `http://localhost:11434`, and `DEFAULT_MODEL` defaults to `llama3.2`.
Blank values and invalid base URLs fail startup. Trailing URL slashes are removed.
Use the model name you actually downloaded.

### Start the API

```powershell
python -m app.main
# Development alternative with automatic reload:
uvicorn app.main:app --reload
```

Both serve locally at http://127.0.0.1:8000. Run from the project root;
`python app/main.py` is not a supported entry point. Interactive API documentation
is at `/docs`, and the OpenAPI schema is at `/openapi.json`.

For deployment, run without reload, for example:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API currently has no authentication or rate limiting. Public deployments
need access controls, TLS, and request limits at the deployment boundary.
Generation uses a synchronous worker-thread route, a 5-second connection timeout,
and 120-second HTTP operation timeouts. These are not a total request deadline.

### Endpoints

- `GET /health`: API liveness and configuration validated at startup. Returns
  `status`, `configuration`, `environment`, `provider`, and `model`. It does not
  probe the selected backend or confirm model availability.
- `POST /api/v1/generate`: accepts `{"prompt": "Explain Python briefly"}` and
  returns `{"response": "..."}`. Prompts must be nonblank strings of at most
  32,000 characters after trimming. Extra request fields are rejected.

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/api/v1/generate `
  -Method Post -ContentType 'application/json' `
  -Body '{"prompt":"Reply with one short sentence."}'
```

| Status | Meaning |
| --- | --- |
| 200 | Successful health check or generation |
| 422 | Invalid request; FastAPI validation details |
| 502 | Upstream HTTP failure or malformed/empty model response |
| 503 | Provider unreachable or upstream returned 429/503 |
| 504 | Provider request timed out |
| 500 | Unexpected internal failure |

Provider/internal errors return `{"detail": "..."}`. Upstream response bodies
and unexpected exception details are not exposed to clients. Missing, null,
non-string, and blank response text are treated as upstream failures.

### Tests

```powershell
python -m unittest discover -s tests -v
```

Tests mock HTTP calls and do not require Ollama. They cover successful requests,
validation, provider replacement, URL normalization, upstream errors, timeouts,
malformed responses, and sanitized internal failures.

### Phase 1 completion

- [x] Python project structure and environment configuration
- [x] Provider abstraction and injectable service layer
- [x] Ollama HTTP integration and explicit failure handling
- [x] FastAPI health and generation endpoints
- [x] Pydantic request/response schemas
- [x] Offline API and provider regression tests
- [x] Setup and execution instructions

---


A reusable Python-based AI architecture designed to act as an intelligence layer between an application and different AI/ML model providers.

The goal of **AI Bridge** is to reduce dependency on any single AI model or provider and provide a structured foundation that can evolve from simple LLM integration into RAG, AI agents, machine learning, and custom models.

---

## 🎯 Purpose

Modern applications increasingly integrate AI capabilities, but directly connecting application logic to a specific AI model can create tight coupling.

For example:

```text
Application
    ↓
Ollama
    ↓
LLM
```

If the application later needs to switch from Ollama to another model provider, use a custom model, add RAG, or introduce machine-learning predictions, significant changes may be required in the application layer.

**AI Bridge** aims to solve this by introducing an independent Python-based intelligence layer.

```text
                    Application
                        │
                        ▼
                   AI Bridge
                    (Python)
                        │
             ┌──────────┼──────────┐
             │          │          │
             ▼          ▼          ▼
          Ollama     Other LLMs   ML Models
             │                     │
             ▼                     ▼
        Local Models          Custom Models
```

The application communicates with AI Bridge rather than being tightly coupled to a particular model implementation.

---

# 🌍 Real-World Problem Statement

Business applications such as CRM, HRMS, workshop management, inventory systems, and other enterprise platforms generate large amounts of structured and unstructured data.

Integrating AI directly into these applications can create several problems:

* Tight coupling between business logic and AI providers
* Difficulty switching between local and cloud-based models
* Increasing complexity as AI features grow
* Difficulty introducing RAG and contextual data retrieval
* Difficulty integrating machine-learning models
* Lack of a common interface for different AI capabilities
* Difficulty maintaining AI-related logic separately from the core application

The problem is therefore:

> **How can we create a reusable AI architecture that allows an existing application to integrate different AI/ML models without making the application tightly dependent on a particular model or provider?**

AI Bridge is an attempt to provide a solution to this problem.

---

# 💡 Proposed Solution

AI Bridge will act as an independent **AI/ML intelligence layer** between an application and its AI/ML capabilities.

For example:

```text
┌───────────────────────┐
│      Application      │
│                       │
│ Laravel / Node / etc. │
└───────────┬───────────┘
            │
            │ API
            ▼
┌───────────────────────┐
│       AI Bridge       │
│        Python         │
│                       │
│ Model Integration     │
│ Context Management    │
│ RAG                   │
│ AI Tools              │
│ Agents                │
│ ML Models             │
└───────────┬───────────┘
            │
       ┌────┴─────┐
       ▼          ▼
    Ollama     Other Models
```

This allows the application layer and AI layer to evolve independently.

---

# 🤖 Possible AI/ML Approach

The project will be developed incrementally.

## Phase 1 — LLM Integration

Start with an existing local model provider such as Ollama.

```text
Application
     ↓
Python AI Bridge
     ↓
Ollama
     ↓
Local LLM
```

The first objective is to create a clean interface through which an application can send a request to the AI Bridge and receive a response without directly interacting with Ollama.

---

## Phase 2 — Model Abstraction

Introduce a provider abstraction so that the architecture is not dependent on Ollama.

Conceptually:

```text
                  AI Bridge
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
       Ollama     Cloud LLM   Custom Model
```

A model provider should be replaceable without requiring major changes to the application layer.

---

## Phase 3 — Context & RAG

Introduce contextual information and Retrieval-Augmented Generation (RAG).

```text
Application Data
       ↓
Data Retrieval
       ↓
Relevant Context
       ↓
AI Bridge
       ↓
LLM
       ↓
Response
```

This will allow AI responses to be based on application-specific information rather than only the model's existing knowledge.

---

## Phase 4 — AI Tools & Dynamic Execution

Introduce controlled tools that allow the AI system to interact with application capabilities.

For example:

```text
User
 ↓
AI Bridge
 ↓
AI Model
 ↓
Determine required action
 ↓
Tool
 ↓
Application API
 ↓
Result
 ↓
AI Model
 ↓
Final Response
```

Potential tools could include:

* Search customers
* Retrieve enquiries
* Generate reports
* Create follow-up tasks
* Retrieve sales information
* Analyze inventory
* Query approved application data

The AI should not receive unrestricted access to the application's database.

Tools should operate through controlled interfaces and permission checks.

---

# 📊 Phase 5 — Machine Learning

Once sufficient data is available, Python can be used for traditional AI/ML capabilities in addition to LLMs.

Possible applications include:

* Lead conversion prediction
* Sales forecasting
* Customer segmentation
* Customer churn prediction
* Inventory forecasting
* Dealer performance analysis
* Anomaly detection
* Recommendation systems

Example:

```text
Historical Data
      ↓
Data Processing
      ↓
Feature Engineering
      ↓
ML Model
      ↓
Prediction
      ↓
AI Bridge
      ↓
Application
```

---

# 🧠 Phase 6 — Custom / Fine-Tuned Models

The architecture should eventually support custom or fine-tuned models.

The long-term objective is not necessarily to build a large language model from scratch.

Instead, the project can progressively explore:

```text
Existing Model
      ↓
Domain Data
      ↓
Fine-tuning / Customization
      ↓
Specialized Model
      ↓
AI Bridge
```

This creates a path from using existing models to developing specialized models for specific business problems.

---

# 🏗️ Target Architecture

The initial target architecture is:

```text
                         Application
                              │
                              │ API
                              ▼
                    ┌──────────────────┐
                    │    AI Bridge     │
                    │      Python      │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
           Providers        RAG        ML Engine
              │              │              │
       ┌──────┴──────┐       │              │
       ▼             ▼       ▼              ▼
    Ollama       Other LLM  Data       Custom Models
```

The architecture should remain modular so individual components can be introduced as the project evolves.

---

# 🔧 Initial Technology Direction

The project will initially explore:

* **Python** — AI/ML application layer
* **Ollama** — local LLM runtime
* **HTTP APIs** — communication with external applications
* **Git/GitHub** — version control
* **Future:** RAG
* **Future:** ML frameworks
* **Future:** AI agents and tool execution
* **Future:** Custom/fine-tuned models

Specific frameworks and libraries will be selected as implementation requirements become clearer.

---

# 📁 Planned Project Structure

The project will evolve toward a structure similar to:

```text
ai-bridge/
│
├── README.md
├── .gitignore
├── requirements.txt
│
├── app/
│   ├── main.py
│   │
│   ├── providers/
│   │   ├── ollama.py
│   │   └── ...
│   │
│   ├── models/
│   │   └── ...
│   │
│   ├── agents/
│   │   └── ...
│   │
│   ├── tools/
│   │   └── ...
│   │
│   └── rag/
│       └── ...
│
└── tests/
    └── ...
```

This structure is a target and will change as the project develops.

---

# 🚀 Mini Project

The initial mini-project will be to build a simple AI Bridge that can:

1. Receive an AI request from an external application.
2. Process the request through Python.
3. Communicate with an AI model provider.
4. Return a structured response.
5. Keep the application independent from the underlying model provider.

The first model provider will be **Ollama**.

Future providers and AI/ML capabilities will be added incrementally.

---

# 🗺️ Learning Roadmap

The project will be developed alongside Python and AI/ML learning.

```text
Python Fundamentals
        ↓
Python APIs
        ↓
Project Structure
        ↓
Ollama Integration
        ↓
Model Abstraction
        ↓
Data Processing
        ↓
RAG
        ↓
AI Tools / Agents
        ↓
Machine Learning
        ↓
Custom / Fine-Tuned Models
```

The objective is to learn the concepts by applying them to a real-world architecture rather than treating each concept as an isolated exercise.

---

# 🎯 Long-Term Vision

AI Bridge is intended to become a reusable architecture that can be adapted to different applications.

A future application should ideally be able to integrate the architecture as follows:

```text
Existing Application
        │
        ▼
     AI Bridge
        │
        ├── Local Models
        ├── Cloud Models
        ├── RAG
        ├── AI Agents
        ├── ML Models
        └── Custom Models
```

Only application-specific customization should be required to connect the AI Bridge to a particular business system.

---

# 📌 Current Status

**Stage:** Phase 3 local context and RAG implemented

* [x] Python environment available
* [x] Git repository created
* [x] Real-world problem identified
* [x] Proposed architecture documented
* [x] Initial AI/ML approach identified
* [x] Python project structure
* [x] Ollama integration
* [x] Application API
* [x] Model abstraction
* [x] RAG (local in-memory retrieval)
* [ ] AI tools
* [ ] Machine-learning experiments
* [ ] Custom model experiments

---

# 📚 Project Objective

The primary objective of this project is to build a practical understanding of Python and Applied AI/ML by developing a reusable AI architecture that can solve real-world application integration problems.

This project will evolve as new concepts are learned and tested.
