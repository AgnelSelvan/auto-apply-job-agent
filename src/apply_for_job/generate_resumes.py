import os
import sys
import logging
import pandas as pd
import json

from .browser_search import fetch_jd_from_url
from .ollama import generate_resume_latex

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    # Add TeX Live to PATH to ensure pdflatex is found
    tex_path = r"C:\texlive\2026\bin\windows"
    if tex_path not in os.environ.get("PATH", ""):
        os.environ["PATH"] = tex_path + os.pathsep + os.environ.get("PATH", "")

    # Paths
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    excel_path = os.path.join(base_dir, "linkedin_jobs.xlsx")
    about_me_path = os.path.join(base_dir, "about_me.md")
    resume_dir = os.path.join(base_dir, "resume")
    config_path = os.path.join(base_dir, "config.json")

    # Read config
    config = {"generate_latex": False}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read config.json: {e}")

    # Verify files exist
    if not os.path.exists(excel_path):
        logger.error(f"Excel file not found at {excel_path}. Run the search script first.")
        sys.exit(1)

    if not os.path.exists(about_me_path):
        logger.error(f"about_me.md not found at {about_me_path}")
        sys.exit(1)

    # Read about me
    with open(about_me_path, "r", encoding="utf-8") as f:
        about_me_text = f.read()

    # Read Excel
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        logger.error(f"Failed to read excel file: {e}")
        sys.exit(1)

    if "Application Web Link" not in df.columns:
        logger.error("Column 'Application Web Link' not found in the excel file.")
        sys.exit(1)

    if "Job Description" not in df.columns:
        df["Job Description"] = None

    # For now, process only the top 2 latest jobs
    process_df = df.head(2)
    print(f"Limiting to top 2 jobs for resume generation.")

    # Create resume directory
    os.makedirs(resume_dir, exist_ok=True)

    excel_needs_update = False

    # Process each job
    for index, row in process_df.iterrows():
        url = row.get("Application Web Link")
        title = row.get("Job Title", "Unknown Role")
        company = row.get("Company", "Unknown Company")

        if pd.isna(url) or url == "No URL":
            logger.warning(f"Row {index} has no valid URL. Skipping.")
            print(f"Row {index} has no valid URL. Skipping.")
            continue

        print(f"\n[{index+1}/{len(process_df)}] Processing Job: {title} at {company}")
        print(f"URL: {url}")
        logger.info(f"Processing index {index}: {title} at {company}")

        jd_text = row.get("Job Description")
        if pd.isna(jd_text) or not str(jd_text).strip():
            logger.info(f"Fetching JD from {url}")
            print(f"Fetching Job Description (JD)...")
            jd_text = fetch_jd_from_url(url)

            if jd_text and len(str(jd_text).strip()) >= 50:
                df.at[index, "Job Description"] = jd_text
                excel_needs_update = True
        else:
            print(f"JD already exists in excel file. Using stored JD.")

        if not jd_text or len(str(jd_text).strip()) < 50:
            logger.warning(f"Failed to fetch meaningful JD for index {index}. Skipping.")
            print(f"Failed to fetch meaningful JD. Skipping this job.")
            continue

        print(f"JD fetched successfully (length: {len(str(jd_text))} chars).")
        logger.info(f"Generating resume content using Ollama for index {index}...")
        print(f"Generating resume using Ollama...")

        latex_content = generate_resume_latex(jd_text, about_me_text)

        if not latex_content:
            logger.error(f"Failed to generate resume for index {index}.")
            print(f"Failed to generate resume.")
            continue

        # Save to resume folder
        tex_file = os.path.join(resume_dir, f"{index}.tex")
        try:
            with open(tex_file, "w", encoding="utf-8") as f:
                f.write(latex_content)
        except Exception as e:
            logger.error(f"Error saving file {tex_file}: {e}")
            print(f"Error saving file {tex_file}: {e}")
            continue

        # Compile to PDF using pdflatex directly
        if config.get("compile_pdf", True):
            print(f"Compiling PDF for index {index} using subprocess...")
            try:
                import subprocess
                from dotenv import load_dotenv
                load_dotenv()
                pdflatex_path = os.environ.get("PDFLATEX_PATH", r'C:\texlive\2026\bin\windows\pdflatex.exe')
                
                # run it twice to resolve references if needed, but once is usually fine for a basic resume
                result = subprocess.run(
                    [pdflatex_path, '-interaction=nonstopmode', '-output-directory', resume_dir, tex_file],
                    check=True,
                    capture_output=True,
                    text=True
                )
                print(f"Successfully compiled PDF for index {index}")
            except FileNotFoundError:
                logger.error("pdflatex executable not found at C:\\texlive\\2026\\bin\\windows\\pdflatex.exe.")
                print("pdflatex executable not found. Please ensure MiKTeX or TeX Live is installed.")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to compile PDF. pdflatex error:\n{e.output}")
                print(f"Failed to compile PDF. Check {tex_file.replace('.tex', '.log')} for details.")
            except Exception as e:
                logger.error(f"Unexpected error compiling PDF: {e}")
                print(f"Failed to compile PDF.")

        # Cleanup .tex if latex generation is not explicitly enabled
        if not config.get("generate_latex", False):
            try:
                if os.path.exists(tex_file):
                    os.remove(tex_file)
            except Exception as e:
                pass
        else:
            print(f"Successfully saved LaTeX source to {tex_file}")

    if excel_needs_update:
        try:
            df.to_excel(excel_path, index=False)
            logger.info("Updated excel file with scraped Job Descriptions.")
            print("Updated excel file with scraped Job Descriptions.")
        except Exception as e:
            logger.error(f"Failed to save updated excel file: {e}")
            print(f"Failed to save updated excel file: {e}")

if __name__ == "__main__":
    main()
