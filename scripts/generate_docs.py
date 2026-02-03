
import os
import ast

def extract_docstrings(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())

    docs = []
    
    # Module docstring
    if ast.get_docstring(tree):
        docs.append({"type": "module", "name": os.path.basename(filepath), "docstring": ast.get_docstring(tree)})

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            docstring = ast.get_docstring(node)
            if docstring:
                docs.append({"type": node.__class__.__name__.replace('Def', '').lower(), "name": node.name, "docstring": docstring})
    return docs

def generate_markdown(all_docs, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for doc_item in all_docs:
        filepath = doc_item["filepath"]
        filename = os.path.basename(filepath).replace(".py", ".md")
        output_filepath = os.path.join(output_dir, filename)
        
        with open(output_filepath, 'w', encoding='utf-8') as f:
            f.write(f"""# Documentation for {doc_item['module_name']}

""")
            for item in doc_item["docs"]:
                if item["type"] == "module":
                    f.write(f"""## Module: `{item['name']}`

""")
                elif item["type"] == "class":
                    f.write(f"""### Class: `{item['name']}`

""")
                elif item["type"] == "function":
                    f.write(f"""### Function: `{item['name']}`

""")
                f.write(f"""```
{item['docstring']}
```

""")
        print(f"Generated documentation for {doc_item['module_name']} at {output_filepath}")

def main():
    source_dir = "src"
    output_dir = "docs/generated"
    
    all_extracted_docs = []

    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                module_name = os.path.relpath(filepath, source_dir).replace(os.sep, ".")[:-3]
                
                docs = extract_docstrings(filepath)
                if docs:
                    all_extracted_docs.append({"filepath": filepath, "module_name": module_name, "docs": docs})
    
    generate_markdown(all_extracted_docs, output_dir)

if __name__ == "__main__":
    main()
