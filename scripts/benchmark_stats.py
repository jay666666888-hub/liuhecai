#!/usr/bin/env python3
"""Benchmark script for stats API loading"""

import urllib.request
import json
import time

BASE_URL = "http://localhost:5188"

def measure_api(name, url, runs=3):
    """Measure API response time"""
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = json.loads(resp.read())
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)
        except Exception as e:
            print(f"Error accessing {url}: {e}")
            return None
    avg = sum(times) / len(times)
    min_t = min(times)
    max_t = max(times)
    print(f"{name}: avg={avg:.1f}ms, min={min_t:.1f}ms, max={max_t:.1f}ms (n={runs})")
    return avg

def benchmark_current():
    """Benchmark current API structure"""
    print("=" * 60)
    print("CURRENT API STRUCTURE BENCHMARK")
    print("=" * 60)

    # Measure individual endpoints
    endpoints = [
        ("/api/stats/categories", "categories discovery"),
        ("/api/stats/draw_stats/hot_stats", "hot_stats"),
        ("/api/stats/special_stats/zodiac_miss", "zodiac_miss"),
        ("/api/stats/special_stats/wave_miss", "wave_miss"),
        ("/api/stats/number_stats/special_number_miss", "special_number_miss"),
    ]

    print("\n--- Individual Endpoint Response Times ---")
    individual_times = {}
    for path, desc in endpoints:
        t = measure_api(desc, BASE_URL + path)
        if t is not None:
            individual_times[desc] = t

    total_individual = sum(individual_times.values()) if individual_times else 0
    print(f"\nIndividual endpoints total: {total_individual:.1f}ms")

    # Simulate full load sequence (categories + 4 stats in parallel)
    print("\n--- Full Load Sequence ---")

    # Categories first
    cat_start = time.perf_counter()
    with urllib.request.urlopen(BASE_URL + "/api/stats/categories", timeout=30) as resp:
        categories = json.loads(resp.read())
    cat_time = (time.perf_counter() - cat_start) * 1000

    # Sequential stat loads (browser would do in parallel)
    stat_times = []
    stat_categories = {
        'hot_stats': 'draw_stats',
        'zodiac_miss': 'special_stats',
        'wave_miss': 'special_stats',
        'special_number_miss': 'number_stats'
    }

    for typ, cat in stat_categories.items():
        t_start = time.perf_counter()
        with urllib.request.urlopen(f"{BASE_URL}/api/stats/{cat}/{typ}", timeout=30) as resp:
            json.loads(resp.read())
        stat_times.append((time.perf_counter() - t_start) * 1000)

    total_sequential = cat_time + sum(stat_times)
    max_parallel = cat_time + max(stat_times)  # browser parallel loads

    print(f"Categories fetch: {cat_time:.1f}ms")
    print(f"4 stat loads (sequential): {sum(stat_times):.1f}ms")
    print(f"Total sequential: {total_sequential:.1f}ms")
    print(f"Estimated true parallel (categories + max stat): {max_parallel:.1f}ms")

    print("\n" + "=" * 60)
    print("CURRENT STATE SUMMARY")
    print("=" * 60)
    print(f"Requests per full load: 5 (1 categories + 4 stats)")
    print(f"First screen load time (sequential): ~{total_sequential:.0f}ms")
    print(f"First screen load time (parallel, browser): ~{max_parallel:.0f}ms")
    print(f"Tab switch time: ~50-200ms per switch (new network request)")
    print(f"  - First tab: {cat_time + stat_times[0]:.0f}ms")
    print(f"  - Subsequent tabs (no cache): same as above")

    return {
        'requests': 5,
        'first_load_sequential_ms': total_sequential,
        'first_load_parallel_ms': max_parallel,
        'tab_switch_ms': stat_times[0] if stat_times else 100,
        'individual_times': individual_times
    }

if __name__ == "__main__":
    result = benchmark_current()
    print("\n" + "=" * 60)
    print("RESULT JSON")
    print("=" * 60)
    print(json.dumps(result, indent=2))