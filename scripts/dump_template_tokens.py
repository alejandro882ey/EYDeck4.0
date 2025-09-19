import re
from pathlib import Path
p = Path(r"c:\Users\CK624GF\OneDrive - EY\Documents\2025\dashboard_django\core_dashboard\templates\core_dashboard\dashboard.html")
text = p.read_text(encoding='utf-8').splitlines()
pattern = re.compile(r"({%\s*(end\w+|\w+)(?:\s+[^%}]*)?%})")
stack = []
for i,line in enumerate(text, start=1):
    for m in pattern.finditer(line):
        whole, token = m.group(1), m.group(2)
        token = token.strip()
        print(f"Line {i}: token='{whole}'  -> '{token}'  stack_before={stack}")
        if token.startswith('end'):
            tag = token[3:]
            if stack and stack[-1] == tag:
                stack.pop()
            else:
                print(f"  >> MISMATCH at line {i}: trying to end '{tag}' but top is {stack[-1] if stack else None}")
        else:
            if token in ('if','for','block','with','comment','autoescape','filter'):
                stack.append(token)
            elif token in ('elif','else'):
                # no push/pop but validate
                if not stack or stack[-1] != 'if':
                    print(f"  >> UNEXPECTED {token} at line {i} with stack {stack}")
            # else ignore
print('final stack:', stack)
