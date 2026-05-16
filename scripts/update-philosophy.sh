#!/bin/bash
SRC="${AGENTOS_PHILOSOPHY_DIR:-$HOME/Documents/agentos-philosophy}"
[ ! -d "$SRC" ] && echo "ERROR: Set AGENTOS_PHILOSOPHY_DIR" && exit 1
cp "$SRC/PHILOSOPHY.md" ../PHILOSOPHY.md
echo "Done. Run: git add . && git commit -m 'chore: update philosophy'"
