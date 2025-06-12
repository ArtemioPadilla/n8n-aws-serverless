import re

files_to_fix = {
    "tests/unit/test_access_stack.py": ["stack"],
    "tests/unit/test_base_stack.py": ["template"],
    "tests/unit/test_cloudflare_config.py": ["config", "sidecar"],
    "tests/security/test_iam_policies.py": ["template"],
    "tests/performance/test_load_benchmarks.py": ["ecs", "cloudwatch"],
}

for file_path, vars_to_fix in files_to_fix.items():
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        for var_name in vars_to_fix:
            # Find lines where variable is assigned but check if it's used later
            lines = content.split('\n')
            new_lines = []
            i = 0
            while i < len(lines):
                if f"{var_name} = " in lines[i] and "=" in lines[i]:
                    # Check if variable is used in the next 30 lines or until next test
                    var_used = False
                    j = i + 1
                    while j < min(i + 30, len(lines)):
                        if "def test_" in lines[j] or "def setup" in lines[j]:
                            break
                        if f"{var_name}." in lines[j] or f"{var_name})" in lines[j] or f"{var_name}," in lines[j] or f"({var_name}" in lines[j]:
                            var_used = True
                            break
                        j += 1
                    
                    if not var_used and lines[i].strip().startswith(f"{var_name} = "):
                        # Replace assignment with just the call
                        lines[i] = lines[i].replace(f"{var_name} = ", "")
                
                new_lines.append(lines[i])
                i += 1
            
            content = '\n'.join(new_lines)
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        print(f"Fixed {file_path}")
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")

print("Done fixing unused variables")
