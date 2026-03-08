# Regenerating the animated SVG demo

## Prerequisites (one-time)

```bash
npm install -g terminal-demo svg-term-cli
```

## Pipeline

```bash
# 1. Generate asciinema cast from scenario
echo "" | npx terminal-demo play docs/demo-verify-scenario.md -o docs/demo-verify.cast

# 2. Convert to animated SVG
npx svg-term-cli --in docs/demo-verify.cast --out docs/demo-verify.svg \
  --window --width 85 --height 38 --no-cursor

# 3. Add 10s end pause (otherwise the animation loops instantly)
python3 -c "
import json, pathlib
p = pathlib.Path('docs/demo-verify.cast')
lines = p.read_text().splitlines()
last = json.loads(lines[-1])
lines.append(json.dumps([last[0] + 10, 'o', ' ']))
p.write_text('\n'.join(lines) + '\n')
"
```

## Files

| File | Role |
|------|------|
| `demo-verify-scenario.md` | Source scenario (`terminal-demo` markdown format) |
| `demo-verify.cast` | Asciinema recording (intermediate) |
| `demo-verify.svg` | Animated SVG with CSS keyframes (final, embedded in README) |
| `references-before.bib` | LLM-generated references (before verification) |
| `references-after.bib` | Corrected references with source URLs (after verification) |
