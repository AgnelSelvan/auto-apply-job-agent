# Auto Apply Job Agent

An autonomous AI agent for discovering jobs, evaluating opportunities, and automating the job application workflow.

Search | Understand | Match | Apply

Auto Apply Job Agent is an experimental open-source-style project exploring how AI agents can automate repetitive parts of the job-search process.

Instead of manually searching job boards, opening hundreds of listings, checking requirements, and filling out repetitive application forms, the agent can continuously discover relevant opportunities and assist with the application workflow, with everything happening locally on your machine.

## Requirements & Setup

This agent runs completely locally. You will need to set up the following dependencies:

### 1. Ollama (LLM Engine)
The agent relies on [Ollama](https://ollama.com/) to process job information and tailor resumes. 
- Install Ollama from [ollama.com](https://ollama.com/download).
- The project specifically requires the **Qwen 2.5 (7B)** model. Download it by running:
  ```bash
  ollama pull qwen2.5:7b
  ```

### 2. LaTeX Compiler (Resume Generation)
The project dynamically generates tailored PDF resumes using LaTeX (`pdflatex`). You must install a LaTeX distribution:
- **Windows:** Install [MiKTeX](https://miktex.org/download) or [TeX Live](https://tug.org/texlive/windows.html). Ensure the installation adds `pdflatex` to your system `PATH`.
- **macOS:** Install [MacTeX](https://tug.org/mactex/): `brew install --cask mactex`
- **Linux:** Install TeX Live via your package manager (e.g., `sudo apt install texlive-full` for Ubuntu/Debian).

### 3. Project Installation
Install the Python project and its dependencies in editable mode:
```bash
pip install -e .
```
*(Optionally, you may want to set up Playwright browsers if required by the scraper: `playwright install chromium`)*

## How to Run

You can run the agent directly from your terminal.

**Run with arguments:**
```bash
auto-apply-job-agent "software engineer python" -l "Bangalore, Remote"
```

**Run interactively:**
If you don't provide a query or location, the tool will launch interactively and prompt you for them:
```bash
auto-apply-job-agent
```

## Development

```bash
pip install -e ".[dev]"
pytest
```