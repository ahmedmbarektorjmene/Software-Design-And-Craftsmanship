#!/usr/bin/env python3
"""Type-check every TypeScript example in the book.

Each fenced ```ts block is written to build/ts/ as its own module and compiled
with the project's TypeScript under strict settings. A block that needs a
snippet of surrounding declarations must carry them itself; the point is that
every example compiles on its own.
"""

import glob
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, "build", "ts")

COMPILER_OPTIONS = {
    "strict": True,
    "target": "ES2022",
    "module": "ES2022",
    "moduleResolution": "bundler",
    "lib": ["ES2022", "DOM", "ESNext.Disposable"],
    "noEmit": True,
    "skipLibCheck": True,
    "noUnusedLocals": False,
    "noUnusedParameters": False,
    "exactOptionalPropertyTypes": False,
}


def fences(path):
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    return re.findall(r"```(?:ts|typescript)\n(.*?)```", text, re.S)


def compiler():
    local = os.path.join(ROOT, "node_modules", ".bin", "tsc")
    return local if os.path.exists(local) else shutil.which("tsc")


def main(paths):
    tsc = compiler()
    if tsc is None:
        print("TypeScript not found. Run: npm install", file=sys.stderr)
        return 1

    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK)

    count = 0
    for path in paths:
        base = os.path.splitext(os.path.basename(path))[0]
        for index, code in enumerate(fences(path), 1):
            count += 1
            name = "%s_%02d.ts" % (base, index)
            with open(os.path.join(WORK, name), "w", encoding="utf-8") as handle:
                handle.write("export {};\n" + code)

    config = os.path.join(WORK, "tsconfig.json")
    with open(config, "w", encoding="utf-8") as handle:
        json.dump({"compilerOptions": COMPILER_OPTIONS,
                   "include": ["*.ts"]}, handle, indent=2)

    result = subprocess.run([tsc, "-p", config], capture_output=True, text=True)
    print(result.stdout, end="")
    print(result.stderr, end="")
    print("fences: %d  exit: %d" % (count, result.returncode))
    return result.returncode


if __name__ == "__main__":
    files = sys.argv[1:] or sorted(glob.glob(os.path.join(ROOT, "book", "*.md")))
    sys.exit(main(files))
