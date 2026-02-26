# Blackjack GA Strategy Evolution — Design Summary

## Goal
Evolve optimal hit/stand strategies for single-deck blackjack using a genetic algorithm. Target: converge toward ~49.5% win rate (pushes scored as 0.5 wins).

## Chromosome Encoding (260 bits)
Each individual is a 260-bit binary string mapping every (player total, dealer up-card) state to **hit (1)** or **stand (0)**.

| Segment | Bits | Rows | Player Totals |
|---------|------|------|---------------|
| Hard hands | 0–169 | 17 | 4–20 |
| Soft hands | 170–259 | 9 | 12–20 |

Each row has 10 columns for dealer up-cards: Ace, 2, 3, …, 10.

## Simulation
- **Single deck:** 52 cards, reshuffled each hand.
- **Naturals** checked before player action.
- **Dealer rule:** hit on 16 or less, stand on 17+.
- **Fitness:** average result over 1,000 hands (1.0 = win, 0.5 = push, 0.0 = loss).

## GA Parameters
| Parameter | Value |
|-----------|-------|
| Population size | 100 |
| Generations | 50 |
| Hands per evaluation | 1,000 |
| Mutation rate | 0.01 per bit |
| Elitism | Top 2 copied unchanged |
| Selection | Roulette wheel (fitness-proportional) |
| Crossover | Single-point |

## Pipeline (per generation)
1. Evaluate all 100 individuals (1,000 hands each).
2. Record min / max / mean / median fitness.
3. Copy top 2 elites to next generation.
4. Fill remaining 98 slots via roulette selection → single-point crossover → bit-flip mutation.

## Outputs
- **Console:** per-generation fitness statistics.
- **`fitness_plot.png`:** min / max / mean / median fitness curves over generations.
- **`strategy_heatmap.png`:** two heatmaps (hard & soft hands) showing hit frequency across the final population, color-coded red (hit) to blue (stand).
