import os
import re
import json
import asyncio
import requests
import subprocess
import shutil
import time
import webbrowser
import threading
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse
from pydantic import BaseModel

# Event to notify clients on shutdown
shutdown_trigger = asyncio.Event()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks executed via daemon thread to keep server async loop unblocked
    threading.Thread(target=run_startup_tasks, daemon=True).start()
    yield
    # Shutdown execution layer
    print("🛑 Server is shutting down...")
    shutdown_trigger.set()
    await asyncio.sleep(0.8)
    
    print("🤖 Unloading gemma4 from local hardware VRAM...")
    try:
        subprocess.run(["ollama", "stop", "gemma4"], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        requests.post("http://localhost:11434/api/generate", json={"model": "gemma4", "keep_alive": 0}, timeout=2)
    except Exception:
        pass

app = FastAPI(title="Agentic Coding Engine", lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HISTORY_DIR = os.path.join(os.getcwd(), ".agent_history")
HISTORY_FILE = os.path.join(HISTORY_DIR, "history.json")
PROJECTS_DIR = os.path.join(os.getcwd(), "projects")

def load_history():
    if not os.path.exists(HISTORY_FILE):
        data = {"projects": {}}
    else:
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {"projects": {}}
            
    if "projects" not in data or not data["projects"]:
        data["projects"] = {
            "default": {
                "id": "default",
                "name": "Default Project",
                "history": []
            }
        }
        os.makedirs(HISTORY_DIR, exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
    return data

def save_history(data):
    os.makedirs(HISTORY_DIR, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def get_project_workspace(project_id: str) -> str:
    path = os.path.abspath(os.path.join(PROJECTS_DIR, project_id))
    os.makedirs(path, exist_ok=True)
    return path

SYSTEM_PROMPT = """You are a highly capable agentic coding assistant. Your task is to implement the user's request by creating or modifying files in the current workspace.

You MUST output your file edits using strict structural blocks. Do not wrap these blocks in markdown code fences (like ```) unless the file content itself requires it. Make sure the headers and tags are exactly as specified.

For creating or overwriting files, use this format:
=== CREATE_FILE: path/to/filename.ext ===
[file contents here]
=== END_FILE ===

For editing specific sections of existing files, use this format:
=== MODIFY_FILE: path/to/filename.ext ===
<<< SEARCH
[exact old code to look for]
=== REPLACE
[new code to overwrite it with]
>>> END_MODIFY

Rules:
1. The search block in MODIFY_FILE must match the existing file content EXACTLY, character-for-character, including all indentation and whitespace.
2. Specify the relative path for files (e.g., "src/main.js" or "index.html").
3. Avoid explanatory text outside of these blocks as much as possible. Keep it concise.
4. You can generate multiple CREATE_FILE and MODIFY_FILE blocks in a single response to perform multi-file operations.
"""

class ExecuteRequest(BaseModel):
    prompt: str
    project_id: str

class ProjectCreate(BaseModel):
    name: str

def run_agent_workflow(user_prompt: str, project_id: str):
    history_data = load_history()
    if project_id not in history_data["projects"]:
        history_data["projects"][project_id] = {
            "id": project_id,
            "name": project_id.replace("-", " ").title(),
            "history": []
        }
    
    history_data["projects"][project_id]["history"].append({
        "role": "user",
        "text": user_prompt,
        "timestamp": datetime.now().isoformat()
    })
    save_history(history_data)

    agent_logs = []

    def log_and_yield(message):
        agent_logs.append(message)
        return f"data: {message}\n\n"

    yield log_and_yield("⚡ Preparing agent environment...")
    yield log_and_yield("⚡ Contacting local Ollama instance (gemma4) at http://localhost:11434...")

    workspace_path = get_project_workspace(project_id)
    combined_prompt = f"{SYSTEM_PROMPT}\n\nUser Request: {user_prompt}\n\nResponse:"

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "gemma4",
                "prompt": combined_prompt,
                "stream": False
            },
            timeout=180
        )
        
        if response.status_code != 200:
            yield log_and_yield(f"❌ Ollama returned status code {response.status_code}: {response.text}")
            return
            
        data = response.json()
        response_text = data.get("response", "")
        
        if not response_text:
            yield log_and_yield("⚠️ Received empty response from Ollama.")
            return
            
        yield log_and_yield("⚡ Ollama engine execution finalized. Parsing syntax blocks...")
        
    except requests.exceptions.RequestException as e:
        yield log_and_yield(f"❌ Connection to Ollama dropped. Is 'ollama run gemma4' active? Error: {str(e)}")
        history_data = load_history()
        history_data["projects"][project_id]["history"].append({
            "role": "agent",
            "text": "\n".join(agent_logs),
            "timestamp": datetime.now().isoformat()
        })
        save_history(history_data)
        return

    create_count = 0
    modify_count = 0
    
    # Parse CREATE_FILE blocks
    idx = 0
    while True:
        create_start = response_text.find("=== CREATE_FILE:", idx)
        if create_start == -1:
            break
            
        header_end = response_text.find("===", create_start + 16)
        if header_end == -1:
            break
            
        file_path = response_text[create_start + 16 : header_end].strip()
        yield log_and_yield(f"⚡ Found instructions to create file: {file_path}")
        
        end_marker = "=== END_FILE ==="
        end_idx = response_text.find(end_marker, header_end)
        if end_idx == -1:
            yield log_and_yield(f"❌ Malformed CREATE_FILE block for {file_path}: missing '{end_marker}'")
            idx = header_end
            continue
            
        content = response_text[header_end + 3 : end_idx]
        
        if content.startswith("\r\n"):
            content = content[2:]
        elif content.startswith("\n"):
            content = content[1:]
            
        if content.endswith("\r\n"):
            content = content[:-2]
        elif content.endswith("\n"):
            content = content[:-1]
            
        try:
            clean_rel_path = os.path.normpath(file_path.strip().lstrip('/\\'))
            full_path = os.path.abspath(os.path.join(workspace_path, clean_rel_path))
            
            if not full_path.startswith(workspace_path):
                yield log_and_yield(f"❌ Security restriction: Path traversal blocked for {file_path}")
                idx = end_idx + len(end_marker)
                continue

            dir_name = os.path.dirname(full_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
                
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
                
            yield log_and_yield(f"✅ Successfully generated {file_path}")
            create_count += 1
        except Exception as e:
            yield log_and_yield(f"❌ Error writing {file_path}: {str(e)}")
            
        idx = end_idx + len(end_marker)

    # Parse MODIFY_FILE blocks
    idx = 0
    while True:
        modify_start = response_text.find("=== MODIFY_FILE:", idx)
        if modify_start == -1:
            break
            
        header_end = response_text.find("===", modify_start + 16)
        if header_end == -1:
            break
            
        file_path = response_text[modify_start + 16 : header_end].strip()
        yield log_and_yield(f"⚡ Found instructions to modify file: {file_path}")
        
        end_marker = ">>> END_MODIFY"
        end_idx = response_text.find(end_marker, header_end)
        if end_idx == -1:
            yield log_and_yield(f"❌ Malformed MODIFY_FILE block for {file_path}: missing '{end_marker}'")
            idx = header_end
            continue
            
        block_content = response_text[header_end + 3 : end_idx]
        
        search_start = block_content.find("<<< SEARCH")
        replace_start = block_content.find("=== REPLACE")
        
        if search_start == -1 or replace_start == -1 or replace_start < search_start:
            yield log_and_yield(f"❌ Malformed SEARCH/REPLACE structure inside modification for {file_path}")
            idx = end_idx + len(end_marker)
            continue
            
        search_code = block_content[search_start + 10 : replace_start]
        if search_code.startswith("\r\n"):
            search_code = search_code[2:]
        elif search_code.startswith("\n"):
            search_code = search_code[1:]
            
        if search_code.endswith("\r\n"):
            search_code = search_code[:-2]
        elif search_code.endswith("\n"):
            search_code = search_code[:-1]
            
        replace_code = block_content[replace_start + 11 :]
        if replace_code.startswith("\r\n"):
            replace_code = replace_code[2:]
        elif replace_code.startswith("\n"):
            replace_code = replace_code[1:]
            
        if replace_code.endswith("\r\n"):
            replace_code = replace_code[:-2]
        elif replace_code.endswith("\n"):
            replace_code = replace_code[:-1]
            
        try:
            clean_rel_path = os.path.normpath(file_path.strip().lstrip('/\\'))
            full_path = os.path.abspath(os.path.join(workspace_path, clean_rel_path))
            
            if not full_path.startswith(workspace_path):
                yield log_and_yield(f"❌ Security violation: Attempted path traversal out of sandbox array.")
                idx = end_idx + len(end_marker)
                continue

            if not os.path.exists(full_path):
                yield log_and_yield(f"❌ File target not discovered on path: {file_path}")
            else:
                with open(full_path, "r", encoding="utf-8") as f:
                    file_content = f.read()
                    
                if search_code not in file_content:
                    yield log_and_yield(f"❌ Code matching target search block not verified in {file_path}.")
                else:
                    new_file_content = file_content.replace(search_code, replace_code, 1)
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(new_file_content)
                    yield log_and_yield(f"✅ Successfully modified {file_path}")
                    modify_count += 1
        except Exception as e:
            yield log_and_yield(f"❌ Error structural modification failure on {file_path}: {str(e)}")
            
        idx = end_idx + len(end_marker)
        
    if create_count == 0 and modify_count == 0:
        yield log_and_yield("⚠️ No execution syntax structures compiled by local model.")
        
    yield log_and_yield(f"🚀 Execution complete! Created: {create_count}, Modified: {modify_count}")

    history_data = load_history()
    if project_id in history_data["projects"]:
        history_data["projects"][project_id]["history"].append({
            "role": "agent",
            "text": "\n".join(agent_logs),
            "timestamp": datetime.now().isoformat()
        })
        save_history(history_data)

@app.post("/execute")
async def execute(request_data: ExecuteRequest):
    return StreamingResponse(
        run_agent_workflow(request_data.prompt, request_data.project_id),
        media_type="text/event-stream"
    )

@app.get("/projects")
async def get_projects():
    history_data = load_history()
    return list(history_data["projects"].values())

@app.post("/projects")
async def create_project(data: ProjectCreate):
    history_data = load_history()
    project_id = re.sub(r'[^a-zA-Z0-9-]', '-', data.name.lower()).strip('-')
    if not project_id:
        project_id = "unnamed-project"
        
    original_id = project_id
    counter = 1
    while project_id in history_data["projects"]:
        project_id = f"{original_id}-{counter}"
        counter += 1
        
    workspace_path = get_project_workspace(project_id)
    os.makedirs(workspace_path, exist_ok=True)
    
    history_data["projects"][project_id] = {
        "id": project_id,
        "name": data.name,
        "history": []
    }
    save_history(history_data)
    return history_data["projects"][project_id]

@app.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    history_data = load_history()
    if project_id in history_data["projects"]:
        del history_data["projects"][project_id]
        save_history(history_data)
        return {"status": "success", "message": f"Project {project_id} deleted."}
    raise HTTPException(status_code=404, detail="Project not found")

@app.get("/projects/{project_id}/files")
async def get_project_files(project_id: str):
    workspace_path = get_project_workspace(project_id)
    if not os.path.exists(workspace_path):
        raise HTTPException(status_code=404, detail="Project workspace not found")
        
    file_list = []
    for root, dirs, files in os.walk(workspace_path):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, workspace_path)
            rel_path_clean = rel_path.replace(os.sep, '/')
            file_list.append(rel_path_clean)
            
    return file_list

@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_path = os.path.join(os.getcwd(), "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>index.html not discovered. Ensure it is mapped inside execution directory.</h1>", status_code=404)

def get_gpu_stats():
    if not shutil.which("nvidia-smi"):
        return {"status": "unavailable", "message": "NVIDIA GPU not detected"}
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,temperature.gpu,utilization.gpu,memory.total,memory.used,memory.free", "--format=csv,noheader,nounits"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        lines = result.stdout.strip().split("\n")
        gpus = []
        for line in lines:
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 6:
                gpus.append({
                    "name": parts,
                    "temperature": f"{parts}°C",
                    "utilization": f"{parts}%",
                    "memory_total": f"{parts} MB",
                    "memory_used": f"{parts} MB",
                    "memory_free": f"{parts} MB"
                })
        return {"status": "success", "gpus": gpus}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/backend-status")
async def get_backend_status():
    ollama_status = "offline"
    ollama_models = []
    ollama_loaded = []
    try:
        r = requests.get("http://localhost:11434/", timeout=2)
        if r.status_code == 200 and "Ollama is running" in r.text:
            ollama_status = "online"
            try:
                r_tags = requests.get("http://localhost:11434/api/tags", timeout=2)
                if r_tags.status_code == 200:
                    ollama_models = [m["name"] for m in r_tags.json().get("models", [])]
            except Exception:
                pass
            try:
                r_ps = requests.get("http://localhost:11434/api/ps", timeout=2)
                if r_ps.status_code == 200:
                    ollama_loaded = r_ps.json().get("models", [])
            except Exception:
                pass
    except Exception:
        pass

    gpu_info = get_gpu_stats()
    return {
        "backend_initialized": True,
        "ollama": {
            "status": ollama_status,
            "models": ollama_models,
            "loaded": ollama_loaded
        },
        "gpu": gpu_info
    }

@app.get("/events")
async def sse_events(request: Request):
    async def event_generator():
        while not shutdown_trigger.is_set():
            try:
                await asyncio.wait_for(shutdown_trigger.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                yield "data: ping\n\n"
                continue
            if shutdown_trigger.is_set():
                break
        yield "data: shutdown\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")

def run_startup_tasks():
    time.sleep(1.5)
    print("🤖 Waking up local gemma4 layer via background shell pipeline...")
    try:
        subprocess.Popen(["ollama", "run", "gemma4"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        # 30-second response allocation to let system RAM unpack dense weights completely
        requests.post("http://localhost:11434/api/generate", json={"model": "gemma4", "prompt": ""}, timeout=30)
    except Exception as e:
        print(f"⚠️ Initializing cold boot failed. Ensure Ollama application is active. Log: {e}")

    print("🌐 Opening web interface at [http://127.0.0.1:8000](http://127.0.0.1:8000) ...")
    try:
        webbrowser.open("[http://127.0.0.1:8000](http://127.0.0.1:8000)")
    except Exception as e:
        print(f"⚠️ Target viewport display error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agent_server:app", host="127.0.0.1", port=8000, reload=False)