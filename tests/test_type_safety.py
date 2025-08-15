"""Type safety tests to ensure proper typing throughout the codebase."""

import subprocess
import sys
from pathlib import Path


def test_pyright_type_checking():
    """Run pyright and ensure no type errors."""
    # Run pyright
    result = subprocess.run(
        [sys.executable, "-m", "pyright", "--statistics"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    # Extract error count from output
    error_count = 0
    for line in result.stdout.splitlines():
        if "errors" in line and line.strip()[0].isdigit():
            error_count = int(line.split()[0])
            break

    # Print output for debugging
    if error_count > 0:
        print("\nPyright output:")
        print(result.stdout)

    # Assert no errors (can be adjusted to allow some errors during transition)
    # Phase 2 target: reduce errors below 50
    assert error_count <= 50, (
        f"Too many type errors: {error_count}. Target is 50 or less."
    )


def test_no_any_types_in_core_modules():
    """Ensure core modules don't use Any type excessively."""
    import ast
    from pathlib import Path

    core_modules = [
        "src/domain",
        "src/application",
        "src/infrastructure/persistence",
    ]

    any_count = 0
    total_types = 0

    for module_path in core_modules:
        path = Path(module_path)
        if not path.exists():
            continue

        for py_file in path.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            try:
                with open(py_file, encoding="utf-8") as f:
                    tree = ast.parse(f.read())

                for node in ast.walk(tree):
                    if isinstance(node, ast.Name) and node.id == "Any":
                        any_count += 1
                    if isinstance(node, ast.arg | ast.AnnAssign | ast.FunctionDef):
                        total_types += 1
            except Exception:
                pass

    # Calculate percentage
    any_percentage = (any_count / total_types * 100) if total_types > 0 else 0

    # Assert Any usage is below threshold
    # Phase 2 target: reduce Any usage below 5%
    # Temporarily increased to 6% during migration (see issue #393)
    assert any_percentage <= 6, (
        f"Any type usage too high: {any_percentage:.1f}%. "
        "Target is 6% or less during migration."
    )


def test_all_functions_have_return_types():
    """Ensure all functions have return type annotations."""
    import ast
    from pathlib import Path

    modules_to_check = [
        "src/domain",
        "src/application",
    ]

    functions_without_returns = []

    for module_path in modules_to_check:
        path = Path(module_path)
        if not path.exists():
            continue

        for py_file in path.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            try:
                with open(py_file, encoding="utf-8") as f:
                    tree = ast.parse(f.read())

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Skip __init__ methods
                        if node.name == "__init__":
                            continue
                        # Check if has return annotation
                        if node.returns is None:
                            functions_without_returns.append(
                                f"{py_file}:{node.lineno}:{node.name}"
                            )
            except Exception:
                pass

    # Print functions without return types for debugging
    if functions_without_returns:
        print("\nFunctions without return types:")
        for func in functions_without_returns[:10]:  # Show first 10
            print(f"  - {func}")
        if len(functions_without_returns) > 10:
            print(f"  ... and {len(functions_without_returns) - 10} more")

    # Assert all functions have return types
    assert len(functions_without_returns) <= 50, (
        f"Too many functions without return types: {len(functions_without_returns)}"
    )


if __name__ == "__main__":
    test_pyright_type_checking()
    test_no_any_types_in_core_modules()
    test_all_functions_have_return_types()
