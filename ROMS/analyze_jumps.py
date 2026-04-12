# Save this as analyze_jumps.py
# Paste your addresses from the cmp output into the 'addresses' list
addresses = [
    0x0010, 0x003e, 0x0094, 0x1d08, 0x3790, 
    0x465e, 0x4704, 0x47b8, 0x47e6, 0x4e44
]

print("Analyzing Address Deltas (Looking for powers of 2)...")
for i in range(len(addresses) - 1):
    delta = addresses[i+1] - addresses[i]
    # Check if delta is a power of 2 (a single bit flip)
    is_bit_flip = (delta & (delta - 1) == 0) and (delta != 0)
    print(f"Jump from {hex(addresses[i])} to {hex(addresses[i+1])}: Delta = {hex(delta)} {'<-- SINGLE BIT FLIP!' if is_bit_flip else ''}")