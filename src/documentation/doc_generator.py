import ast
import os

def generate_module_docs(file_path):
    """Generates markdown documentation for a given Python file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())

    module_name = os.path.basename(file_path).replace('.py', '')
    docs = [f"# Module: `{module_name}`\n"]

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            docs.append(f"## Class: `{node.name}`\n")
            if ast.get_docstring(node):
                docs.append(f"```python\n{ast.get_docstring(node)}\n```\n")
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    docs.append(f"### Method: `{node.name}.{item.name}`\n")
                    if ast.get_docstring(item):
                        docs.append(f"```python\n{ast.get_docstring(item)}\n```\n")
        elif isinstance(node, ast.FunctionDef):
            docs.append(f"## Function: `{node.name}`\n")
            if ast.get_docstring(node):
                docs.append(f"```python\n{ast.get_docstring(node)}\n```\n")
    return "\n".join(docs)

def generate_project_docs(source_dir, output_dir):
    """Generates documentation for the entire project."""
    os.makedirs(output_dir, exist_ok=True)
    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                doc_content = generate_module_docs(file_path)
                relative_path = os.path.relpath(file_path, source_dir)
                output_file_name = relative_path.replace('.py', '.md').replace(os.sep, '__')
                output_path = os.path.join(output_dir, output_file_name)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(doc_content)
                print(f"Generated documentation for {file_path} -> {output_path}")

if __name__ == "__main__":
    # Example usage:
    # Assuming 'src' is the directory to document and 'docs/generated' is the output
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    source_directory = os.path.join(project_root, 'src')
    output_directory = os.path.join(project_root, 'docs', 'generated')
    
    generate_project_docs(source_directory, output_directory)
