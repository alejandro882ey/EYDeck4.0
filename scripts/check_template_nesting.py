import re
import sys
from pathlib import Path

file_path = Path(r"c:\Users\CK624GF\OneDrive - EY\Documents\2025\dashboard_django\core_dashboard\templates\core_dashboard\dashboard.html")
if not file_path.exists():
    print("Template not found:", file_path)
    sys.exit(1)

open_tags = []
line_no = 0
pattern = re.compile(r"{%\s*(end\w+|\w+)(?:\s+[^%}]*)?%}")
errors = []
for line in file_path.read_text(encoding='utf-8').splitlines():
    line_no += 1
    for m in pattern.finditer(line):
        token = m.group(1).strip()
        if token.startswith('end'):
            tag = token[3:]
            if not open_tags:
                errors.append((line_no, 'Unmatched end%s' % tag, list(open_tags)))
            else:
                top = open_tags[-1]
                if top != tag:
                    errors.append((line_no, 'Mismatched end%s (top=%s)' % (tag, top), list(open_tags)))
                    # try to recover: pop until matching tag or empty
                    while open_tags and open_tags[-1] != tag:
                        open_tags.pop()
                    if open_tags and open_tags[-1] == tag:
                        open_tags.pop()
                else:
                    open_tags.pop()
        else:
            word = token
            if word in ('if', 'for', 'block', 'comment', 'autoescape', 'filter', 'with'):
                open_tags.append(word)
            elif word in ('elif', 'else'):
                if not open_tags or open_tags[-1] != 'if':
                    errors.append((line_no, 'Unexpected %s without open if' % word, list(open_tags)))
                # else fine
            else:
                # other tags ignored
                pass

print('Open tags at EOF:', open_tags)
print('Errors found:', len(errors))
for ln, msg, stack in errors:
    print(f'Line {ln}: {msg} | stack={stack}')

if errors:
    sys.exit(2)
else:
    print('No nesting errors detected')
