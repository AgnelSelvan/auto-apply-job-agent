import logging
import json
import re
import asyncio
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

logger = logging.getLogger(__name__)

def _run_adk_agent_sync(prompt: str, instruction: str) -> str:
    """Helper to run the ADK Agent synchronously."""
    agent = Agent(
        name="resume_agent",
        model="ollama/qwen2.5:7b",
        instruction=instruction,
    )

    async def _run():
        session_service = InMemorySessionService()
        await session_service.create_session(app_name="app", user_id="user", session_id="s1")
        runner = Runner(agent=agent, app_name="app", session_service=session_service)

        result_text = ""
        try:
            async for event in runner.run_async(
                user_id="user", session_id="s1",
                new_message=types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
            ):
                if event.is_final_response() and event.content:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            result_text += part.text
        except Exception as e:
            logger.error(f"Error running ADK Agent: {e}")

        return result_text.strip()

    return asyncio.run(_run())

def extract_job_details_with_ollama(text):
    """
    Extract job details using ADK with Ollama model.
    """
    instruction = "You are a helpful assistant. Provide the output strictly in valid JSON format."
    prompt = f"""
    Extract the job details from the following search result snippet.
    Provide the output strictly in JSON format with the following keys:
    - "job_title": The title of the job.
    - "company": The company offering the job.
    - "location": The location of the job.
    - "description": A brief description or summary.

    If a piece of information is missing, set its value to "N/A".
    Only output valid JSON, nothing else. Do not include markdown blocks.

    Text:
    {text}
    """

    generated_text = _run_adk_agent_sync(prompt, instruction)

    match = re.search(r'\{.*\}', generated_text, re.DOTALL)
    if match:
        clean_text = match.group(0)
    else:
        clean_text = generated_text

    try:
        return json.loads(clean_text)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse JSON from ADK. Original text: {generated_text}")
        return None


async def _run_adk_agent_async(prompt: str, instruction: str) -> str:
    """Helper to run the ADK Agent asynchronously."""
    agent = Agent(
        name="resume_agent",
        model="ollama/qwen2.5:7b",
        instruction=instruction,
    )
    import uuid
    current_session = f"match_session_{uuid.uuid4()}"
    session_service = InMemorySessionService()
    await session_service.create_session(app_name="app", user_id="user", session_id=current_session)
    runner = Runner(agent=agent, app_name="app", session_service=session_service)

    result_text = ""
    try:
        async for event in runner.run_async(
            user_id="user", session_id=current_session,
            new_message=types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
        ):
            if event.is_final_response() and event.content:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        result_text += part.text
    except Exception as e:
        logger.error(f"Error running ADK Agent async: {e}")

    return result_text.strip()

def calculate_match_percentage(job_description: str, about_me: str) -> float:
    """Synchronous match calculator (legacy)."""
    return asyncio.run(calculate_match_percentage_async(job_description, about_me))

async def calculate_match_percentage_async(job_description: str, about_me: str) -> float:
    """
    Evaluates the job description against the candidate's profile to calculate a match percentage asynchronously.
    """
    instruction = "You are an expert technical recruiter and ATS system. Output ONLY a raw number between 0 and 100 representing the match percentage. Do not include any other text, symbols, or explanations."
    prompt = f"""
    Evaluate how well the candidate's profile matches the job description.
    Analyze the skills, experience, and requirements.
    Output ONLY a single integer from 0 to 100.

    [JOB DESCRIPTION]
    {job_description[:2000]}  # Truncate to avoid context window issues

    [CANDIDATE PROFILE]
    {about_me[:3000]}
    """

    generated_text = await _run_adk_agent_async(prompt, instruction)
    
    match = re.search(r'\d+', generated_text)
    if match:
        try:
            score = float(match.group(0))
            return min(100.0, max(0.0, score))
        except ValueError:
            pass
    return 0.0


def generate_resume_latex(jd_text: str, about_me_text: str) -> str:
    """
    Generate a tailored LaTeX resume using ADK with Ollama model.
    """
    instruction = "Act as an expert technical recruiter and professional resume writer specializing in the software engineering industry. You write highly optimized, tailored, ATS-friendly resumes in LaTeX format."

    prompt = f"""I will provide you with a Job Description (JD) and my complete candidate profile details. The provided details represent EVERYTHING about my background and experience. Your goal is to rewrite and format my resume based on this information so it is highly optimized for Applicant Tracking Systems (ATS). You must build a highly relevant, strong, ATS-friendly tailored resume that is designed to pass with an ATS match score of at least 85%, and instantly demonstrates high technical impact to human hiring managers.

Please follow these strict formatting and content rules:

1. STRUCTURE & LAYOUT (ATS-Friendly LaTeX):
- Use a clean, reverse-chronological order.
- Use simple, standard section headers: Contact Information, Summary (mandatory strong headline, max 3-4 lines), Technical Skills, Professional Experience, SELECTED PROJECTS (MANDATORY), OPEN SOURCE & COMMUNITY (MANDATORY), ACHIEVEMENTS (MANDATORY), Education.
- Output the final resume entirely in valid LaTeX code.
- Do NOT include any markdown formatting blocks like ```latex or ``` in your response, just output the raw LaTeX code directly.

2. TECHNICAL SKILLS SECTION:
- Categorize skills clearly (e.g., Languages, Frameworks, Databases, Cloud/Tools).
- Prioritize and mirror the exact technical keywords, tools, and methodologies found in the provided Job Description.
- CRITICAL: You must ONLY list skills that are genuinely present in the candidate's profile (whether explicitly listed in their skills, or implicitly used in their projects/work experience). DO NOT hallucinate or invent skills the candidate does not have, even if the JD asks for them.

3. HIGH-IMPACT BULLET POINTS (The Core Task):
- Rewrite every experience and project bullet point using Googles XYZ formula: "Accomplished [X], as measured by [Y], by doing [Z]".
- Start every single bullet point with a powerful, varied technical action verb (e.g., Architected, Engineered, Optimized, Scaled, Migrated, Spearheaded). Avoid passive words like "Responsible for" or "Assisted".
- Quantify impact wherever possible. CRITICAL: DO NOT create formula placeholders like "[X%]" or "[Y%]" or "[Z%]" in the generated text. If a metric is not provided in my profile, either seamlessly infer a realistic, reasonable quantitative result without using any brackets, or simply omit the metric and focus entirely on the technical achievement.
- Ensure the technologies used in each project/job are explicitly stated at the end of that section (e.g., "Technologies used: React, Node.js, AWS").
- KEYWORD HIGHLIGHTING: In the "Professional Experience" and "Selected Projects" sections ONLY, use bold text (\\textbf{{...}}) to highlight specific keywords, tools, or metrics that are highly relevant to the Job Description. Do NOT bold entire sentences—only highlight the specific matching words.

4. TONE & ORIGINALITY (AI/Plagiarism Avoidance):
- Write the resume in a highly humanized, authentic, and natural tone, exactly as a real human professional would write it.
- Strictly avoid common AI-generated clichés, robotic phrasing, and overused buzzwords (e.g., "delve into", "testament to", "synergize", "unwavering").
- Ensure all text passes AI-detection and plagiarism checks by varying sentence structure, using conversational yet professional vocabulary, and making the phrasing sound unique and personalized. DO NOT copy standard templates word-for-word.

5. RELEVANCE & STRICT LENGTH LIMIT (CRITICAL):
- You MUST aggressively prune the candidate's profile. DO NOT copy everything from the profile.
- CRITICAL: You MUST explicitly include the "SELECTED PROJECTS", "OPEN SOURCE & COMMUNITY", and "ACHIEVEMENTS" sections. These headers are strictly MANDATORY. If you are struggling for space, cut down the Professional Experience bullet points instead. You must populate these sections with at least one entry, even if you have to choose an achievement or project that is only loosely related to the JD. Do not drop these headers.
- Limit each role/project to a MAXIMUM of 3 to 4 of the most impactful, JD-aligned bullet points.
- Ensure the final generated resume fits on exactly 1 page. However, if the candidate's highly relevant experience exceeds 1 page, allow the resume to expand to exactly 2 pages. If it extends to 2 pages, ensure the content fills the second page appropriately without awkward trailing empty space.

6. LATEX STYLING GUIDELINES:
Use exactly the following preamble and document structure template for the LaTeX document. Ensure you populate it with the candidate's actual tailored data, but strictly maintain this formatting:

\\documentclass[a4paper,10pt]{{article}}

\\usepackage[a4paper,margin=0.3in]{{geometry}}
\\usepackage{{enumitem}}
\\usepackage{{titlesec}}
\\usepackage{{parskip}}
\\usepackage{{titleps}}

\\usepackage{{xcolor}}

\\usepackage[default]{{sourcesanspro}}
\\usepackage[T1]{{fontenc}}

% Define colors
\\definecolor{{customblue}}{{HTML}}{{279AFF}}
\\definecolor{{darkblue}}{{HTML}}{{0B3D91}}

% Hyperlinks
\\usepackage[colorlinks=true, urlcolor=darkblue]{{hyperref}}

\\pagenumbering{{gobble}}

% Section Styling
\\titleformat{{\\section}}
{{\\color{{customblue}}\\large\\bfseries}}
{{}}{{0em}}{{}}[\\color{{black}}\\titlerule]

\\setlist[itemize]{{noitemsep, topsep=1pt, leftmargin=15pt}}

\\begin{{document}}

% ================= HEADER =================

\\begin{{center}}
    {{\\Huge \\bfseries\\color{{customblue}} [Candidate Name]}} \\\\[6pt]
    \\textbf{{[Target Job Title | Key Value Proposition]}} \\\\[6pt]

    {{\\small
\\href{{[LinkedIn URL]}}{{LinkedIn}}
\\ \\textbar\\
\\href{{[GitHub URL]}}{{GitHub}}
\\ \\textbar\\
\\href{{[Medium URL]}}{{Medium}}
\\ \\textbar\\
\\href{{mailto:[Email]}}{{[Email]}}
\\ \\textbar\\
[Phone Number]
\\ \\textbar\\
[Location]
}}
\\end{{center}}

% ================= SUMMARY =================

\\vspace{{4pt}}
\\color{{black}}\\titlerule[0.3pt]
\\vspace{{1pt}}

[Strong headline tailored to the JD, maximum 3-4 lines...]

% ================= CORE EXPERTISE =================

\\section*{{SKILLS}}

\\textbf{{Languages \\& Packages:}} [Skills...]

\\vspace{{1pt}}

\\textbf{{Backend \\& Cloud:}} [Skills...]

\\vspace{{1pt}}

\\textbf{{AI \\& Agent Engineering:}} [Skills...]

\\vspace{{1pt}}

\\textbf{{Tools:}} [Skills...]

% ================= EXPERIENCE =================

\\section*{{PROFESSIONAL EXPERIENCE}}

\\textbf{{\\large [Company Name]}} \\hfill \\textit{{[Start Date] -- [End Date]}} \\\\[3pt]
\\textit{{[Job Title]}}
\\begin{{itemize}}
    \\item [Accomplishment X, as measured by Y, by doing Z...]
\\end{{itemize}}

% ================= PROJECTS =================

\\section*{{SELECTED PROJECTS}}

% ---------- [Project Name] ----------

\\textbf{{\\large [Project Name]}} \\\\[-20pt]

% (Only include the following block if the project has links)
{{\\footnotesize
\\href{{[Project Link 1]}}{{[Link 1 Name]}}
\\ \\textbar\\
\\href{{[Project Link 2]}}{{[Link 2 Name]}}
}} \\\\[-16pt]
% (End of links block)

[Short summary paragraph of the project describing what was built and technologies used...]

\\begin{{itemize}}
    \\item [Accomplishment X, as measured by Y, by doing Z...]
\\end{{itemize}}

% ================= OPEN SOURCE & COMMUNITY =================

\\section*{{OPEN SOURCE \\& COMMUNITY}}

\\textbf{{\\large [Project/Community Name]}} \\hfill \\textit{{[Date]}} \\\\[3pt]
\\textit{{[Role or Contribution Type]}}
\\begin{{itemize}}
    \\item [Brief description of contribution or impact...]
\\end{{itemize}}

% ================= ACHIEVEMENTS =================

\\section*{{ACHIEVEMENTS}}

\\begin{{itemize}}
    \\item [Brief description of achievement or award...]
\\end{{itemize}}

% ================= EDUCATION =================

\\section*{{EDUCATION}}

\\textbf{{\\large [Degree]}} \\hfill \\textit{{[Date]}} \\\\[3pt]
\\textit{{[University Name]}}

\\end{{document}}

[TARGET JOB DESCRIPTION]
{jd_text}

[MY CURRENT RESUME / EXPERIENCE DETAILS]
{about_me_text}
"""

    max_attempts = 3
    for attempt in range(max_attempts):
        logger.info(f"Starting LaTeX generation with ADK Agent (Attempt {attempt + 1}/{max_attempts})...")
        generated_text = _run_adk_agent_sync(prompt, instruction)

        # Continuation loop if \end{document} is missing
        max_continuations = 5
        continuations = 0
        while "\\end{document}" not in generated_text and continuations < max_continuations:
            logger.info(f"Generated text is incomplete. Requesting continuation {continuations + 1}/{max_continuations}...")
            continuation_prompt = f"The previous response was truncated. Continue generating the exact LaTeX code from exactly where you left off. Do not include introductory text, just the raw LaTeX code continuing from: {generated_text[-200:]}"

            cont_text = _run_adk_agent_sync(continuation_prompt, instruction)

            # Remove any markdown code block artifacts from continuation
            cont_text = re.sub(r'^```(?:latex)?\s*', '', cont_text.strip(), flags=re.IGNORECASE)
            generated_text += " " + cont_text
            continuations += 1

        # Clean up if the model wrapped it in markdown
        generated_text = re.sub(r'^```(?:latex)?\s*', '', generated_text, flags=re.IGNORECASE)
        generated_text = re.sub(r'\s*```$', '', generated_text)

        # Check if it was successfully completed
        if "\\end{document}" in generated_text:
            logger.info("LaTeX generation completed successfully.")
            return generated_text.strip()
        else:
            logger.warning(f"Attempt {attempt + 1} failed to generate a complete document even with continuations.")
            if attempt == max_attempts - 1:
                logger.warning("Max attempts reached. Forcing close tags.")
                if "\\begin{itemize}" in generated_text and "\\end{itemize}" not in generated_text.split("\\begin{itemize}")[-1]:
                    generated_text += "\n\\end{itemize}"
                generated_text += "\n\\end{document}"
                return generated_text.strip()

    return ""

def generate_resume_docx_content(jd_text: str, about_me_text: str) -> str:
    """
    Generate a tailored HTML resume using ADK with Ollama model, which will be converted to DOCX.
    """
    instruction = "Act as an expert technical recruiter and professional resume writer specializing in the software engineering industry. You write highly optimized, tailored, ATS-friendly resumes in HTML format."
    prompt = f"""I will provide you with a Job Description (JD) and my complete candidate profile details. The provided details represent EVERYTHING about my background and experience. Your goal is to rewrite and format my resume based on this information so it is highly optimized for Applicant Tracking Systems (ATS). You must build a highly relevant, strong, ATS-friendly tailored resume that is designed to pass with an ATS match score of at least 85%, and instantly demonstrates high technical impact to human hiring managers.

Please follow these strict formatting and content rules:

1. STRUCTURE & LAYOUT (HTML):
- Use a clean, reverse-chronological order.
- Use simple, standard section headers wrapped in <h1> or <h2> tags.
- Output the final resume entirely in valid HTML code. Do NOT include ```html markdown blocks, just output raw HTML.
- Include standard sections: Header (Name, Contact Info), Summary, Technical Skills, Professional Experience, Selected Projects, Open Source & Community, Achievements, Education.

2. HIGH-IMPACT BULLET POINTS (The Core Task):
- Rewrite every experience and project bullet point using Googles XYZ formula: "Accomplished [X], as measured by [Y], by doing [Z]".
- Start every single bullet point with a powerful, varied technical action verb.
- Highlight highly relevant keywords using <b> or <strong> tags.
- Limit each role/project to a MAXIMUM of 3 to 4 of the most impactful, JD-aligned bullet points.
- Structure lists correctly using <ul> and <li> tags.

[TARGET JOB DESCRIPTION]
{jd_text}

[MY CURRENT RESUME / EXPERIENCE DETAILS]
{about_me_text}
"""

    generated_text = _run_adk_agent_sync(prompt, instruction)

    # Clean up if the model wrapped it in markdown
    generated_text = re.sub(r'^```(?:html)?\s*', '', generated_text, flags=re.IGNORECASE)
    generated_text = re.sub(r'\s*```$', '', generated_text)

    return generated_text.strip()
