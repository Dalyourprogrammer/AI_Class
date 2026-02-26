#!/usr/bin/env python3
"""Genetic Algorithm for evolving Blackjack hit/stand strategies.

Evolves 260-bit chromosomes encoding hit(1)/stand(0) decisions for every
player-total / dealer-up-card combination in single-deck blackjack.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── Constants ────────────────────────────────────────────────────────────────
POP_SIZE = 100
GENERATIONS = 50
HANDS_PER_EVAL = 1000
MUTATION_RATE = 0.01
ELITE_COUNT = 2
CHROMOSOME_LEN = 260

# ── Deck / Hand Utilities ────────────────────────────────────────────────────

def make_deck():
    """Return a 52-card array: values 1-10 with face cards worth 10."""
    card = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10]
    return np.array(card * 4, dtype=np.int32)


def hand_value(cards):
    """Return (total, is_soft) for a hand of cards.

    Promotes one ace from 1 to 11 if doing so keeps total <= 21.
    """
    total = int(np.sum(cards))
    is_soft = False
    if 1 in cards and total + 10 <= 21:
        total += 10
        is_soft = True
    return total, is_soft


# ── Chromosome Indexing ──────────────────────────────────────────────────────

def dealer_col(up_card):
    """Map dealer up-card to column index 0-9. Ace=0, 2=1, ..., 10=9."""
    if up_card == 1:
        return 0
    return up_card - 1


def strategy_index(player_total, is_soft, up_card):
    """Return the chromosome bit index for a given game state.

    Hard hands (bits 0-169): totals 4-20 (17 rows) x 10 dealer columns.
    Soft hands (bits 170-259): totals 12-20 (9 rows) x 10 dealer columns.
    """
    dc = dealer_col(up_card)
    if not is_soft:
        return (player_total - 4) * 10 + dc
    else:
        return 170 + (player_total - 12) * 10 + dc


# ── Blackjack Simulation ────────────────────────────────────────────────────

def simulate_one_hand(strategy, deck, rng):
    """Play one hand of blackjack using the given strategy chromosome.

    Returns 1.0 (win), 0.5 (push), or 0.0 (loss).
    """
    rng.shuffle(deck)
    pos = 0

    # Deal: player card, dealer card, player card, dealer hole card
    player_cards = [deck[0], deck[2]]
    dealer_cards = [deck[1], deck[3]]
    pos = 4

    # Check naturals (blackjack = 21 with 2 cards)
    p_val, _ = hand_value(np.array(player_cards))
    d_val, _ = hand_value(np.array(dealer_cards))

    if p_val == 21 and d_val == 21:
        return 0.5
    if p_val == 21:
        return 1.0
    if d_val == 21:
        return 0.0

    # Player's turn — hit according to strategy
    while True:
        p_val, p_soft = hand_value(np.array(player_cards))
        if p_val >= 21:
            break
        idx = strategy_index(p_val, p_soft, dealer_cards[0])
        if strategy[idx] == 0:  # stand
            break
        player_cards.append(deck[pos])
        pos += 1

    p_val, _ = hand_value(np.array(player_cards))
    if p_val > 21:
        return 0.0  # player busts

    # Dealer's turn — hit on 16 or less, stand on 17+
    while True:
        d_val, _ = hand_value(np.array(dealer_cards))
        if d_val >= 17:
            break
        dealer_cards.append(deck[pos])
        pos += 1

    d_val, _ = hand_value(np.array(dealer_cards))
    if d_val > 21:
        return 1.0  # dealer busts

    # Compare
    if p_val > d_val:
        return 1.0
    elif p_val == d_val:
        return 0.5
    else:
        return 0.0


def evaluate_fitness(strategy, n_hands, rng):
    """Return average win rate over n_hands (push counts as 0.5)."""
    deck = make_deck()
    total = 0.0
    for _ in range(n_hands):
        total += simulate_one_hand(strategy, deck, rng)
    return total / n_hands


# ── GA Operators ─────────────────────────────────────────────────────────────

def init_population(rng):
    """Create random initial population of binary chromosomes."""
    return rng.integers(0, 2, size=(POP_SIZE, CHROMOSOME_LEN), dtype=np.int8)


def roulette_selection(population, fitnesses, rng):
    """Select one individual via fitness-proportional roulette wheel."""
    total = fitnesses.sum()
    if total == 0:
        return population[rng.integers(POP_SIZE)]
    pick = rng.random() * total
    cumsum = 0.0
    for i, f in enumerate(fitnesses):
        cumsum += f
        if cumsum >= pick:
            return population[i].copy()
    return population[-1].copy()


def crossover(parent1, parent2, rng):
    """Single-point crossover producing two children."""
    point = rng.integers(1, CHROMOSOME_LEN)
    child1 = np.concatenate([parent1[:point], parent2[point:]])
    child2 = np.concatenate([parent2[:point], parent1[point:]])
    return child1, child2


def mutate(chromosome, rng):
    """Flip each bit with probability MUTATION_RATE (vectorized)."""
    mask = rng.random(CHROMOSOME_LEN) < MUTATION_RATE
    chromosome[mask] = 1 - chromosome[mask]
    return chromosome


def evolve_one_generation(population, fitnesses, rng):
    """Produce next generation: elites + crossover/mutation offspring."""
    new_pop = np.empty_like(population)

    # Elitism: copy top ELITE_COUNT unchanged
    elite_idx = np.argsort(fitnesses)[-ELITE_COUNT:]
    for i, idx in enumerate(elite_idx):
        new_pop[i] = population[idx].copy()

    # Fill remaining slots with crossover + mutation
    num_pairs = (POP_SIZE - ELITE_COUNT) // 2
    pos = ELITE_COUNT
    for _ in range(num_pairs):
        p1 = roulette_selection(population, fitnesses, rng)
        p2 = roulette_selection(population, fitnesses, rng)
        c1, c2 = crossover(p1, p2, rng)
        new_pop[pos] = mutate(c1, rng)
        new_pop[pos + 1] = mutate(c2, rng)
        pos += 2

    return new_pop


# ── Visualization ────────────────────────────────────────────────────────────

def plot_fitness(history, filename="fitness_plot.png"):
    """Plot min/max/mean/median fitness across generations."""
    gens = range(len(history["mean"]))
    plt.figure(figsize=(10, 6))
    plt.plot(gens, history["max"], label="Max", linewidth=2)
    plt.plot(gens, history["mean"], label="Mean", linewidth=2)
    plt.plot(gens, history["median"], label="Median", linewidth=2, linestyle="--")
    plt.plot(gens, history["min"], label="Min", linewidth=2, linestyle=":")
    plt.xlabel("Generation")
    plt.ylabel("Win Rate")
    plt.title("Blackjack GA — Fitness Over Generations")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()
    print(f"Saved {filename}")


def plot_strategy_heatmap(population, filename="strategy_heatmap.png"):
    """Plot heatmaps showing hit-frequency for hard and soft hands."""
    # Compute mean strategy across final population
    mean_strat = population.mean(axis=0)  # fraction choosing hit

    # Hard hands: rows = player total 4-20, cols = dealer up Ace,2..10
    hard = np.zeros((17, 10))
    for row, ptotal in enumerate(range(4, 21)):
        for col in range(10):
            hard[row, col] = mean_strat[(ptotal - 4) * 10 + col]

    # Soft hands: rows = player total 12-20, cols = dealer up Ace,2..10
    soft = np.zeros((9, 10))
    for row, ptotal in enumerate(range(12, 21)):
        for col in range(10):
            soft[row, col] = mean_strat[170 + (ptotal - 12) * 10 + col]

    col_labels = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 8))

    # Hard hands heatmap
    im1 = ax1.imshow(hard, cmap="RdBu_r", vmin=0, vmax=1, aspect="auto")
    ax1.set_xticks(range(10))
    ax1.set_xticklabels(col_labels)
    ax1.set_yticks(range(17))
    ax1.set_yticklabels(range(4, 21))
    ax1.set_xlabel("Dealer Up Card")
    ax1.set_ylabel("Player Total")
    ax1.set_title("Hard Hands (Red=Hit, Blue=Stand)")
    for r in range(17):
        for c in range(10):
            ax1.text(c, r, f"{hard[r, c]:.0%}", ha="center", va="center",
                     fontsize=6, color="white" if 0.3 < hard[r, c] < 0.7 else "black")

    # Soft hands heatmap
    im2 = ax2.imshow(soft, cmap="RdBu_r", vmin=0, vmax=1, aspect="auto")
    ax2.set_xticks(range(10))
    ax2.set_xticklabels(col_labels)
    ax2.set_yticks(range(9))
    ax2.set_yticklabels(range(12, 21))
    ax2.set_xlabel("Dealer Up Card")
    ax2.set_ylabel("Player Total")
    ax2.set_title("Soft Hands (Red=Hit, Blue=Stand)")
    for r in range(9):
        for c in range(10):
            ax2.text(c, r, f"{soft[r, c]:.0%}", ha="center", va="center",
                     fontsize=6, color="white" if 0.3 < soft[r, c] < 0.7 else "black")

    fig.colorbar(im1, ax=[ax1, ax2], shrink=0.6, label="Hit Frequency")
    fig.suptitle("Evolved Blackjack Strategy — Final Population", fontsize=14)
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()
    print(f"Saved {filename}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    rng = np.random.default_rng(42)
    population = init_population(rng)

    history = {"min": [], "max": [], "mean": [], "median": []}

    print(f"Blackjack GA — {POP_SIZE} individuals, {GENERATIONS} generations, "
          f"{HANDS_PER_EVAL} hands/eval")
    print("-" * 65)

    for gen in range(GENERATIONS):
        # Evaluate fitness for all individuals
        fitnesses = np.array([
            evaluate_fitness(population[i], HANDS_PER_EVAL, rng)
            for i in range(POP_SIZE)
        ])

        # Record statistics
        history["min"].append(fitnesses.min())
        history["max"].append(fitnesses.max())
        history["mean"].append(fitnesses.mean())
        history["median"].append(np.median(fitnesses))

        print(f"Gen {gen:3d} | Min: {fitnesses.min():.4f}  "
              f"Mean: {fitnesses.mean():.4f}  "
              f"Median: {np.median(fitnesses):.4f}  "
              f"Max: {fitnesses.max():.4f}")

        # Evolve (skip on last generation to keep final population)
        if gen < GENERATIONS - 1:
            population = evolve_one_generation(population, fitnesses, rng)

    print("-" * 65)
    best_idx = np.argmax(fitnesses)
    print(f"Best final fitness: {fitnesses[best_idx]:.4f}")

    # Generate plots
    plot_fitness(history)
    plot_strategy_heatmap(population)


if __name__ == "__main__":
    main()
