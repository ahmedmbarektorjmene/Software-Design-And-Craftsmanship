
# Default recipe
default: pdf

# Typeset the PDF from the files in book/.
pdf:
    python3 tools/build.py

# Type-check every TypeScript example.
check:
    python3 tools/check_code.py

# Verify that the typesetting toolchain is installed.
doctor:
    python3 tools/build.py --check

# Remove generated build artifacts.
clean:
    rm -rf build
