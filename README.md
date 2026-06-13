
# Intelligent Binary & Disassembly Vectorization Engine

An automated static analysis and natural language processing (NLP) pipeline designed to extract decompiler Abstract Syntax Trees (ASTs) via Ghidra, map operational sequences into high-dimensional vector spaces, and leverage local LLMs for behavioral pattern recognition.

## 🚀 Current Implementation Status (Core Pipeline)
* **Static Analysis Harness:** Headless Ghidra API integration scripts for processing target binaries and extracting structural assembly operational subroutines.
* **Feature Engineering Layer:** Tokenization routines designed to map raw opcodes (`MOV`, `PUSH`, `XOR`) into standardized execution sequences.
* **Mathematical Vectorization:** NumPy and Scikit-Learn implementations to calculate Cosine Similarity matrices across high-dimensional token arrays to detect behavioral pattern anomalies.

## 🗺️ Active Development Roadmap (In Progress)
* [ ] **Local LLM Asynchronous Loop:** Finalizing the stateless FastAPI inference workspace to pipe compiled token matrices directly into a local Gemma 4 agent loop.
* [ ] **Live Telemetry Visualization:** Integrating multi-threaded tracking views to graph similarity distribution clusters in real-time.

## 🛠️ Local Installation & Setup
1. Clone the repository
