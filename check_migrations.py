"""
Script to check all migration files for proper structure
"""
import os
import ast

def check_migration_files(base_dir):
    apps = ['users', 'elections', 'blockchain', 'reports']
    issues = []
    
    for app in apps:
        migration_dir = os.path.join(base_dir, app, 'migrations')
        if not os.path.exists(migration_dir):
            continue
        
        migration_files = [f for f in os.listdir(migration_dir) 
                          if f.endswith('.py') and f != '__init__.py']
        
        for migration_file in migration_files:
            file_path = os.path.join(migration_dir, migration_file)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            if not content:
                issues.append(f"Empty migration file: {app}/{migration_file}")
                continue
            
            try:
                tree = ast.parse(content)
                has_migration_class = False
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name == 'Migration':
                        has_migration_class = True
                        break
                
                if not has_migration_class:
                    issues.append(f"No Migration class in: {app}/{migration_file}")
            except SyntaxError:
                issues.append(f"Syntax error in: {app}/{migration_file}")
    
    return issues

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    issues = check_migration_files(base_dir)
    
    if issues:
        print("Found migration issues:")
        for issue in issues:
            print(f" - {issue}")
    else:
        print("All migration files look good!")
