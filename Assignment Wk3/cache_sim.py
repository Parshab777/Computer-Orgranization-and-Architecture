import math
import random


class CacheSimulator:

    def __init__(
        self, cache_size_bytes, block_size_bytes, associativity, policy="LRU"
    ):
        self.cache_size = cache_size_bytes
        self.block_size = block_size_bytes
        self.associativity = associativity
        self.policy = policy.upper()

        self.num_blocks = self.cache_size // self.block_size
        self.num_sets = self.num_blocks // self.associativity

        self.offset_bits = int(math.log2(self.block_size))
        self.index_bits = int(math.log2(self.num_sets)) if self.num_sets > 1 else 0
        self.tag_bits = 32 - self.offset_bits - self.index_bits

        self.sets = [[] for _ in range(self.num_sets)]
        self.access_counter = 0
        self.hits = 0
        self.misses = 0

    def access(self, access_type, addr):
        self.access_counter += 1
        offset_mask = (1 << self.offset_bits) - 1
        index_mask = ((1 << self.index_bits) - 1) if self.index_bits > 0 else 0

        offset = addr & offset_mask
        set_index = (
            (addr >> self.offset_bits) & index_mask if self.index_bits > 0 else 0
        )
        tag = addr >> (self.offset_bits + self.index_bits)

        set_lines = self.sets[set_index]
        hit_block = next((b for b in set_lines if b["tag"] == tag), None)

        if hit_block:
            self.hits += 1
            hit_block["accessed"] = self.access_counter
            status = "HIT"
            evicted = "N/A"
        else:
            self.misses += 1
            status = "MISS"
            new_block = {
                "tag": tag,
                "inserted": self.access_counter,
                "accessed": self.access_counter,
            }

            if len(set_lines) < self.associativity:
                set_lines.append(new_block)
                evicted = "None"
            else:
                victim_idx = (
                    min(
                        range(len(set_lines)),
                        key=lambda i: set_lines[i][
                            "accessed" if self.policy == "LRU" else "inserted"
                        ],
                    )
                    if self.policy in ["LRU", "FIFO"]
                    else random.randint(0, len(set_lines) - 1)
                )
                evicted = hex(set_lines[victim_idx]["tag"])
                set_lines[victim_idx] = new_block

        return {
            "step": self.access_counter,
            "type": "READ" if access_type == 0 else "WRITE",
            "address": hex(addr),
            "tag": hex(tag),
            "set_index": set_index,
            "offset": offset,
            "status": status,
            "evicted": evicted,
        }


def generate_trace(filename="memory_trace.din", total_accesses=200):
    random.seed(42)
    accesses = []
    # Spatial locality
    for i in range(50):
        accesses.append((0 if random.random() < 0.8 else 1, 0x1000 + (i * 4)))
    # Temporal locality loop
    loop_addrs = [0x2000 + (j * 4) for j in range(8)]
    for _ in range(10):
        for addr in loop_addrs:
            accesses.append((0 if random.random() < 0.85 else 1, addr))
    # Random access
    for _ in range(total_accesses - len(accesses)):
        accesses.append(
            (
                0 if random.random() < 0.7 else 1,
                random.choice([0x1000, 0x2000, 0x3000, 0x4000])
                + random.randint(0, 1024),
            )
        )

    with open(filename, "w") as f:
        for acc_type, addr in accesses:
            f.write(f"{acc_type} 0x{addr:08x}\n")
    return accesses


if __name__ == "__main__":
    trace = generate_trace()

    configs = [
        (1024, 16, 1, "LRU"),
        (1024, 32, 1, "LRU"),
        (1024, 64, 1, "LRU"),
        (1024, 32, 2, "LRU"),
        (1024, 32, 4, "LRU"),
        (1024, 32, 2, "FIFO"),
        (1024, 32, 4, "FIFO"),
    ]

    # Output detailed trace log
    sim_base = CacheSimulator(1024, 32, 1, "LRU")
    with open("simulation_output.txt", "w") as f:
        f.write(
            f"{'Step':<5} | {'Type':<5} | {'Address':<10} | {'Tag':<10} | {'Index':<6} | {'Offset':<6} | {'Status':<6} | {'Evicted'}\n"
        )
        f.write("-" * 75 + "\n")
        for acc_type, addr in trace:
            res = sim_base.access(acc_type, addr)
            f.write(
                f"{res['step']:<5} | {res['type']:<5} | {res['address']:<10} | {res['tag']:<10} | {res['set_index']:<6} | {res['offset']:<6} | {res['status']:<6} | {res['evicted']}\n"
            )

    # Print summary table to terminal
    print(
        f"{'Cache Size':<10} | {'Block':<6} | {'Assoc':<8} | {'Policy':<6} | {'Accesses':<8} | {'Hits':<6} | {'Misses':<6} | {'Hit Ratio':<10} | {'Miss Ratio'}"
    )
    print("-" * 85)
    for c_size, b_size, assoc, pol in configs:
        sim = CacheSimulator(c_size, b_size, assoc, pol)
        for acc_type, addr in trace:
            sim.access(acc_type, addr)
        tot = sim.hits + sim.misses
        h_ratio = (sim.hits / tot) * 100
        m_ratio = (sim.misses / tot) * 100
        assoc_str = "Direct" if assoc == 1 else f"{assoc}-Way"
        print(
            f"{c_size} B{'':<5} | {b_size} B{'':<2} | {assoc_str:<8} | {pol:<6} | {tot:<8} | {sim.hits:<6} | {sim.misses:<6} | {h_ratio:<9.2f}% | {m_ratio:.2f}%"
        )