# 🤖 AI Builder

An autonomous local AI coding workspace that transforms natural language instructions into real code changes.

AI Builder combines **FastAPI**, **Ollama**, and local LLMs to create an agent capable of generating, editing, and managing project files inside isolated workspaces. Instead of acting as a simple chatbot, the system operates as an execution-oriented coding agent that understands project context, maintains history, and applies structured file modifications automatically.

---

## ✨ Features

### 🧠 Local AI-Powered Development

* Runs entirely on local hardware
* Integrates with Ollama-hosted models
* Optimized for Gemma-based coding workflows
* No external API dependency required

### 📂 Workspace Management

* Project-based architecture
* Isolated development environments
* Persistent project history
* Automatic workspace creation

### ⚡ Agentic Code Generation

* Create new files from natural language prompts
* Modify existing files intelligently
* Multi-file project generation
* Structured file operations for safer automation

### 🔄 Persistent Memory

* Tracks project conversations
* Maintains development history
* Stores project metadata
* Enables iterative development workflows

### 🌐 FastAPI Backend

* REST API architecture
* Asynchronous execution pipeline
* CORS support
* Streaming response capability

---

## 🏗️ Architecture

```text
User Prompt
      │
      ▼
 FastAPI Server
      │
      ▼
 Agent Execution Engine
      │
      ▼
 Local LLM (Ollama)
      │
      ▼
 Structured File Actions
      │
      ▼
 Project Workspace
```

The AI model generates structured instructions that are automatically interpreted and applied to project files.

---

## 📁 Project Structure

```text
AI BUILDER/
│
├── agent_server.py          # Main FastAPI backend
├── calculator.py            # Example project
│
├── projects/
│   └── default/
│       └── fibonacci.py
│
└── .agent_history/
    └── history.json
```

---

## 🚀 Getting Started

### 1. Clone the Repository

### 2. Install Dependencies

```bash
pip install fastapi uvicorn requests pydantic
```

### 3. Install Ollama

Download and install Ollama:

https://ollama.com

### 4. Pull a Model

```bash
ollama pull gemma3
```

or

```bash
ollama pull gemma2
```

### 5. Start the Server

```bash
python agent_server.py
```

---

## 💡 Example Workflow

Prompt:

```text
Create a Flask blog application with authentication.
```

Agent Output:

```text
CREATE_FILE app.py
CREATE_FILE templates/index.html
CREATE_FILE requirements.txt
```

The system automatically creates and updates the required project files inside the workspace.

---

## 🎯 Vision

AI Builder is designed to evolve from a coding assistant into a fully autonomous development environment capable of:

* Planning software projects
* Writing production-ready code
* Running validation workflows
* Tracking progress automatically
* Managing multiple projects simultaneously
* Integrating local LLM reasoning with development automation

The long-term goal is to create a local-first software engineering agent that can function as an autonomous coding partner while keeping all data and computation on the user's machine.

---

## 🛠️ Tech Stack

* Python
* FastAPI
* Ollama
* Gemma
* AsyncIO
* JSON-based Project Memory
* Local File System Workspaces

---

## 📜 License

This project is open source and available under the MIT License.

---

## 👨‍💻 Author

Built for developers who want the power of autonomous AI coding agents without relying on cloud-based services.

**Local. Private. Agentic.**
