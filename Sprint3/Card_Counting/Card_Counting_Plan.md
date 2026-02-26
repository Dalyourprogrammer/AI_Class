# Card Counting GA Strategy Evolution — Design Summary

## Goal
Extend the BlackJack GA to co-evolve a card-counting system alongside a hit/stand strategy and adaptive bet sizing. Fitness is final bankroll after 1,000 hands on a 6-deck shoe (starting $1,000), rewarding strategies that exploit count information for profit.

---

## Chromosome Encoding (294 bits)

| Component | Bits | Size | Description |
|-----------|------|------|-------------|
| Play strategy | 0–259 | 260 bits | 17×10 hard hands + 9×10 soft hands (hit=1 / stand=0) |
| Count values | 260–281 | 22 bits | 11 card ranks × 2 bits → {−1, 0, +1} |
| Bet multipliers | 282–293 | 12 bits | 4 true-count ranges × 3 bits → multiplier 1–8 |

### Component 1: Play Strategy (bits 0–259)
Identical to the basic BlackJack GA — see `Sprint3/BlackJack/BlackJack_Plan.md`.

### Component 2: Count Values (bits 260–281)
Each pair of bits encodes a count increment for one card rank:

| Bits | Value |
|------|-------|
| 00   | −1    |
| 01   |  0    |
| 10   | +1    |
| 11   | +1    |

11 rank indices in order: A, 2, 3, 4, 5, 6, 7, 8, 9, 10, Face(J/Q/K)

> Face cards are represented with distinct rank values (J=11, Q=12, K=13) in the shoe for counting purposes, but play as game-value 10.

### Component 3: Bet Multipliers (bits 282–293)
3 bits → unsigned int (0–7) + 1 = multiplier 1–8.

| Range idx | True Count | Bits    |
|-----------|-----------|---------|
| 0         | TC ≤ 0    | 282–284 |
| 1         | 1 ≤ TC ≤ 2 | 285–287 |
| 2         | 3 ≤ TC ≤ 4 | 288–290 |
| 3         | TC ≥ 5    | 291–293 |

---

## Simulation

### Shoe
- 6 standard decks (312 cards), ranks 1–13.
- Shuffled once at session start; reshuffled when the cut card is reached (~52 cards remaining).
- Running count resets to 0 after each reshuffle.

### Running Count & True Count
```
running_count += count_value[rank]   # for each visible card
decks_remaining = (shoe_length - shoe_pos) / 52
true_count = round(running_count / decks_remaining)
```

### Bet Sizing (per hand)
```
multiplier = bet_multipliers[true_count_range(true_count)]
bet = clamp(multiplier, MIN_BET=1, min(MAX_BET=8, bankroll))
```

### Hand Outcomes
| Result | Bankroll change |
|--------|----------------|
| Player natural (3:2) | +1.5 × bet |
| Win | +bet |
| Push | 0 |
| Loss | −bet |

If bankroll reaches $0, the session ends immediately — fitness = 0.

### Fitness
`fitness = final_bankroll` after up to 1,000 hands (0 if bankrupt).

---

## GA Parameters

| Parameter | Value |
|-----------|-------|
| Population size | 100 |
| Generations | 50 |
| Hands per evaluation | 1,000 |
| Mutation rate | 0.01/bit |
| Elitism | Top 2 copied unchanged |
| Selection | Roulette wheel (fitness-proportional) |
| Crossover | Single-point |
| Chromosome length | **294 bits** |

---

## Outputs

| File | Description |
|------|-------------|
| `fitness_plot.png` | Min/max/mean/median bankroll over 50 generations |
| `strategy_heatmap.png` | Hit-frequency heatmaps (hard & soft) from final population |
| `count_values.png` | Grouped bar chart: evolved count values vs Hi-Lo reference |
| `bankroll_history.png` | Bankroll trajectory over 1,000 hands for best individual |
| Console | Per-generation stats, evolved count table, bet multiplier table |

### Hi-Lo Reference (for comparison)
| Rank | A | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | Face |
|------|---|---|---|---|---|---|---|---|---|----|------|
| Hi-Lo | −1 | +1 | +1 | +1 | +1 | +1 | 0 | 0 | 0 | −1 | −1 |
