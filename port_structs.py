"""Parses C# source files from the Dark Cloud Enhanced mod and generates
Python data modules. Handles:
- const int/byte/ushort fields → Python constants
- static arrays (int[], ushort[], byte[], string[]) → Python lists
- Nested classes with offset-based fields (Enemy0..Enemy15, Orb0..Orb5, etc.)
- Dictionary<ushort, string> initializers
"""

import re
import os
import sys
from pathlib import Path

CS_DIR = Path(__file__).parent.parent / "Dark Cloud Improved Version"
OUT_DIR = Path(__file__).parent / "data"


def parse_const(line):
    """Parse: public const int foo = 0x1234; or similar."""
    m = re.match(
        r'\s*(?:public|internal|private|protected|static|readonly|\s)*'
        r'const\s+(\w+)\s+(\w+)\s*=\s*(.+?)\s*;', line)
    if not m:
        return None
    typ, name, val = m.group(1), m.group(2), m.group(3)
    return name, resolve_value(val, typ)


def parse_static_field(line):
    """Parse: public static int foo = 0x1234; or similar non-array."""
    m = re.match(
        r'\s*(?:public|internal|private|protected|static|\s)*'
        r'static\s+(\w+)\s+(\w+)\s*=\s*(.+?)\s*;', line)
    if not m:
        return None
    typ, name, val = m.group(1), m.group(2), m.group(3)
    if '[]' in typ or '{' in val:
        return None
    return name, resolve_value(val, typ)


def resolve_value(val, typ=None):
    """Convert C# literal to Python literal string."""
    val = val.strip()
    # Skip C# constructors
    if val.startswith("new "):
        return None
    # Handle hex
    if val.startswith("0x") or val.startswith("0X"):
        return val
    # Handle float suffix
    if val.endswith("F") or val.endswith("f"):
        return val[:-1]
    # Handle bool
    if val == "true":
        return "True"
    if val == "false":
        return "False"
    # Handle references like Addresses.mode or Enemy0.visible
    if '.' in val and not val.startswith('"'):
        return val
    # Handle casts
    val = re.sub(r'\((?:int|byte|ushort|uint|short|float|double|long)\)', '', val)
    return val.strip()


def parse_array(lines, start_idx):
    """Parse a static array initializer, possibly spanning multiple lines."""
    line = lines[start_idx]
    # Match: public static int[] name = { ... }; or new int[] { ... };
    m = re.match(
        r'\s*(?:public|internal|private|protected|static|readonly|\s)*'
        r'(?:static\s+)?(\w+)\[\]\s+(\w+)\s*=\s*(?:new\s+\w+\[\]\s*)?', line)
    if not m:
        return None, start_idx
    typ, name = m.group(1), m.group(2)

    # Collect everything from { to };
    full = ""
    i = start_idx
    while i < len(lines):
        full += lines[i]
        if '};' in lines[i] or ('{' in full and '}' in full and ';' in lines[i]):
            break
        i += 1

    # Extract between { }
    brace_m = re.search(r'\{(.+?)\}', full, re.DOTALL)
    if not brace_m:
        return None, i

    inner = brace_m.group(1)
    # Strip C# comments from array content
    inner = re.sub(r'//[^\n]*', '', inner)
    elements = [e.strip().rstrip(',') for e in inner.split(',') if e.strip()]

    if typ == "string":
        # Keep string literals as-is
        py_elements = [e if e.startswith('"') else f'"{e}"' for e in elements]
    else:
        py_elements = [resolve_value(e, typ) for e in elements]

    return (name, py_elements, typ), i


def parse_dict(lines, start_idx):
    """Parse Dictionary<ushort, string> initializer."""
    line = lines[start_idx]
    m = re.match(r'.*Dictionary<\w+,\s*\w+>\s+(\w+)\s*=\s*new', line)
    if not m:
        return None, start_idx

    name = m.group(1)
    full = ""
    i = start_idx
    brace_depth = 0
    while i < len(lines):
        full += lines[i]
        brace_depth += lines[i].count('{') - lines[i].count('}')
        if brace_depth <= 0 and '{' in full:
            break
        i += 1

    entries = re.findall(r'\{\s*(\d+)\s*,\s*"([^"]+)"\s*\}', full)
    return (name, entries), i


def parse_cs_file(filepath):
    """Parse a C# file and extract all constants, arrays, and dicts."""
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()

    results = {
        'constants': {},     # name -> value
        'arrays': {},        # name -> (elements, type)
        'dicts': {},         # name -> [(key, val), ...]
        'classes': {},       # class_name -> {constants}
    }

    current_class = None
    class_stack = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Track class nesting
        class_m = re.match(r'\s*(?:public|internal|private|protected|static|\s)*class\s+(\w+)', line)
        if class_m:
            cname = class_m.group(1)
            class_stack.append(cname)
            current_class = cname
            if cname not in results['classes']:
                results['classes'][cname] = {}
            i += 1
            continue

        # Track braces for class scope
        if stripped == '{' or stripped == '}':
            if stripped == '}' and class_stack:
                class_stack.pop()
                current_class = class_stack[-1] if class_stack else None
            i += 1
            continue

        # Skip comments
        if stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
            i += 1
            continue

        # Constants
        if 'const ' in line:
            result = parse_const(line)
            if result:
                name, val = result
                if current_class and current_class not in ('Addresses', 'Items', 'Enemies',
                        'Player', 'Weapons', 'Shop', 'Dungeon', 'CustomChests',
                        'CustomEffects', 'SideQuestManager', 'CheatCodes',
                        'MiniBoss', 'DailyShopItem', 'RubyOrbs', 'Dayuppy',
                        'TownCharacter', 'Dialogues', 'ReusableFunctions'):
                    results['classes'].setdefault(current_class, {})[name] = val
                else:
                    results['constants'][name] = val
            i += 1
            continue

        # Static arrays
        if 'static' in line and '[]' in line and ('{' in line or (i + 1 < len(lines) and '{' in lines[i + 1])):
            arr, end_i = parse_array(lines, i)
            if arr:
                name, elements, typ = arr
                target = results['classes'].get(current_class, results['arrays']) if (
                    current_class and current_class not in ('Addresses', 'Items', 'Enemies',
                        'Player', 'Weapons', 'Shop', 'Dungeon', 'CustomChests',
                        'CustomEffects', 'SideQuestManager', 'CheatCodes',
                        'MiniBoss', 'DailyShopItem', 'RubyOrbs', 'Dayuppy',
                        'TownCharacter', 'Dialogues', 'ReusableFunctions')) else results['arrays']
                target[name] = (elements, typ)
                i = end_i + 1
                continue

        # Dictionaries
        if 'Dictionary<' in line and 'new' in line:
            d, end_i = parse_dict(lines, i)
            if d:
                results['dicts'][d[0]] = d[1]
                i = end_i + 1
                continue

        # Static fields (non-array)
        if 'static' in line and '=' in line and '[]' not in line and 'const' not in line:
            result = parse_static_field(line)
            if result:
                name, val = result
                if current_class and current_class not in ('Addresses', 'Items', 'Enemies',
                        'Player', 'Weapons'):
                    results['classes'].setdefault(current_class, {})[name] = val
                else:
                    results['constants'][name] = val

        i += 1

    return results


def generate_python(parsed, module_name, source_file):
    """Generate a Python module from parsed C# data."""
    out = []
    out.append(f'"""Auto-generated from {source_file} — do not edit manually."""\n\n')

    # Constants
    if parsed['constants']:
        for name, val in parsed['constants'].items():
            if val is None:
                continue
            out.append(f"{name} = {val}\n")
        out.append("\n")

    # Arrays
    if parsed['arrays']:
        for name, (elements, typ) in parsed['arrays'].items():
            if len(elements) > 10:
                out.append(f"{name} = [\n")
                # Chunk into lines of 10
                for j in range(0, len(elements), 10):
                    chunk = ", ".join(elements[j:j+10])
                    out.append(f"    {chunk},\n")
                out.append("]\n\n")
            else:
                out.append(f"{name} = [{', '.join(elements)}]\n")
        out.append("\n")

    # Dicts
    if parsed['dicts']:
        for name, entries in parsed['dicts'].items():
            out.append(f"{name} = {{\n")
            for k, v in entries:
                out.append(f'    {k}: "{v}",\n')
            out.append("}\n\n")

    # Nested classes → Python classes or dicts with computed offsets
    for cname, fields in parsed['classes'].items():
        if not fields:
            continue
        # Filter out None values
        fields = {k: v for k, v in fields.items() if v is not None} if isinstance(fields, dict) else fields
        if not fields:
            continue
        # Check if this is an offset-based class (Enemy1, Enemy2, etc.)
        has_offset_refs = any('Enemy0.' in str(v) or 'Orb0.' in str(v) for v in fields.values()
                             if isinstance(v, str))
        if has_offset_refs:
            # Generate as computed constants
            out.append(f"\n# --- {cname} (computed from base + offset) ---\n")
            out.append(f"class {cname}:\n")
            for fname, fval in fields.items():
                out.append(f"    {fname} = {fval}\n")
            out.append("\n")
        else:
            out.append(f"\n\nclass {cname}:\n")
            for fname, fval in fields.items():
                if isinstance(fval, tuple):
                    # Array
                    elements, typ = fval
                    out.append(f"    {fname} = [{', '.join(elements)}]\n")
                else:
                    out.append(f"    {fname} = {fval}\n")
            out.append("\n")

    return "".join(out)


def generate_enemy_classes(parsed):
    """Special handler: generate Enemy0-15 using offset math instead of copy-paste."""
    out = []
    # Find Enemy0 fields
    e0 = parsed['classes'].get('Enemy0', {})
    if not e0:
        return ""

    out.append("\n# Enemy offset between floor enemies\n")
    out.append("ENEMY_OFFSET = 0x190\n\n")
    out.append("class Enemy:\n")
    out.append("    \"\"\"Access enemy N's field: Enemy.field(n, 'hp')\"\"\"\n")
    out.append("    _base = {\n")
    for fname, fval in e0.items():
        out.append(f"        '{fname}': {fval},\n")
    out.append("    }\n\n")
    out.append("    @classmethod\n")
    out.append("    def addr(cls, enemy_num, field):\n")
    out.append("        return cls._base[field] + (ENEMY_OFFSET * enemy_num)\n")
    out.append("\n")
    return "".join(out)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    cs_files = [
        "Items.cs", "Enemies.cs", "CheatCodes.cs", "MiniBoss.cs",
        "DailyShopItem.cs", "RubyOrbs.cs", "CustomChests.cs",
        "CustomEffects.cs", "SideQuestManager.cs",
    ]

    for cs_file in cs_files:
        filepath = CS_DIR / cs_file
        if not filepath.exists():
            print(f"SKIP: {cs_file} not found")
            continue

        print(f"Parsing {cs_file}...")
        parsed = parse_cs_file(filepath)

        module_name = cs_file.replace('.cs', '').lower()
        py_name = f"{module_name}.py"

        # Special handling for Enemies — use offset math
        extra = ""
        if cs_file == "Enemies.cs":
            extra = generate_enemy_classes(parsed)
            # Remove Enemy1-15 from classes since we use the dynamic accessor
            for i in range(1, 16):
                parsed['classes'].pop(f'Enemy{i}', None)

        py_code = generate_python(parsed, module_name, cs_file)
        if extra:
            py_code += extra

        out_path = OUT_DIR / py_name
        with open(out_path, 'w') as f:
            f.write(py_code)

        const_count = len(parsed['constants'])
        array_count = len(parsed['arrays'])
        dict_count = len(parsed['dicts'])
        class_count = len([c for c in parsed['classes'].values() if c])
        print(f"  → {py_name}: {const_count} constants, {array_count} arrays, "
              f"{dict_count} dicts, {class_count} classes")

    # Post-process all generated files
    for py_file in OUT_DIR.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        postprocess(py_file)

    print("\nDone! Generated files in:", OUT_DIR)


def postprocess(filepath):
    """Fix remaining C# syntax that leaked through."""
    with open(filepath, 'r') as f:
        content = f.read()

    # Button enum → integer flags
    button_map = {
        'Button.None': '0x0000', 'Button.L2': '0x0001', 'Button.R2': '0x0002',
        'Button.L1': '0x0004', 'Button.R1': '0x0008', 'Button.Triangle': '0x0010',
        'Button.Circle': '0x0020', 'Button.Cross': '0x0040', 'Button.Square': '0x0080',
        'Button.Select': '0x0100', 'Button.L3': '0x0200', 'Button.R3': '0x0400',
        'Button.Start': '0x0800', 'Button.DPad_Up': '0x1000', 'Button.DPad_Right': '0x2000',
        'Button.DPad_Down': '0x4000', 'Button.DPad_Left': '0x8000',
    }
    for cs, py in button_map.items():
        content = content.replace(cs, py)

    # Remove lines with C# constructors
    lines = content.split('\n')
    lines = [l for l in lines if 'new ' not in l or l.strip().startswith('#') or l.strip().startswith('"')]

    # Fix C# bools
    content = '\n'.join(lines)
    content = re.sub(r'\bfalse\b', 'False', content)
    content = re.sub(r'\btrue\b', 'True', content)

    # Remove C# comments that leaked
    content = re.sub(r'\s*//[^\n]*', '', content)

    # Remove empty class bodies
    content = re.sub(r'class \w+:\s*\n\n', '', content)

    with open(filepath, 'w') as f:
        f.write(content)


if __name__ == "__main__":
    main()
