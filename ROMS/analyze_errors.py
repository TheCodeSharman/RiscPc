import sys

def analyze_diffs(file1, file2):
    errors = []
    with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
        d1 = f1.read()
        d2 = f2.read()
        
    # Compare byte by byte
    min_len = min(len(d1), len(d2))
    for i in range(min_len):
        if d1[i] != d2[i]:
            errors.append(i)
            
    return errors

if len(sys.argv) < 3:
    print("Usage: python3 analyze_errors.py <your_dump.bin> <official_rom.bin>")
    sys.exit(1)

errors = analyze_diffs(sys.argv[1], sys.argv[2])

print(f"Total discrepancies found: {len(errors)}")
print("Analyzing intervals between errors (first 20 diffs)...")

# Show the 'gaps' between errors
for i in range(1, min(21, len(errors))):
    diff = errors[i] - errors[i-1]
    print(f"Error at {hex(errors[i])} (Gap: {diff})")