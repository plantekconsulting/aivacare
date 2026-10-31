# AivaCare: Agentic AI Continuous Care (Roadshow Prototype)

A continuous-care platform for fatty liver disease (MASLD/MASH) built for LiverWell Clinic. Everything runs on **synthetic data**. This is a demonstration system, not for clinical use.

**Design principle:** rules decide, AI explains, physicians approve.

| Surface | Tech | Path |
|---|---|---|
| Patient mobile app | Expo / React Native | `apps/mobile` |
| Patient web portal, clinician dashboard, presenter controls | Next.js, Tailwind, Recharts, Vercel AI SDK UI | `apps/web` |
| API, agents, rules, workflows | FastAPI, Claude API, FastMCP, LangGraph, pgvector | `services/api` |
| System of record | HAPI FHIR R4 | Docker |

## Architecture at a glance
- **2 agents:** the Patient Care Agent (patient-scoped tools) and the Clinician Copilot (panel-scoped tools). Both use a streaming Claude tool loop.
- **MCP tool layer:** five FastMCP servers (fhir, knowledge, insights, workflow, document) are composed per request. Identity is bound from the JWT, so the patient tools have no patient-id parameter.
- **Deterministic safety core:** the YAML rule catalog (`services/api/app/rules/rules.yaml`) covers FIB-4 bands, ALT against baseline, wearable trends and the red-flag bypass.
- **Escalation workflow:** a LangGraph flow goes rule hit → FHIR Task → AI review → `interrupt()` for clinician approval → care-plan update → patient follow-up. It is checkpointed in Postgres.
- **RAG:** clinician-approved markdown content is embedded locally (bge-small via fastembed) into pgvector and searched with hybrid search. Answers cite their sources.
- **Document AI:** Claude reads the uploaded PDF or image into a validated schema, and the patient confirms before anything is saved to FHIR.

## Run locally
```bash
cd infra
cp .env.example .env        # add ANTHROPIC_API_KEY
docker compose up -d --build
```
- Web: http://localhost:3710 (choose a persona)
- API: http://localhost:8710/docs
- FHIR: http://localhost:8090/fhir

The first start seeds the data automatically. Use **Presenter controls → Reset** to restore the demo state.

Mobile (development): `cd apps/mobile && npm install && npx expo start --tunnel`, then open it in Expo Go and set Server to the API URL.

## Tests
```bash
cd services/api && uv run pytest
```

## Demo
See [docs/Demo-Script.md](docs/Demo-Script.md). A sample report for the upload step is in `sample-labs/`.
