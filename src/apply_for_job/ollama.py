import requests
import json
import logging

logger = logging.getLogger(__name__)

def extract_job_details_with_ollama(text):
    """
    Pass the text to Ollama running locally with the qwen3.5:9b model.
    """
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

    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "qwen3.5:9b",
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()

        # Parse the JSON response from Ollama
        generated_text = result.get("response", "{}").strip()

        import re
        match = re.search(r'\{.*\}', generated_text, re.DOTALL)
        if match:
            clean_text = match.group(0)
        else:
            clean_text = generated_text

        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from Ollama. Original text: {generated_text}")
            return None

    except Exception as e:
        logger.error(f"Error calling Ollama API: {e}")
        return None

def generate_resume_latex(jd_text: str, about_me_text: str) -> str:
    """
    Generate a tailored LaTeX resume using Ollama.
    """
    prompt = f"""Act as an expert technical recruiter and professional resume writer specializing in the software engineering industry. You write highly optimized, tailored, ATS-friendly resumes in LaTeX format. You must NEVER invent or hallucinate responsibilities, skills, or outcomes that are not explicitly stated in the input profile text. You should only rephrase, enhance, and structure what is actually provided, making it sound impactful while strictly avoiding fabrication. If information is missing, you should leave a placeholder like [X%] or [to be specified].

I will provide you with a Job Description (JD) and my complete candidate profile details. The provided details represent EVERYTHING about my background and experience. Your goal is to rewrite and format my resume based on this information so it is highly optimized for Applicant Tracking Systems (ATS). You must build a highly relevant, strong, ATS-friendly tailored resume that is designed to pass with an ATS match score of at least 85%, and instantly demonstrates high technical impact to human hiring managers.

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

    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "qwen3.5:9b",
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": 4096,
            "num_ctx": 32768
        }
    }

    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            logger.info(f"Starting LaTeX generation with Ollama (Attempt {attempt + 1}/{max_attempts})...")
            response = requests.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

            generated_text = result.get("response", "").strip()
            
            # Continuation loop if \end{document} is missing
            max_continuations = 5
            continuations = 0
            while "\\end{document}" not in generated_text and continuations < max_continuations:
                logger.info(f"Generated text is incomplete. Requesting continuation {continuations + 1}/{max_continuations}...")
                continuation_prompt = f"The previous response was truncated. Continue generating the exact LaTeX code from exactly where you left off. Do not include introductory text, just the raw LaTeX code continuing from: {generated_text[-200:]}"
                
                continuation_payload = {
                    "model": "qwen3.5:9b",
                    "prompt": continuation_prompt,
                    "stream": False,
                    "options": {
                        "num_predict": 4096,
                        "num_ctx": 32768
                    }
                }
                
                cont_response = requests.post(url, json=continuation_payload)
                cont_response.raise_for_status()
                cont_result = cont_response.json()
                cont_text = cont_result.get("response", "")
                
                # Remove any markdown code block artifacts from continuation
                import re
                cont_text = re.sub(r'^```(?:latex)?\s*', '', cont_text.strip(), flags=re.IGNORECASE)
                generated_text += " " + cont_text
                continuations += 1

            # Clean up if the model wrapped it in markdown
            import re
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

        except Exception as e:
            logger.error(f"Error calling Ollama API for resume generation on attempt {attempt + 1}: {e}")
            if attempt == max_attempts - 1:
                return ""

def generate_resume_docx_content(jd_text: str, about_me_text: str) -> str:
    """
    Generate a tailored HTML resume using Ollama, which will be converted to DOCX.
    """
    prompt = f"""Act as an expert technical recruiter and professional resume writer specializing in the software engineering industry. You write highly optimized, tailored, ATS-friendly resumes in HTML format. You must NEVER invent or hallucinate responsibilities, skills, or outcomes that are not explicitly stated in the input profile text. You should only rephrase, enhance, and structure what is actually provided, making it sound impactful while strictly avoiding fabrication. If information is missing, you should leave a placeholder like [X%] or [to be specified].

I will provide you with a Job Description (JD) and my complete candidate profile details. The provided details represent EVERYTHING about my background and experience. Your goal is to rewrite and format my resume based on this information so it is highly optimized for Applicant Tracking Systems (ATS). You must build a highly relevant, strong, ATS-friendly tailored resume that is designed to pass with an ATS match score of at least 85%, and instantly demonstrates high technical impact to human hiring managers.

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
    
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "qwen3.5:9b",
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": 4096,
            "num_ctx": 32768
        }
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        
        generated_text = result.get("response", "").strip()
        
        # Clean up if the model wrapped it in markdown
        import re
        generated_text = re.sub(r'^```(?:html)?\s*', '', generated_text, flags=re.IGNORECASE)
        generated_text = re.sub(r'\s*```$', '', generated_text)
        
        return generated_text.strip()
        
    except Exception as e:
        logger.error(f"Error calling Ollama API for DOCX HTML generation: {e}")
        return ""
