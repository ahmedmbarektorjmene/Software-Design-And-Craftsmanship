# 19. Performance and Algorithmic Thinking

Performance is a requirement like any other. It is also the requirement most often addressed by folklore: intuitions about which operations are slow, which optimizations matter, and which costs are negligible. Those intuitions were formed on different hardware, different runtimes, and different workloads, and they are frequently wrong.

This chapter is about making performance a disciplined engineering activity: specifying it, measuring it, understanding the algorithmic costs, and optimizing only where the evidence points.

## Learning objectives

- Turn vague performance wishes into measurable requirements.
- Benchmark and profile without fooling yourself.
- Reason about asymptotic cost and why constants sometimes dominate.
- Identify the critical path and the dominant cost in a system.
- Apply the small set of optimizations that still matter: better algorithms, batching, caching, and reducing work.
- Explain the costs of optimization, including complexity, correctness risk, and maintainability.

## 19.1 Performance as a requirement

"Fast" is not a requirement. A requirement has a **measure**, a **workload**, and a **threshold**:

- *Measure:* p95 latency of the checkout endpoint, or time to first byte, or peak memory, or cost per thousand requests.
- *Workload:* at 200 requests per second with a cart of 20 items, or on a 1 GB file, or with 10 million rows.
- *Threshold:* under 300 ms, under 2 GB, under $0.40.

Without all three, a performance discussion is a disagreement about feelings.

Useful measures:

- **Latency percentiles.** Averages hide tail behavior. p50 tells you the typical experience; p95 and p99 tell you who is suffering. A mean of 100 ms with a p99 of 4 s is a system with a serious tail problem.
- **Throughput.** Requests or records per unit time, usually at a stated latency budget.
- **Resource use.** CPU, memory, disk I/O, network, and the dollar cost they imply.
- **Scalability.** How the measure changes as the workload grows. A system that meets its target at today's volume but degrades super-linearly has a future incident built in.

Write the requirement down, with the workload and the measurement method. It becomes the target for profiling and the acceptance criterion for optimization.

## 19.2 Measurement

You cannot optimize what you do not measure, and most attempts to measure are subtly wrong.

### Benchmarking pitfalls

- **Measuring the wrong thing.** A microbenchmark of a function that is called once per request tells you nothing about a system spending 80% of its time in the database.
- **Warm-up effects.** JIT compilers, caches, and connection pools need warm-up. A first-run measurement includes costs that production never sees.
- **Dead-code elimination.** A compiler may remove a computation whose result is unused, making it appear infinitely fast. Consume the result.
- **Unrealistic inputs.** A benchmark on a 10-element array says nothing about a 10-million-element one; both the algorithm and the cache behavior change.
- **Noise.** Garbage collection, other processes, frequency scaling, and network jitter add variance. Run enough iterations and report distributions, not single numbers.
- **Observing the observer.** Profilers add overhead and can change the behavior they measure.

```typescript
interface BenchmarkResult {
  readonly label: string;
  readonly iterations: number;
  readonly medianMs: number;
  readonly p95Ms: number;
}

async function benchmark(
  label: string,
  iterations: number,
  work: () => void,
): Promise<BenchmarkResult> {
  const samples: number[] = [];
  for (let i = 0; i < iterations; i++) {
    const start = performance.now();
    work();
    samples.push(performance.now() - start);
  }
  samples.sort((a, b) => a - b);
  return {
    label,
    iterations,
    medianMs: samples[Math.floor(samples.length / 2)] ?? 0,
    p95Ms: samples[Math.floor(samples.length * 0.95)] ?? 0,
  };
}
```

A benchmark that reports a median and a p95 is already better than one that reports an average, because it shows the spread. A benchmark that reports a p99 needs enough samples for that percentile to mean anything—at least a few hundred.

### Profiling

A **profiler** attributes time or resources to code. Two common views:

- **Sampling profiler:** periodically records the call stack. Low overhead, statistically meaningful, good for finding hot functions.
- **Instrumenting profiler:** records every function entry and exit. Precise counts, higher overhead, distorts timing.

Start with the coarsest view that answers the question. For a web service: which endpoint is slow? Then: which phase—parse, query, render? Then: which function? Then: which line?

The **flame graph** is the most useful visualization: width is time, depth is the call stack. A wide plateau is a hot path; a tall, narrow tower is a deep call chain. Look for the widest frame that is *not* an expected part of the work.

For memory, the equivalent is an allocation profile or a heap snapshot. A leak shows up as a growing retained set across requests; a churn problem shows up as high allocation rate with low retention.

## 19.3 Algorithmic thinking

The largest performance wins come from changing the algorithm, not from micro-optimizing it. An O(n²) algorithm on ten thousand records does a hundred million operations; no amount of loop unrolling fixes that.

Common orders, from best to worst:

| Order | Growth | Typical example |
|-------|--------|-----------------|
| O(1) | constant | Hash lookup, array index |
| O(log n) | logarithmic | Binary search, balanced tree |
| O(n) | linear | Single pass over a collection |
| O(n log n) | linearithmic | Comparison sort |
| O(n²) | quadratic | Nested loop over the same collection |
| O(2ⁿ) | exponential | Naive subset enumeration |

The practical questions:

- **What is n, realistically?** An O(n²) algorithm on n = 20 is fine; on n = 200,000 it is not.
- **What is the constant?** A hash lookup with a slow hash and poor locality can lose to a linear scan of a small array.
- **What is the memory cost?** An index that makes lookups O(1) costs memory and maintenance. Sometimes the trade is right; sometimes it is not.

```typescript
interface Order { readonly id: string; readonly customerId: string }
interface Customer { readonly id: string }

// O(n²): for each order, scan all customers.
function attachCustomersSlow(
  orders: readonly Order[],
  customers: readonly Customer[],
): { order: Order; customer: Customer | undefined }[] {
  return orders.map((order) => ({
    order,
    customer: customers.find((c) => c.id === order.customerId),
  }));
}

// O(n): index the customers once.
function attachCustomersFast(
  orders: readonly Order[],
  customers: readonly Customer[],
): { order: Order; customer: Customer | undefined }[] {
  const byId = new Map(customers.map((c) => [c.id, c]));
  return orders.map((order) => ({ order, customer: byId.get(order.customerId) }));
}
```

For n = 50 the difference is invisible. For n = 50,000 it is the difference between a page load and a timeout. The algorithmic fix is usually shorter and clearer than the slow version, which is a pleasant property: the fast code is often the simple code.

### Data structures

Choosing the right structure is an algorithmic decision:

- **Array** for ordered data and iteration; O(n) search unless sorted.
- **Map/Set** for membership and lookup by key; O(1) average, with hashing costs.
- **Sorted array** for range queries and binary search; O(log n) lookup, O(n) insert.
- **Heap** for repeatedly extracting the minimum or maximum; O(log n) per operation.
- **Tree** for ordered traversal and range queries with dynamic updates.
- **Bloom filter** for probabilistic membership with bounded memory; false positives, no false negatives.

The cost of the wrong structure usually appears as an accidental O(n) inside a loop. An array `.find()` inside a `.map()` is the canonical example.

![A buffer object backed by a collection of memory chunks.](assets/buffer-chunks.jpg){width=60%}

## 19.4 The critical path

Most systems have a small number of operations that dominate. Find them before optimizing anything.

**Amdahl's law** quantifies the ceiling: if a fraction *p* of the work is improved by a factor *s*, the overall speedup is bounded by

```
speedup = 1 / ((1 - p) + p / s)
```

If 40% of the time is in code you can make infinitely fast, the maximum speedup is 1 / 0.6 ≈ 1.67×. Optimizing the other 60% is where the remaining gains are.

A practical consequence: **measure the distribution before choosing a target.** A service spending 70% of its time in serialization gains little from a faster router. A service spending 70% in one slow query gains everything from an index.

### Latency numbers worth knowing

Approximate orders of magnitude for a modern server (they change, but the ratios are stable):

| Operation | Approximate cost |
|-----------|------------------|
| L1 cache reference | ~1 ns |
| Main memory reference | ~100 ns |
| SSD random read | ~100 µs |
| Network round trip within a datacenter | ~0.5 ms |
| Disk seek | ~10 ms |
| Network round trip across continents | ~100 ms |

The ratios explain most performance folklore. A memory access is a hundred times an L1 hit; a disk seek is ten thousand times a memory access; a cross-continent round trip is a hundred thousand times a memory access. This is why batching network calls and avoiding N+1 queries dominate micro-optimizations: they remove whole round trips, not nanoseconds.

## 19.5 Optimizations that still matter

Most low-level tricks are obsolete; a few structural optimizations remain valuable in almost every system.

### Better algorithms and data structures

Covered above. This is the first and largest lever.

### Batching and reducing round trips

The dominant cost in distributed systems is often the number of round trips, not the size of the payload.

```typescript
interface Order { readonly id: string; readonly customerId: string }
interface Customer { readonly id: string }

interface Database {
  query<T>(sql: string, params: readonly unknown[]): Promise<T[]>;
  queryOne<T>(sql: string, params: readonly unknown[]): Promise<T | undefined>;
}

// N+1: one query per order.
async function loadCustomersSlow(orders: readonly Order[], db: Database): Promise<Customer[]> {
  const customers: Customer[] = [];
  for (const order of orders) {
    const customer = await db.queryOne<Customer>("select * from customers where id = $1", [order.customerId]);
    if (customer) customers.push(customer);
  }
  return customers;
}

// Batched: one query for all ids.
async function loadCustomersFast(orders: readonly Order[], db: Database): Promise<Customer[]> {
  const ids = [...new Set(orders.map((order) => order.customerId))];
  return db.query<Customer>("select * from customers where id = any($1)", [ids]);
}
```

The second version is fewer lines and one round trip instead of *n*. It also fails more predictably: one query either succeeds or fails, rather than leaving a partial result.

### Caching

A cache trades memory and consistency for speed. It is worth it when:

- the computation is expensive relative to the lookup;
- the data is read far more often than it changes;
- a stale value is acceptable for some bounded period, or invalidation is reliable.

```typescript
function memoize<A, R>(fn: (arg: A) => R): (arg: A) => R {
  const cache = new Map<A, R>();
  return (arg: A): R => {
    if (cache.has(arg)) return cache.get(arg) as R;
    const result = fn(arg);
    cache.set(arg, result);
    return result;
  };
}

// Bounded variant: evict the oldest entry when the limit is reached.
function memoizeBounded<A, R>(fn: (arg: A) => R, limit: number): (arg: A) => R {
  const cache = new Map<A, R>();
  return (arg: A): R => {
    const hit = cache.get(arg);
    if (hit !== undefined) return hit;
    const result = fn(arg);
    cache.set(arg, result);
    if (cache.size > limit) {
      const oldest = cache.keys().next().value;
      if (oldest !== undefined) cache.delete(oldest);
    }
    return result;
  };
}
```

Caches introduce their own failure modes: unbounded growth, stale data, thundering herds on expiry, and invalidation bugs that are hard to reproduce. A cache is a correctness decision disguised as a performance decision.

### Reducing work

Often the best optimization is to not do the work:

- **Lazy evaluation:** compute only what is used.
- **Early exit:** stop when the answer is known.
- **Pagination and limits:** never load a million rows to display twenty.
- **Projection:** select only the columns needed.
- **Compression:** trade CPU for network and storage.
- **Deferral:** move work off the request path into a queue.

### Concurrency and parallelism

Useful when work is independent and the bottleneck is CPU or I/O latency. It adds coordination cost, so it pays only when the parallelism is substantial and the shared state is small. Chapter 20 covers the design constraints.

## 19.6 The cost of optimization

Optimized code is usually more complex, more fragile, and harder to change. That cost is worth paying only when the measured benefit exceeds it.

- **Complexity.** Manual loop unrolling, custom allocators, bit packing, and hand-tuned data layouts are hard to read and easy to break.
- **Correctness risk.** Caching introduces staleness; batching changes failure semantics; parallelism introduces races; memoization can leak memory.
- **Portability.** An optimization tuned for one runtime or CPU may be slower elsewhere.
- **Maintenance.** The next developer must understand why the code is shaped oddly, or they will "simplify" it back to the slow version.

**Rules of thumb:**

1. Make it correct first.
2. Make it clear second.
3. Measure against a stated requirement.
4. Optimize the dominant cost.
5. Keep the benchmark and the requirement with the code, so the optimization can be justified and revisited.
6. Prefer algorithmic and structural fixes to micro-optimizations.
7. Revert optimizations that do not show a measurable improvement.

> **The first rule of optimization is: don't. The second is: don't yet. The third is: measure before you do.** The order matters—the prohibition is against guessing, not against optimizing.

## 19.7 A worked example

A report endpoint takes 4.2 seconds at p95. The requirement is under 800 ms for 10,000 orders.

**Measure.** Profiling shows: 3.1 s in `attachCustomers` (one query per order), 0.6 s in template rendering, 0.3 s in serialization, 0.2 s elsewhere.

**Analyze.** 74% of the time is N+1 queries. Amdahl's law says fixing it perfectly yields at most 1 / 0.26 ≈ 3.8×, taking 4.2 s to about 1.1 s—closer, but not enough.

**Fix the dominant cost.** Batch the customer query: 3.1 s becomes 0.15 s. Total: about 1.25 s.

**Re-measure.** Rendering is now 48% of the time. The template does a linear scan over orders for each row to compute a running total—O(n²) in the number of orders. Replace it with a single pass: 0.6 s becomes 0.05 s. Total: about 0.7 s.

**Verify.** p95 is now 0.68 s, under the 800 ms target. Add a benchmark that runs the report against 10,000 orders and asserts a budget, so a future change that reintroduces N+1 queries fails loudly.

The example illustrates the general shape: measure, fix the largest term, re-measure, repeat until the requirement is met—then stop. Continuing past the requirement is optimizing something nobody asked for, at a cost someone will pay later.

![Buffer allocation before optimization.](assets/buffer-allocation-before.jpg){width=70%}

![The optimized allocation path.](assets/buffer-allocation-after.jpg){width=55%}

## Summary

- A performance requirement needs a measure, a workload, and a threshold; "fast" is not a requirement.
- Measure with realistic inputs, warm-up, and distributions; microbenchmarks and averages mislead.
- Profile to find the dominant cost; flame graphs show where time actually goes.
- Algorithmic and data-structure choices dominate; an accidental O(n) inside a loop is the most common defect.
- Amdahl's law bounds the gain: optimize the largest fraction, then re-measure.
- The structural optimizations that still matter are algorithms, batching, caching, reducing work, and judicious parallelism.
- Optimized code is more complex and more fragile; pay that cost only for a measured benefit against a stated requirement.

## Exercises

1. **Write a requirement.** Convert "the search page should be fast" into a measure, a workload, and a threshold. What measurement method would verify it?
2. **Benchmark honestly.** Write a benchmark for a function you own. Report median and p95 over at least 200 iterations with warm-up. How different are they?
3. **Find the accidental O(n²).** Search a codebase for `.find(`, `.filter(`, or `.includes(` inside a loop. Estimate n for the realistic workload. Fix one with a `Map` or `Set`.
4. **Profile a real path.** Profile an endpoint or command. Identify the top three costs by percentage. Which one would you fix first, and what is the Amdahl ceiling if you make it free?
5. **Batch a round trip.** Find an N+1 pattern (database, HTTP, file reads). Rewrite it as a single batched call and compare latency and failure behavior.
6. **Cache with a bound.** Add a cache to an expensive pure function. Include a size limit and a reason for the limit. What is the invalidation story?
7. **Justify an optimization.** Find a piece of code that was optimized (unrolled loop, custom structure, manual bit packing). Can you reconstruct the measurement that justified it? If not, what would you do?
8. **Amdahl exercise.** A pipeline spends 50% in parsing, 30% in computation, and 20% in I/O. What is the maximum speedup from making parsing free? From making I/O free? Which investment is worth more?
