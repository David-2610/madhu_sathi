import os
import ast
import json

routes_dir = "app/api/routes"
api_inventory = []

for filename in os.listdir(routes_dir):
    if not filename.endswith(".py") or filename == "__init__.py":
        continue
    filepath = os.path.join(routes_dir, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    tree = ast.parse(content)
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                    if isinstance(decorator.func.value, ast.Name) and decorator.func.value.id == "router":
                        method = decorator.func.attr.upper()
                        route_path = "Unknown"
                        if decorator.args and isinstance(decorator.args[0], ast.Constant):
                            route_path = decorator.args[0].value
                        
                        purpose = ast.get_docstring(node)
                        if not purpose:
                            purpose = "No docstring provided"
                        
                        api_inventory.append({
                            "controller": filename.replace(".py", ""),
                            "method": method,
                            "route": route_path,
                            "purpose": purpose.split("\n")[0]
                        })

print(json.dumps(api_inventory, indent=2))
