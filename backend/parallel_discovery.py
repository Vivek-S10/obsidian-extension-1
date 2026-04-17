import multiprocessing
import math
import time
import argparse
import sys

"""
Parallel Matrix Mapping Simulation
----------------------------------
This script demonstrates the "Relationship Discovery" logic by distributing 
a simulated O(N^2) Similarity Matrix calculation across multiple "ranks".

Concept:
In a vault with N notes, a full relationship scan requires an N x N matrix 
of similarity checks. Instead of one CPU doing all N^2 checks, we divide 
the matrix into 'Quadrants' or 'Tiles'.

Each process in this script simulates an MPI rank responsible for a specific 
portion of the "Relationship Space".
"""

def simulated_rank_worker(rank_id, total_ranks, intensity):
    # This block simulates the logic that would run inside an MPI rank
    process_name = f"Rank-{rank_id}"
    print(f"[{process_name}] Booting... Assigned to Relationship Quadrant {rank_id + 1}/{total_ranks}")
    
    # Scaling factor for the workload
    # At intensity 5, we do more work per 'tick' to saturate CPU
    # At intensity 1, we add sleep to slow it down
    work_load = 200 if intensity >= 5 else 50
    
    try:
        for row_block in range(work_load):
            # SIMULATION: The actual O(N^2) work happens here.
            # We use trigonometric math to force high CPU usage in htop.
            start_tick = time.time()
            
            # Keep process busy for a short burst
            burst_duration = 0.15 if intensity >= 5 else 0.05
            while time.time() - start_tick < burst_duration:
                # Tight loop of heavy floating point math
                x = 0.5
                for _ in range(200000):
                    x = math.sqrt(math.sin(x) * math.cos(x) + 0.1)
            
            # INTENSITY LOGIC:
            # If intensity is low (e.g., 1), we artificialy throttle the execution
            if intensity < 5:
                # This makes the progress "chunky" and slow
                time.sleep(0.3)
            
            # Progress reporting
            if row_block % (work_load // 5) == 0:
                progress = (row_block / work_load) * 100
                print(f"[{process_name}] Matrix Mapping Progress: {progress:.1f}% ... Calculating Row Blocks {row_block*10}-{(row_block+1)*10}")

        print(f"[{process_name}] Success: Quadrant {rank_id + 1} finalized and synced to Master.")
    except KeyboardInterrupt:
        pass

def main():
    parser = argparse.ArgumentParser(description="Parallel Matrix Mapping (MPI-Style) Simulation")
    parser.add_argument("--intensity", type=int, default=5, 
                        help="Simulation Intensity: 1 = Slow/Throttled, 5 = High CPU Saturation")
    args = parser.parse_args()

    # We simulate 5 workers to show significant load in htop
    num_simulated_ranks = 5
    
    print("="*60)
    print("  SCALING RELATIONSHIP DISCOVERY: PARALLEL MATRIX MAPPING")
    print("="*60)
    print(f"Target: Simulation of {num_simulated_ranks} Parallel Discovery Ranks")
    print(f"Intensity Level: {args.intensity} {'(PERFORMANCE MODE)' if args.intensity >= 5 else '(THROTTLED MODE)'}")
    print("="*60)
    print("Logic: Distributing O(N^2) Similarity calculations across quadrants...")
    
    processes = []
    
    # Spawn simulated "MPI Ranks" using Python multiprocessing
    # This allows each one to occupy its own core in htop
    for i in range(num_simulated_ranks):
        p = multiprocessing.Process(
            target=simulated_rank_worker, 
            args=(i, num_simulated_ranks, args.intensity)
        )
        processes.append(p)
        p.start()

    print(f"Discovery Engine started. Check 'htop' to see {num_simulated_ranks} processors at work.")
    
    # Wait for all simulated ranks to finish
    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        print("\nAborting Discovery Engine...")
        for p in processes:
            p.terminate()
            
    print("\n" + "="*60)
    print("  DISTRIBUTED MATRIX SYNC COMPLETE")
    print("="*60)
    print("All relationship quadrants merged. Link suggestions ready for frontend.")

if __name__ == "__main__":
    main()
