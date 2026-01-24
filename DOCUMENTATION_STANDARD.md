# ZenAI Documentation Standard

**Version:** 1.0
**Date:** 2026-01-24
**Purpose:** Ensure all code is self-explanatory, LLM-friendly, and maintainable

---

## File Header Template

Every Python file MUST start with this structured header:

```python
# -*- coding: utf-8 -*-
"""
<filename> - <One-line Purpose>

WHAT:
    <Detailed description of what this module/file does>
    <List all major components, classes, functions>
    <Specify inputs/outputs if applicable>

WHY:
    <Explain why this module exists>
    <What problem does it solve?>
    <How does it fit into the larger architecture?>

HOW:
    <High-level explanation of the approach>
    <Key algorithms or design patterns used>
    <Important dependencies or assumptions>

TESTING:
    <How to test this module>
    <Example usage or test commands>
    <Expected behavior or outputs>

EXAMPLES:
    ```python
    # Basic usage example
    from module import function
    result = function(input)
    ```

DEPENDENCIES:
    <List key dependencies>
    <Minimum versions if applicable>

AUTHOR: ZenAI Team
MODIFIED: <Date>
"""
```

---

## Function Docstring Template

Every function MUST have this structured docstring:

```python
def function_name(param1: type, param2: type) -> return_type:
    """
    <One-line summary of what the function does>

    WHAT:
        - Accepts: <description of parameters>
        - Returns: <description of return value>
        - Side effects: <any state changes or I/O>

    WHY:
        - Purpose: <why this function exists>
        - Problem solved: <specific issue addressed>
        - Design decision: <architectural reasoning>

    HOW:
        1. <First major step>
        2. <Second major step>
        3. <Third major step>
        - Algorithm: <any special algorithms>
        - Complexity: <time/space if relevant>

    TESTING:
        >>> function_name(example_input)
        expected_output

        # Edge cases:
        - <Edge case 1>
        - <Edge case 2>

    EXAMPLES:
        ```python
        # Basic usage
        result = function_name(arg1, arg2)

        # Advanced usage
        result = function_name(
            arg1=value1,
            arg2=value2
        )
        ```

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ExceptionType: When this exception occurs

    Note:
        - Important caveat 1
        - Important caveat 2
    """
```

---

## Class Docstring Template

Every class MUST have this structured docstring:

```python
class ClassName:
    """
    <One-line summary of what the class represents>

    WHAT:
        - Purpose: <what this class models or manages>
        - Attributes: <list key attributes>
        - Methods: <list key public methods>
        - State: <describe state management>

    WHY:
        - Design pattern: <why chosen (Singleton, Factory, etc.)>
        - Abstraction: <what complexity it hides>
        - Responsibility: <single responsibility principle>

    HOW:
        - Initialization: <how to create instances>
        - Lifecycle: <creation → usage → cleanup>
        - Thread safety: <if applicable>
        - Performance: <any optimization notes>

    TESTING:
        ```python
        # Create instance
        obj = ClassName(params)

        # Use methods
        result = obj.method()

        # Verify state
        assert obj.attribute == expected
        ```

    EXAMPLES:
        ```python
        # Basic usage
        instance = ClassName()
        instance.do_something()

        # Advanced usage
        with ClassName() as ctx:
            ctx.complex_operation()
        ```

    Attributes:
        attr1: Description
        attr2: Description

    Methods:
        method1(): Description
        method2(): Description
    """
```

---

## Comment Standards

### Inline Comments

Use comments to explain **WHY**, not **WHAT**:

```python
# GOOD - Explains WHY
# Use binary search for O(log n) lookup in sorted array
result = binary_search(array, target)

# BAD - Just repeats code
# Search the array for target
result = binary_search(array, target)
```

### Section Comments

Use section headers for logical code blocks:

```python
# ==========================================================================
# INITIALIZATION
# ==========================================================================

# ==========================================================================
# HELPER FUNCTIONS
# ==========================================================================

# ==========================================================================
# MAIN LOGIC
# ==========================================================================
```

### TODO Comments

Format TODO comments consistently:

```python
# TODO(feature): Implement caching for faster lookups
# TODO(bug): Fix edge case when input is empty
# TODO(optimization): Use async I/O for better performance
# TODO(refactor): Extract to separate module
```

---

## Type Hints

Always use type hints for better LLM understanding:

```python
from typing import List, Dict, Optional, Tuple, Union, Any

def process_data(
    items: List[Dict[str, Any]],
    config: Optional[Dict[str, str]] = None
) -> Tuple[bool, str]:
    """Process data with optional configuration."""
    pass
```

---

## Examples Directory

Create examples showing:

1. **Basic usage** - Simplest possible example
2. **Common patterns** - Frequently used scenarios
3. **Edge cases** - Unusual but valid usage
4. **Anti-patterns** - What NOT to do

---

## Testing Documentation

Every test file should have:

```python
"""
Test suite for <module>

WHAT:
    - Tests: <what is being tested>
    - Coverage: <what scenarios are covered>
    - Fixtures: <shared test data or setup>

WHY:
    - Critical paths: <why these tests matter>
    - Edge cases: <unusual scenarios tested>
    - Regression: <bugs prevented from recurring>

HOW:
    - Setup: <test environment preparation>
    - Execution: <how tests are run>
    - Teardown: <cleanup after tests>

RUNNING:
    pytest test_file.py
    pytest test_file.py::test_specific_function
    pytest test_file.py -v  # Verbose
    pytest test_file.py -k "pattern"  # Filter by name
"""
```

---

## LLM-Friendly Practices

### 1. Explicit Over Implicit

```python
# GOOD - Clear intent
def calculate_total_price(items: List[Item], tax_rate: float) -> float:
    """Calculate total price including tax."""
    subtotal = sum(item.price for item in items)
    tax = subtotal * tax_rate
    total = subtotal + tax
    return total

# BAD - Too implicit
def calc(x, r):
    return sum(i.p for i in x) * (1 + r)
```

### 2. Named Constants

```python
# GOOD
MAX_RETRIES = 3
TIMEOUT_SECONDS = 30
DEFAULT_BATCH_SIZE = 100

# BAD
if attempts > 3:  # Magic number
    timeout = 30  # What unit?
```

### 3. Descriptive Variable Names

```python
# GOOD
user_authentication_token = generate_token(user_id)
validated_email_addresses = [e for e in emails if is_valid(e)]

# BAD
t = gen(u)
v = [e for e in es if val(e)]
```

---

## Documentation Checklist

Before committing code, verify:

- [ ] File header includes WHAT/WHY/HOW/TESTING
- [ ] Every function has structured docstring
- [ ] Every class has structured docstring
- [ ] Type hints on all function signatures
- [ ] Comments explain WHY, not WHAT
- [ ] Examples provided for complex functions
- [ ] Edge cases documented
- [ ] Dependencies listed
- [ ] Testing instructions included

---

## Benefits

### For Humans
- ✅ Faster onboarding for new developers
- ✅ Easier code reviews
- ✅ Better debugging (understand intent)
- ✅ Self-documenting code

### For LLMs
- ✅ Accurate code analysis
- ✅ Better refactoring suggestions
- ✅ Contextual understanding
- ✅ Targeted improvements
- ✅ Automated documentation generation

### For Maintenance
- ✅ Reduced technical debt
- ✅ Easier to locate bugs
- ✅ Simpler to extend functionality
- ✅ Better test coverage

---

## Example: Before vs After

### Before (Undocumented)

```python
def proc(d, c):
    r = []
    for i in d:
        if i['t'] == c['f']:
            r.append(i)
    return r
```

### After (Documented)

```python
def filter_items_by_type(
    items: List[Dict[str, Any]],
    config: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Filter items based on type specified in configuration.

    WHAT:
        - Accepts: List of item dictionaries, configuration dict
        - Returns: Filtered list of items matching type
        - Side effects: None (pure function)

    WHY:
        - Purpose: Separate items by type for processing pipeline
        - Problem solved: Need to process different item types differently
        - Design decision: Filter early to reduce downstream complexity

    HOW:
        1. Extract target type from config
        2. Iterate through all items
        3. Include only items where 'type' field matches target
        - Algorithm: Simple linear filter (O(n))
        - Complexity: Time O(n), Space O(m) where m = matching items

    TESTING:
        >>> items = [{'type': 'A', 'value': 1}, {'type': 'B', 'value': 2}]
        >>> config = {'filter_type': 'A'}
        >>> filter_items_by_type(items, config)
        [{'type': 'A', 'value': 1}]

        # Edge cases:
        - Empty items list → returns []
        - No matching type → returns []
        - Missing 'type' field → skips item

    Args:
        items: List of dictionaries with 'type' field
        config: Configuration with 'filter_type' key

    Returns:
        Filtered list containing only items of target type

    Raises:
        KeyError: If config missing 'filter_type'
    """
    target_type = config['filter_type']
    filtered_items = []

    for item in items:
        if item.get('type') == target_type:
            filtered_items.append(item)

    return filtered_items
```

---

**Status:** ✅ Standard Defined
**Next:** Apply to all ZenAI files
