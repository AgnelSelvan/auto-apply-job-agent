# Auto Apply Job Agent

An autonomous AI agent for discovering jobs, evaluating opportunities, and automating the job application workflow.

## 🎯 Core Motto
**Search | Understand | Match | Apply**

The main objective of this repository is to fully automate your job search pipeline:
1. **Search**: Find jobs based on a specific title and location (e.g., LinkedIn).
2. **Match**: Scrape the full job description and evaluate it against your personal `about_me.md` profile using local LLMs.
3. **Auto-Apply**: If the matching percentage is greater than **80%**, the agent will automatically apply for the job on your behalf.

Instead of manually searching job boards, opening hundreds of listings, checking requirements, and filling out repetitive application forms, the agent continuously discovers relevant opportunities and handles the application workflow—with everything happening locally on your machine.

---

## 🚀 Requirements & Setup

This agent runs completely locally. You will need to set up the following dependencies:

### 1. Ollama (LLM Engine)
The agent relies on [Ollama](https://ollama.com/) to analyze job descriptions and compute match percentages against your profile. 
- Install Ollama from [ollama.com](https://ollama.com/download).
- The project specifically requires the **Qwen 2.5 (7B)** model. Download it by running:
  ```bash
  ollama pull qwen2.5:7b
  ```

### 2. Candidate Profile Setup
Create an `about_me.md` file in the root directory of this project. Fill this file with your skills, experience, education, and resume details. The AI will read this file to determine how well you match a job.

### 3. LaTeX Compiler (Resume Generation)
The project can dynamically generate tailored PDF resumes using LaTeX (`pdflatex`). You must install a LaTeX distribution:
- **Windows:** Install [MiKTeX](https://miktex.org/download) or [TeX Live](https://tug.org/texlive/windows.html). Ensure the installation adds `pdflatex` to your system `PATH`.
- **macOS:** Install [MacTeX](https://tug.org/mactex/): `brew install --cask mactex`
- **Linux:** Install TeX Live via your package manager (e.g., `sudo apt install texlive-full` for Ubuntu/Debian).

### 4. Project Installation
Install the Python project and its dependencies in editable mode:
```bash
pip install -e .
```
*(Ensure Playwright browsers are installed for the web scraper: `playwright install chromium`)*

---

## 🛠️ How to Run

You can run the agent directly from your terminal.

**Run interactively (Chat Mode):**
Launch the interactive coordinator agent to search and store jobs:
```bash
auto-apply-job-agent
```
*Example prompt: "Search for flutter engineer roles in bengaluru"*

**Run with arguments:**
```bash
auto-apply-job-agent "software engineer python" -l "Bangalore, Remote"
```

---

## 👨‍💻 Development

```bash
pip install -e ".[dev]"
pytest
```