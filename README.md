# Jarvis AI Assistant

A combined frontend and backend agentic assistant prototype. This repository includes:
- A FastAPI backend for intent parsing, task planning, command generation, execution orchestration, and verification.
- A WPF Windows frontend that sends user requests to the backend, displays generated task plans, shows command output, and supports approval-driven execution.

## Overview

This project is built around a multi-stage workflow:

1. The user enters a natural language request.
2. The backend parses intent and entities with a small LLM pipeline.
3. The backend decomposes the request into sub-goals and step-by-step plan steps.
4. The frontend receives the plan and requests executable command generation.
5. The backend returns executable commands as structured output.
6. The frontend displays the plan and generated commands, then waits for user approval.
7. On approval the frontend executes commands locally, including a hard-coded Windows calendar event flow for calendar-related actions.
8. Verification support is available after execution to validate outcomes.

## Execution Flow

### Frontend flow

- The user types a request in the WPF UI and clicks **Send**.
- `MainWindow.xaml.cs` posts the request to the backend plan endpoint via `PlanningService`.
- The plan response is displayed in the chat panel.
- The frontend then calls the backend `/execute` endpoint using `ExecutionService` to generate executable commands from the steps.
- A loading overlay animation is shown while the backend is processing.
- The generated commands appear in the UI.
- The user clicks **Approve** to execute the plan.
- `TaskManager` creates a task and `ExecutionEngine` runs each step locally.
- For calendar-related steps, the frontend does not run PowerShell; instead it generates an `.ics` file and opens it with `explorer.exe` so Windows Calendar can import the event.
- After execution, verification logic can inspect outputs.

### Backend flow

- `/parse` receives raw user text and uses `IntentParser`.
- `IntentParser` normalizes the text and makes LLM calls for intent classification, entity extraction, and risk assessment.
- `/plan` uses `TaskPlanner` to decompose the intent into sub-goals and produce step-by-step plan steps.
- `/execute` uses `ExecutionPlanner` to translate the plan steps into actionable execution commands.
- `/verify` examines executed steps and returns a verification result.

## Backend File Descriptions

### `WindowsAIAssistant/backend/api.py`

This is the backend HTTP entrypoint. Key features:
- registers endpoints: `/health`, `/parse`, `/plan`, `/execute`, `/verify`, `/api/v1/task/process`, `/api/v1/task/verification-plan`, `/api/v1/memory/summarize`, `/api/v1/chat/respond`
- initializes FastAPI app and CORS middleware
- imports and exposes local verification engine adapters when available
- includes backend-side command generation and verification helper functions

### `WindowsAIAssistant/backend/intent_parser.py`

Responsible for converting raw text into a structured intent.
- `normalize()` standardizes whitespace and lowercases input.
- uses `ChatOllama` and `langchain_core` to perform LLM-driven:
  - intent classification
  - entity extraction
  - risk assessment
- returns a `StructuredIntent` with intent type, confidence, entities, risk level, and reasons.

### `WindowsAIAssistant/backend/task_planner.py`

Responsible for generating plans from structured intents.
- decomposes the goal into `SubGoal` items using LLM prompt.
- generates step-by-step `PlanStep` plans for each subgoal.
- output is a `TaskPlan` combining original intent and subgoal plans.

### `WindowsAIAssistant/backend/schemas.py`

Defines the Pydantic models shared across backend components.
- intent parser schemas: `IntentClassification`, `EntityExtraction`, `RiskAssessment`, `StructuredIntent`
- planning schemas: `SubGoal`, `GoalDecomposition`, `PlanStep`, `SubGoalPlan`, `TaskPlan`
- API request/response schemas live in `backend/ai/schemas.py`

### `WindowsAIAssistant/backend/ai/execution_planner.py`

Generates structured execution commands from plan steps.
- uses LLM prompt `execution.txt` to ask for actionable commands
- validates output into `ExecutionPlan` and `ExecutionCommandEntry`
- has fallback parsing when the LLM output is malformed
- outputs commands with `step_number`, `command`, `description`, and `tool`

### `WindowsAIAssistant/backend/ai/safety_analysis.py`

Implements simple heuristic risk analysis.
- detects destructive terms: delete, remove, format, wipe, registry, system
- marks approval as required for high-risk actions
- returns `SafetyAnalysisResult` with risk level, approval requirement, dangerous operations, and reasons

### `WindowsAIAssistant/backend/ai/model_manager.py`

Wraps the `ChatOllama` LLM client.
- loads model settings from `config.py`
- provides `infer()` for generic prompt execution
- includes retry logic and health check behavior

### `WindowsAIAssistant/backend/backend_router.py`

Orchestrates backend AI modules for task processing.
- creates `IntentParser`, `TaskPlanner`, `ModelManager`, `ContextEngine`, `PromptOrchestrator`, `SafetyAnalysisEngine`, and `VerificationPlanner`
- implements `process_task()` for the task pipeline
- exposes `create_verification_plan()`, `summarize_memory()`, and `chat_respond()` gateways

### `WindowsAIAssistant/backend/ai/prompt_orchestrator.py`

Loads prompt templates from the `prompts/` folder and renders them.
- supports prompt files like `planning.txt`, `safety_analysis.txt`, `execution.txt`, and `chat_respond.txt`
- uses `string.Template` substitution

### `WindowsAIAssistant/backend/config.py`

Stores backend configuration settings.
- model connection settings
- prompt directory and context window settings
- feature flags for safety analysis and verification planning

### `WindowsAIAssistant/backend/prompts/` files

- `intent.txt`: prompt template for intent classification and entity extraction
- `planning.txt`: prompt for goal decomposition and task planning
- `execution.txt`: prompt for converting plan steps into shell or command actions
- `safety_analysis.txt`: prompt for risk analysis
- `verification_planning.txt`: prompt for verification plan generation
- `summarization.txt`: prompt for memory summarization
- `chat_respond.txt`: prompt for conversational responses

### `WindowsAIAssistant/backend/verification_engine/`

Contains a complete verification pipeline.
- contracts define request/decision/evidence schemas
- API exposes verification entrypoints and trigger handling
- orchestrator coordinates evidence collection and decision making
- evidence collectors and builders create structured proof packages
- verifiers validate files, processes, downloads, registry state, and tasks
- stores persist audit records, evidence, pending requests, and replay data
- integrations connect execution layer triggers, safety authorizations, and completion reporting

## Frontend File Descriptions

### `WindowsAIAssistant/windowsAssistant.UI/MainWindow.xaml`

Defines the main WPF user interface.
- chat panel for user messages and assistant output
- task status panel with current task name, status text, and progress bar
- approve button for user confirmation before execution
- loading overlay animation shown while waiting on backend responses

### `WindowsAIAssistant/windowsAssistant.UI/MainWindow.xaml.cs`

Controls the UI workflow and backend interaction.
- sends user text to the backend planner
- renders the plan and tool hints in the chat area
- requests command generation from `/execute`
- shows a loading overlay while waiting for backend output
- creates a `TaskExecutionPlan` from actionable steps
- executes the plan on user approval
- optionally verifies the plan using `TaskManager`

### `WindowsAIAssistant/windowsAssistant.UI/Services/ApiClient.cs`

Basic HTTP client for the UI.
- sends POST requests with JSON payloads
- handles response deserialization and errors
- defaults to backend URL `http://localhost:8000`

### `WindowsAIAssistant/windowsAssistant.UI/Services/PlanningService.cs`

Talks to backend `/plan`.
- sends the user request text
- flattens the nested sub-goal plan response into a list of steps
- returns `PlanStep` items for display

### `WindowsAIAssistant/windowsAssistant.UI/Services/ExecutionService.cs`

Talks to backend `/execute`.
- sends the plan steps and receives generated execution commands
- returns `ExecutionApiResponse` containing logs and commands

### `WindowsAIAssistant/windowsAssistant.UI/Services/VerificationService.cs`

Talks to backend `/verify`.
- sends executed steps for validation
- returns a human-readable verification summary

### `WindowsAIAssistant/windowsAssistant.UI/Services/ExecutionEngine.cs`

Executes task steps locally in the UI process.
- translates step text into PowerShell actions
- runs commands using `ProcessStartInfo`
- logs success/failure and command output
- handles calendar event steps specially:
  - parses date and message from step text
  - creates a temporary `.ics` file with an event and 15-minute reminder
  - opens the `.ics` file with `explorer.exe` so Windows can import it
- verifies file/directory creation for a basic post-run check

### `WindowsAIAssistant/windowsAssistant.UI/Services/TaskManager.cs`

Manages task lifecycle at the UI level.
- creates frontend task items
- updates execution status and saves runtime state
- runs plan execution through `ExecutionEngine`
- invokes verification after execution

### `WindowsAIAssistant/windowsAssistant.UI/Services/TaskCoordinator.cs`

A lightweight task coordination service.
- receives plans from `TaskManager`
- currently acts as a pass-through coordinator for generated task plans

### `WindowsAIAssistant/windowsAssistant.UI/Models/`

Contains data structures used by the UI.
- `TaskStep`: action, command, tool id, completion state
- `TaskExecutionPlan`: ordered list of task steps
- `ExecutionCommand`: command string, tool, description
- `TaskItem`: wrapper for a planned task with metadata
- `VerificationResult`: storage for verification summaries

### `WindowsAIAssistant/windowsAssistant.UI/ViewModels/ToolsViewModel.cs`

Example view model for tool registry data.
- loads available tools asynchronously
- exposes an `IsLoading` flag for state binding

## Features Implemented

### Backend
- FastAPI endpoints for parsing, planning, execution, verification, chat, and memory summarization
- LLM-driven intent parsing with structured output handling
- Goal decomposition and step planning for complex user requests
- Command generation using an LLM prompt plus fallback handling
- Safety analysis to flag risky requests and require approval
- Verification engine scaffold for authorization, evidence, and decision workflows
- Modular prompt orchestration for flexible prompt templates

### Frontend
- WPF chat-style assistant interface
- plan rendering with sub-goal and step display
- approval-driven execution workflow
- animated loading overlay while backend is processing
- executable command generation from backend plans
- calendar event creation via `.ics` file for Windows Calendar import
- local execution logs and verification summary display

## How to Run

### Backend
1. Create and activate a Python virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Ensure a local Ollama server is running and accessible at `http://localhost:11434`.
4. Start the backend service:

```powershell
cd D:\Desktop\mini_project1\Jarvis\WindowsAIAssistant\backend
python -m api
```

### Frontend
1. Open `WindowsAIAssistant/windowsAssistant.UI/windowsAssistant.UI.csproj` in Visual Studio.
2. Build and run the WPF app.
3. Enter a natural language task and click **Send**.
4. Review the generated plan and commands.
5. Click **Approve** to execute.

## Important Notes

- The backend currently expects a working local Ollama model. If Ollama is unavailable, the intent parsing and plan generation features will fail.
- Calendar event handling is implemented in the frontend with hard-coded calendar extraction and `.ics` generation; it does not directly manipulate Outlook or Windows Calendar APIs.
- Verification is included but mostly scaffolded for local and demo use. Production verification requires more robust evidence collection and storage.
- The command execution path is currently limited to PowerShell commands and the special calendar event branch.

## Recommended Next Steps

- Add a proper quickstart section for the UI and backend with exact run commands.
- Add a `docker-compose.yml` for Ollama, backend, and optional frontend automation.
- Add authentication and request authorization for the backend.
- Replace the simple safety analysis heuristics with a more advanced policy or user approval flow.
- Extend the execution planner to produce more precise commands for tools like Flutter, Git, package managers, and calendar APIs.
- Add end-to-end tests for the UI/backend interaction and calendar event scenario.

