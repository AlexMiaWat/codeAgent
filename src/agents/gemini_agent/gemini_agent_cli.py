# src/agents/gemini_agent/gemini_agent_cli.py

import argparse
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables from .env file
load_dotenv()

def get_project_context(project_path: Path) -> str:
    """
    Simulates gathering project context. For this iteration, returns a simple string.
    In a real scenario, this would involve reading relevant project files.
    """
    if project_path.exists() and project_path.is_dir():
        # For a more realistic context, you would list directories, specific files, etc.
        # For simplicity, we'll just indicate some files in the root.
        try:
            files_in_root = [p.name for p in project_path.iterdir() if p.is_file()]
            return f"Project path is: {project_path}. Some files in root: {', '.join(files_in_root[:5])}"
        except Exception as e:
            return f"Project path is: {project_path}. Could not list files for context: {e}"
    return "No specific project context gathered for this iteration as path is not valid or empty."

def generate_and_write_todo(instruction: str, output_file_path: Path, control_phrase: str, project_path: Path):
    """
    Generates a todo list using Gemini LLM and writes it to the specified file.
    """
    print(f"Gemini Agent received instruction: '{instruction}'")

    # Get API key from environment
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("GOOGLE_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    try:
        # Configure API key
        genai.configure(api_key=api_key)

        model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-pro-latest")
        model = genai.GenerativeModel(model_name)

        # Crafting the prompt for the LLM
        context = get_project_context(project_path)
        prompt = (
            f"You are a helpful assistant. Based on the following instruction, create a detailed development plan (Todo list) "
            f"for the next 2 days. The project context is: '{context}'.\n\n"
            f"Instruction: {instruction}\n\n"
            f"Please provide the plan in markdown format, and at the very end, include the exact phrase: '{control_phrase}'"
        )

        print("Calling Gemini LLM for content generation...")
        response = model.generate_content(prompt)
        generated_content = response.text
        print("LLM call successful.")

        # Ensure the directory exists
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        output_file_path.write_text(generated_content, encoding='utf-8')
        print(f"Gemini Agent successfully wrote generated content to: {output_file_path}")

    except Exception as e:
        print(f"Error during LLM operation: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gemini CLI agent for generating and writing todo lists.")
    parser.add_argument("instruction", type=str, help="The instruction for the Gemini LLM.")
    parser.add_argument("output_file_path", type=str, help="Absolute path to the output file (e.g., /workspace/docs/test_todo.md).")
    parser.add_argument("control_phrase", type=str, help="The control phrase to include in the generated content.")
    parser.add_argument("--project_path", type=str, default="/workspace", help="Absolute path to the project directory for context.")

    args = parser.parse_args()

    generate_and_write_todo(
        instruction=args.instruction,
        output_file_path=Path(args.output_file_path),
        control_phrase=args.control_phrase,
        project_path=Path(args.project_path)
    )
