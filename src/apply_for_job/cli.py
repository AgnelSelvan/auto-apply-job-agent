import argparse
import logging
import sys

from .search import search_linkedin_jobs
from .generate_resumes import main as generate_resumes_main

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="Search LinkedIn jobs via SearXNG.")
    parser.add_argument("query", nargs="*", help="Job title or keywords to search on LinkedIn.")
    parser.add_argument("-l", "--location", default="", help="Job location(s) separated by comma. Default: India")
    parser.add_argument("--searxng-url", default="http://localhost:8080", help="SearXNG URL (default: http://localhost:8080)")

    args = parser.parse_args()

    query = " ".join(args.query)
    location = args.location

    if not query:
        try:
            query = input("Enter job title or keywords to search on LinkedIn (or Ctrl+C to exit): ")
            if not location:
                location = input("Enter location(s) separated by comma (default: India): ")
        except KeyboardInterrupt:
            print("\nExiting.")
            sys.exit(0)

    if not location.strip():
        location = "India"

    if query.strip():
        search_linkedin_jobs(query, location, args.searxng_url)
        print("\nJob search completed. Starting resume generation in LaTeX format using Ollama Qwen 3.5 9b...")
        generate_resumes_main()
    else:
        print("Empty search query. Exiting.")
        sys.exit(1)

if __name__ == "__main__":
    main()
