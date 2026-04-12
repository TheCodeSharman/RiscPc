import sys

def find_all_occurrences(data, byte_seq):
    occurrences = []
    start = 0
    while True:
        idx = data.find(byte_seq, start)
        if idx == -1:
            break
        occurrences.append(idx)
        start = idx + 1
    return occurrences

# Ensure we have a filename
if len(sys.argv) < 2:
    print("Usage: python3 find_aliases.py <filename.bin>")
    sys.exit(1)

filename = sys.argv[1]
target_seq1 = b'\x8d\xe5' # 0xE58D
target_seq2 = b'\xfd\xe8' # 0xE8FD

try:
    with open(filename, 'rb') as f:
        data = f.read()

    offsets1 = find_all_occurrences(data, target_seq1)
    offsets2 = find_all_occurrences(data, target_seq2)

    print(f"File: {filename}")
    print(f"Occurrences of 0xE58D (b'\\x8d\\xe5') at:")
    print([hex(o) for o in offsets1])
    
    print(f"\nOccurrences of 0xE8FD (b'\\xfd\\xe8') at:")
    print([hex(o) for o in offsets2])

except FileNotFoundError:
    print(f"Error: {filename} not found.")