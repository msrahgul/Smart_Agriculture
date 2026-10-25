# AgriDecision: Autonomous Precision Agriculture Decision Support System

AgriDecision is a goal-directed, multi-agent decision support prototype for Tamil Nadu agriculture. A farmer states a goal (for example, assess rice pest risk in Thanjavur, compare crop options, or estimate crop profit). The planner extracts farm context, selects a bounded plan, delegates evidence gathering to domain specialists, and returns a recommendation with the tools and evidence used. It combines historical agricultural data, machine-learning models, weather, market data, an LLM router/formatter, and session memory.

This is a decision-support prototype. Predictions and cost/profit values are estimates; users should validate them against current field conditions and local agricultural extension guidance.

## What it can do

- Plan and coordinate crop, water, pest-risk, yield, soil-nutrition, and farm-economics specialists.
- Remember district, crop, soil, season, and month within a chat session.
- Query crop suitability, district profiles, rainfall, pest risk, yield, fertilizer guidance, costs, profit, and market prices through registered tools.
- Classify uploaded soil images and incorporate the result into session context.
- English-only interface for this release, with weather context and a scenario simulator. Tamil UI/API responses are disabled behind a feature flag for later restoration.
- Return a plan trace with specialist names, tool names, and completion status for planned goals.

## Agent architecture and planning

The request flow is:

1. **Goal formulation:** detect a supported farm goal and resolve its district, crop, soil, and season from the message and session memory.
2. **Bounded planning:** select only the required tools from a fixed plan library. For example, a crop decision may request suitability, rainfall, and profit evidence; pest assessment invokes the pest specialist.
3. **Specialist execution:** domain workers call isolated functions in `tools.py`, which access `data_engine.py`, trained models, weather, or market data.
4. **Coordination:** the planner gathers worker outputs, records failures, and synthesizes one evidence-backed response. If required context is missing or no supported goal is recognized, the existing LLM tool router handles the request.
5. **Memory and feedback:** district/crop context is retained in the chat session and can guide follow-up plans.

The multi-agent prototype uses named specialist workers coordinated by one deterministic planner. It is intentionally bounded and auditable; it is not a set of independent LLMs negotiating with each other. Inspectable plan metadata is returned by `/chat` and the `done` event of `/chat_stream`.

## Course rubric alignment

| Rubric / outcome | Project evidence |
| --- | --- |
| CO1: planning and goals | `GOAL_PLANS`, `_plan_for_query`, context requirements, bounded tool plans |
| CO2: architecture | LLM router and formatter, registered tools, session memory, ML/data services |
| CO3: functioning system | Flask chat, streaming, specialist tools, image classification, weather and market integrations |
| CO4 / CO6: evaluation | Evaluation protocol below; record accuracy, task completion, latency, tool failures, and robustness before claiming results |
| CO5: multi-agent prototype | Named specialist workers, task allocation, shared request context, tool-level coordination, status trace |
| Innovation | Context-aware farm decision plans combine agronomic suitability, water, pest, and economics evidence |
| Presentation / viva | Architecture and limitations are documented here; demo supported tasks and inspect returned plan trace |
| Report preparation | This README includes system design, rubric mapping, evaluation protocol, and failure modes |

## Evaluation protocol (report actual measured results)

Use a fixed, versioned set of cases covering each goal: crop choice, pest risk, yield, rainfall, fertilizer, profit, farm overview, missing district, missing crop, unknown district, and LLM/data-service unavailable. Run each case at least five times where latency is measured and retain the input, expected goal, tool plan, output, and error.

Report these metrics:

- **Goal accuracy:** correctly routed supported goals / all labeled cases.
- **Task completion:** cases with all required evidence returned / supported cases.
- **Tool success rate:** successful tool calls / attempted tool calls.
- **Plan efficiency:** executed tool calls / calls expected by the plan specification.
- **End-to-end latency:** median and 95th percentile, separated by planned and LLM-routed requests.
- **Robustness:** completion rate under missing context, invalid district/crop, unavailable model/API, and malformed tool results.
- **Recommendation quality:** agronomist or instructor rubric scoring evidence relevance, clarity, and safe uncertainty handling.

Do not treat a successful HTTP response as agricultural accuracy. Compare predictions with held-out labeled data where available, document dataset/model versions, and report per-class precision/recall/F1 for pest classification. The repository does not include measured evaluation results; populate them after running the protocol.

## Failure modes and safeguards

- Missing required context falls through to the LLM router or prompts for clarification; the planner does not execute a crop-specific estimate without a crop.
- Tool errors are recorded as failed in the plan trace. If no specialist returns evidence, the existing route is allowed to handle the request.
- Model output can be stale or affected by training/runtime version mismatch; check `/health` and model logs.
- Weather and market availability may vary. Historical datasets are not real-time observations.
- Crop profit and suitability estimates depend on source data and assumptions. They are guidance, not guarantees or pesticide prescriptions.
- LLM fallback text may be incorrect. Prefer structured tool-backed outputs for field decisions and verify high-impact advice locally.

## Setup

Requirements: Python 3.10+ (use the included venv where configured), dependencies from `requirements.txt`, and optional Ollama/Gemini configuration for language-model features.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

On Windows, `run_server.ps1` starts the server with the repository virtual environment. Open `http://127.0.0.1:5000/`; use `/health` to inspect model/service readiness.

### Ollama setup (first run)

Ollama stores this project's models under the ignored `.ollama/models/` folder on the project drive, and the app uses `http://127.0.0.1:11435` so it does not depend on Ollama's default C: model store.

1. Start the project Ollama service in a PowerShell window: `powershell -ExecutionPolicy Bypass -File .\run_ollama.ps1`.
2. In another PowerShell window, download the configured router and response models: `powershell -ExecutionPolicy Bypass -File .\pull_ollama_models.ps1`.
3. Start AgriDecision with `.un_server.ps1`. The launcher starts the project Ollama service automatically on later runs.

### Language feature flag

The current interface and chat API are English-only. To restore the previous Tamil option later, set `app.config["TAMIL_LANGUAGE_ENABLED"] = True` in `app.py`; the UI toggle and translated responses will become available together.

## Main files

- `app.py` — Flask UI/API, chat sessions, weather, and operational endpoints.
- `agent.py` — goal planner, specialist orchestration, LLM routing, formatting, and memory.
- `tools.py` — specialist tool registry and function adapters.
- `data_engine.py` — agricultural data retrieval and estimators.
- `ml_models.py`, `models/` — trained yield and pest models; soil classifier is in `soil_classifier.py`.
- `templates/`, `static/` — browser dashboard and chat client.
- `data/`, `tn_smart_farming_dataset/` — agricultural datasets.

## Course context

25AI2014 – Agentic AI · B.Tech CSE-AIML · Semester VII · Academic Year 2026–2027. Project topic: **Autonomous Precision Agriculture Decision Support System**.
