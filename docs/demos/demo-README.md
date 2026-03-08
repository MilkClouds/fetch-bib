# Regenerating the animated SVG demos

## Prerequisites (one-time)

```bash
npm install -g terminal-demo svg-term-cli
```

## Pipeline

Each demo follows the same 3-step pipeline: scenario → cast → SVG.

```bash
# 1. Generate asciinema cast from scenario
echo "" | npx terminal-demo play docs/demos/<NAME>-scenario.md --record docs/demos/<NAME>.cast

# 2. Convert to animated SVG
npx svg-term-cli --in docs/demos/<NAME>.cast --out docs/demos/<NAME>.svg \
  --window --width 85 --height <HEIGHT> --no-cursor

# 3. Add 10s end pause (otherwise the animation loops instantly)
python3 -c "
import json, pathlib
p = pathlib.Path('docs/demos/<NAME>.cast')
lines = p.read_text().splitlines()
last = json.loads(lines[-1])
lines.append(json.dumps([last[0] + 10, 'o', ' ']))
p.write_text('\n'.join(lines) + '\n')
"
```

Then re-run step 2 to regenerate the SVG with the updated cast.

## Demos

| Demo | Scenario | Height | Description |
|------|----------|--------|-------------|
| `demo-streamingllm` | `demo-streamingllm-scenario.md` | 30 | Single paper fetch — correct venue |
| `demo-verify` | `demo-verify-scenario.md` | 38 | Bulk verification — catch hallucinated metadata |

## All files

| File | Role |
|------|------|
| `*-scenario.md` | Source scenario (`terminal-demo` markdown format) |
| `*.cast` | Asciinema recording (intermediate, needed to regenerate SVG) |
| `*.svg` | Animated SVG with CSS keyframes (final, embedded in README) |
| `references-before.bib` | LLM-generated references (before verification) |
| `references-after.bib` | Corrected references with source URLs (after verification) |
