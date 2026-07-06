#!/usr/bin/env python3
"""Update all test files to use test_admin_headers instead of auth_headers for isolation."""
import re
from pathlib import Path

TEST_DIR = Path("/home/hindsight/spacetime-crm/server/tests")

# Files that already have the fix (from git diff)
ALREADY_FIXED = {
    "test_customers.py",
    "test_tenants.py", 
    "test_tickets.py",
}

def update_file(filepath: Path) -> bool:
    content = filepath.read_text()
    original = content
    
    # Skip already fixed files
    if filepath.name in ALREADY_FIXED:
        print(f"SKIP (already fixed): {filepath.name}")
        return False
    
    # 1. Update imports: add test_admin_headers if not present
    if "from .conftest import" in content:
        # Find the import line and add test_admin_headers
        import_pattern = r'(from \.conftest import\s+)([^\n]+)'
        def add_import(match):
            imports = match.group(2).strip()
            if "test_admin_headers" in imports:
                return match.group(0)
            # Add test_admin_headers to the imports
            new_imports = imports + ", test_admin_headers"
            return match.group(1) + new_imports
        content = re.sub(import_pattern, add_import, content)
    
    # 2. Replace auth_headers parameter with test_admin_headers in function signatures
    # This catches: def test_xxx(self, auth_headers: dict, ...)
    content = re.sub(
        r'(\bdef\s+\w+\([^)]*)\bauth_headers(\b\s*:)',
        r'\1test_admin_headers\2',
        content
    )
    
    # 3. Replace auth_headers variable references in function bodies
    # But be careful not to replace in strings or comments
    # We'll do a simple replacement for now
    content = re.sub(
        r'\bauth_headers\b(?!\s*=)',  # auth_headers not followed by =
        'test_admin_headers',
        content
    )
    
    # 4. Fix helper function signatures
    content = re.sub(
        r'(def\s+_\w+\([^)]*)\bauth_headers(\b\s*:)',
        r'\1test_admin_headers\2',
        content
    )
    
    # 5. Fix helper function calls that pass auth_headers
    # e.g., create_customer(auth_headers, ...) -> create_customer(test_admin_headers, ...)
    content = re.sub(
        r'(\w+\()\s*auth_headers\s*(,)',
        r'\1test_admin_headers\2',
        content
    )
    content = re.sub(
        r'(\w+\()\s*auth_headers\s*(\))',
        r'\1test_admin_headers\2',
        content
    )
    
    # 6. Fix headers=auth_headers
    content = re.sub(
        r'headers=auth_headers\b',
        'headers=test_admin_headers',
        content
    )
    
    # 7. Fix fixture references: auth_headers -> test_admin_headers in type hints
    content = re.sub(
        r':\s*dict\s*=\s*auth_headers\b',
        ': dict = test_admin_headers',
        content
    )
    
    if content != original:
        filepath.write_text(content)
        print(f"UPDATED: {filepath.name}")
        return True
    else:
        print(f"NO CHANGES: {filepath.name}")
        return False

def main():
    updated = 0
    for filepath in sorted(TEST_DIR.glob("test_*.py")):
        if filepath.name in ALREADY_FIXED:
            continue
        if filepath.name == "__init__.py" or filepath.name == "conftest.py":
            continue
        if update_file(filepath):
            updated += 1
    print(f"\nTotal files updated: {updated}")

if __name__ == "__main__":
    main()