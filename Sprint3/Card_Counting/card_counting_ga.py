#!/usr/bin/env python3
"""Genetic Algorithm for evolving Blackjack card-counting strategies.

Chromosome (294 bits):
  - Bits   0–259: Play strategy — identical 17×10 hard + 9×10 soft hit/stand table.
  - Bits 260–281: Count values — 11 card ranks × 2 bits → {−1, 0, +1}.
  - Bits 282–293: Bet multipliers — 4 true-count ranges × 3 bits → multiplier 1–8.

Fitness: final bankroll (starting $1,000) after 1,000 hands on a 6-deck shoe.
Blackjacks pay 3:2. Bankrupt (≤$0) → fitness 0.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── Constants ─────────────────────────────────────────────────────────────────
POP_SIZE        = 100
GENERATIONS     = 50
HANDS_PER_EVAL  = 1000
MUTATION_RATE   = 0.01
ELITE_COUNT     = 2

PLAY_BITS       = 260
COUNT_BITS      = 22   # 11 ranks × 2 bits
BET_BITS        = 12   # 4 ranges × 3 bits
CHROMOSOME_LEN  = PLAY_BITS + COUNT_BITS + BET_BITS  # 294

NUM_DECKS       = 6
CUT_CARD        = NUM_DECKS * 52 - 52   # reshuffle when 1 deck remains (~260)
STARTING_BANKROLL = 1000.0
MIN_BET         = 1
MAX_BET         = 8

# Hi-Lo reference values for comparison (index order: A,2,3,4,5,6,7,8,9,10,face)
HILO_VALUES = [-1, +1, +1, +1, +1, +1, 0, 0, 0, -1, -1]
RANK_LABELS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "Face"]

# ── Deck / Hand Utilities ─────────────────────────────────────────────────────

def make_shoe(n_decks=NUM_DECKS):
    """Return an unshuffled shoe array using ranks 1–13.

    Ranks 1=A, 2–9=pip, 10=ten, 11=J, 12=Q, 13=K.
    One standard 13-rank deck × 4 suits × n_decks.
    """
    one_deck = list(range(1, 14)) * 4   # 52 cards
    return np.array(one_deck * n_decks, dtype=np.int32)


def game_value(rank):
    """Convert rank to blackjack game value (face cards = 10, ace = 1)."""
    return int(min(rank, 10))


def hand_value(ranks):
    """Return (total, is_soft) for a list of card ranks.

    Promotes one ace from 1 to 11 if it keeps total ≤ 21.
    """
    cards = [game_value(r) for r in ranks]
    total = sum(cards)
    is_soft = False
    if 1 in cards and total + 10 <= 21:
        total += 10
        is_soft = True
    return total, is_soft


def rank_to_count_index(rank):
    """Map card rank (1–13) to count-value index (0–10).

    0=A, 1=2, 2=3, ..., 8=9, 9=10, 10=face(J/Q/K).
    """
    if rank == 1:
        return 0
    elif rank <= 9:
        return rank - 1   # 2→1, 3→2, ..., 9→8
    elif rank == 10:
        return 9
    else:                  # J=11, Q=12, K=13
        return 10


# ── Chromosome Indexing (play strategy) ──────────────────────────────────────

def dealer_col(up_card_rank):
    """Map dealer up-card rank to column index 0–9. Ace=0, 2=1, …, 10=9."""
    gv = game_value(up_card_rank)
    if gv == 1:
        return 0
    return gv - 1


def strategy_index(player_total, is_soft, up_card_rank):
    """Return chromosome bit index for (player_total, is_soft, up_card).

    Hard hands (bits 0–169):  totals 4–20, 17 rows × 10 cols.
    Soft hands (bits 170–259): totals 12–20, 9 rows × 10 cols.
    """
    dc = dealer_col(up_card_rank)
    if not is_soft:
        return (player_total - 4) * 10 + dc
    else:
        return 170 + (player_total - 12) * 10 + dc


# ── Chromosome Decoding ───────────────────────────────────────────────────────

_COUNT_MAP = {(0, 0): -1, (0, 1): 0, (1, 0): 1, (1, 1): 1}

def decode_count_values(chromosome):
    """Decode bits 260–281 → list of 11 ints in {−1, 0, +1}."""
    vals = []
    for i in range(11):
        b0 = int(chromosome[PLAY_BITS + i * 2])
        b1 = int(chromosome[PLAY_BITS + i * 2 + 1])
        vals.append(_COUNT_MAP[(b0, b1)])
    return vals


def decode_bet_multipliers(chromosome):
    """Decode bits 282–293 → list of 4 ints in [1, 8]."""
    mults = []
    base = PLAY_BITS + COUNT_BITS
    for i in range(4):
        b0 = int(chromosome[base + i * 3])
        b1 = int(chromosome[base + i * 3 + 1])
        b2 = int(chromosome[base + i * 3 + 2])
        mults.append(b0 * 4 + b1 * 2 + b2 + 1)   # 0–7 + 1 → 1–8
    return mults


def true_count_range(tc):
    """Map true count to bet-multiplier range index (0–3)."""
    if tc <= 0:
        return 0
    elif tc <= 2:
        return 1
    elif tc <= 4:
        return 2
    else:
        return 3


# ── Blackjack Simulation ──────────────────────────────────────────────────────

def simulate_hand(strategy, shoe, pos, running_count, count_vals):
    """Play one hand from the shoe.

    Returns:
        result       : 'blackjack' | 'win' | 'push' | 'loss'
        new_pos      : updated shoe position
        new_rc       : updated running count
    """
    # Deal: player, dealer, player, dealer-hole
    p_ranks = [shoe[pos], shoe[pos + 2]]
    d_ranks = [shoe[pos + 1], shoe[pos + 3]]
    pos += 4

    # Update running count for all dealt (visible) cards
    # Dealer hole card is face-down — only up-card counted now; hole counted when revealed
    rc = running_count
    for r in p_ranks:
        rc += count_vals[rank_to_count_index(r)]
    rc += count_vals[rank_to_count_index(d_ranks[0])]   # dealer up-card only

    p_val, _ = hand_value(p_ranks)
    d_val, _ = hand_value(d_ranks)

    # Check naturals
    if p_val == 21 and d_val == 21:
        rc += count_vals[rank_to_count_index(d_ranks[1])]  # hole revealed
        return "push", pos, rc
    if p_val == 21:
        rc += count_vals[rank_to_count_index(d_ranks[1])]  # hole revealed
        return "blackjack", pos, rc
    if d_val == 21:
        rc += count_vals[rank_to_count_index(d_ranks[1])]  # hole revealed
        return "loss", pos, rc

    # Player's turn
    while True:
        p_val, p_soft = hand_value(p_ranks)
        if p_val >= 21:
            break
        idx = strategy_index(p_val, p_soft, d_ranks[0])
        if strategy[idx] == 0:   # stand
            break
        p_ranks.append(shoe[pos])
        rc += count_vals[rank_to_count_index(shoe[pos])]
        pos += 1

    p_val, _ = hand_value(p_ranks)
    if p_val > 21:
        # Reveal dealer hole card even on player bust (good counting practice)
        rc += count_vals[rank_to_count_index(d_ranks[1])]
        return "loss", pos, rc

    # Dealer's turn — hits on 16 or less, stands on 17+
    rc += count_vals[rank_to_count_index(d_ranks[1])]   # hole revealed
    while True:
        d_val, _ = hand_value(d_ranks)
        if d_val >= 17:
            break
        d_ranks.append(shoe[pos])
        rc += count_vals[rank_to_count_index(shoe[pos])]
        pos += 1

    d_val, _ = hand_value(d_ranks)
    if d_val > 21:
        return "win", pos, rc

    if p_val > d_val:
        return "win", pos, rc
    elif p_val == d_val:
        return "push", pos, rc
    else:
        return "loss", pos, rc


def simulate_session(chromosome, n_hands=HANDS_PER_EVAL, rng=None, track_history=False):
    """Simulate a full session and return final bankroll.

    If track_history=True also returns list of bankroll-per-hand.
    """
    if rng is None:
        rng = np.random.default_rng()

    strategy    = chromosome[:PLAY_BITS]
    count_vals  = decode_count_values(chromosome)
    bet_mults   = decode_bet_multipliers(chromosome)

    shoe = make_shoe(NUM_DECKS)
    rng.shuffle(shoe)
    pos           = 0
    running_count = 0
    bankroll      = STARTING_BANKROLL
    history       = [] if track_history else None

    for _ in range(n_hands):
        if bankroll <= 0:
            break

        # Reshuffle check
        if pos >= CUT_CARD:
            rng.shuffle(shoe)
            pos           = 0
            running_count = 0

        # True count and bet
        decks_remaining = (len(shoe) - pos) / 52.0
        if decks_remaining >= 0.5:
            tc = int(round(running_count / decks_remaining))
        else:
            tc = 0

        multiplier = bet_mults[true_count_range(tc)]
        bet = float(min(multiplier, min(MAX_BET, bankroll)))
        bet = max(bet, MIN_BET)

        # Play hand
        result, pos, running_count = simulate_hand(
            strategy, shoe, pos, running_count, count_vals
        )

        # Bankroll update
        if result == "blackjack":
            bankroll += bet * 1.5
        elif result == "win":
            bankroll += bet
        elif result == "loss":
            bankroll -= bet
        # push → no change

        if track_history:
            history.append(bankroll)

    if track_history:
        return bankroll, history
    return bankroll


def evaluate_fitness(chromosome, n_hands=HANDS_PER_EVAL, rng=None):
    """Return final bankroll (fitness) for one chromosome."""
    return simulate_session(chromosome, n_hands=n_hands, rng=rng)


# ── GA Operators ──────────────────────────────────────────────────────────────

def init_population(rng):
    """Create random initial population of 294-bit binary chromosomes."""
    return rng.integers(0, 2, size=(POP_SIZE, CHROMOSOME_LEN), dtype=np.int8)


def roulette_selection(population, fitnesses, rng):
    """Select one individual via fitness-proportional roulette wheel."""
    total = fitnesses.sum()
    if total == 0:
        return population[rng.integers(POP_SIZE)].copy()
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
    """Flip each bit with probability MUTATION_RATE."""
    mask = rng.random(CHROMOSOME_LEN) < MUTATION_RATE
    chromosome[mask] = 1 - chromosome[mask]
    return chromosome


def evolve_one_generation(population, fitnesses, rng):
    """Produce next generation: elites + crossover/mutation offspring."""
    new_pop = np.empty_like(population)

    elite_idx = np.argsort(fitnesses)[-ELITE_COUNT:]
    for i, idx in enumerate(elite_idx):
        new_pop[i] = population[idx].copy()

    num_pairs = (POP_SIZE - ELITE_COUNT) // 2
    pos = ELITE_COUNT
    for _ in range(num_pairs):
        p1 = roulette_selection(population, fitnesses, rng)
        p2 = roulette_selection(population, fitnesses, rng)
        c1, c2 = crossover(p1, p2, rng)
        new_pop[pos]     = mutate(c1, rng)
        new_pop[pos + 1] = mutate(c2, rng)
        pos += 2

    return new_pop


# ── Visualization ─────────────────────────────────────────────────────────────

def plot_fitness(history, filename="fitness_plot.png"):
    """Plot min/max/mean/median bankroll across generations."""
    gens = range(len(history["mean"]))
    plt.figure(figsize=(10, 6))
    plt.plot(gens, history["max"],    label="Max",    linewidth=2)
    plt.plot(gens, history["mean"],   label="Mean",   linewidth=2)
    plt.plot(gens, history["median"], label="Median", linewidth=2, linestyle="--")
    plt.plot(gens, history["min"],    label="Min",    linewidth=2, linestyle=":")
    plt.axhline(STARTING_BANKROLL, color="gray", linestyle="-.", linewidth=1,
                label=f"Start (${STARTING_BANKROLL:.0f})")
    plt.xlabel("Generation")
    plt.ylabel("Bankroll ($)")
    plt.title("Card Counting GA — Bankroll Over Generations")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()
    print(f"Saved {filename}")


def plot_strategy_heatmap(population, filename="strategy_heatmap.png"):
    """Plot hit-frequency heatmaps (hard & soft hands) from final population."""
    mean_strat = population[:, :PLAY_BITS].mean(axis=0)

    hard = np.zeros((17, 10))
    for row, ptotal in enumerate(range(4, 21)):
        for col in range(10):
            hard[row, col] = mean_strat[(ptotal - 4) * 10 + col]

    soft = np.zeros((9, 10))
    for row, ptotal in enumerate(range(12, 21)):
        for col in range(10):
            soft[row, col] = mean_strat[170 + (ptotal - 12) * 10 + col]

    col_labels = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 8))

    im1 = ax1.imshow(hard, cmap="RdBu_r", vmin=0, vmax=1, aspect="auto")
    ax1.set_xticks(range(10)); ax1.set_xticklabels(col_labels)
    ax1.set_yticks(range(17)); ax1.set_yticklabels(range(4, 21))
    ax1.set_xlabel("Dealer Up Card"); ax1.set_ylabel("Player Total")
    ax1.set_title("Hard Hands (Red=Hit, Blue=Stand)")
    for r in range(17):
        for c in range(10):
            ax1.text(c, r, f"{hard[r, c]:.0%}", ha="center", va="center",
                     fontsize=6, color="white" if 0.3 < hard[r, c] < 0.7 else "black")

    im2 = ax2.imshow(soft, cmap="RdBu_r", vmin=0, vmax=1, aspect="auto")
    ax2.set_xticks(range(10)); ax2.set_xticklabels(col_labels)
    ax2.set_yticks(range(9));  ax2.set_yticklabels(range(12, 21))
    ax2.set_xlabel("Dealer Up Card"); ax2.set_ylabel("Player Total")
    ax2.set_title("Soft Hands (Red=Hit, Blue=Stand)")
    for r in range(9):
        for c in range(10):
            ax2.text(c, r, f"{soft[r, c]:.0%}", ha="center", va="center",
                     fontsize=6, color="white" if 0.3 < soft[r, c] < 0.7 else "black")

    fig.colorbar(im1, ax=[ax1, ax2], shrink=0.6, label="Hit Frequency")
    fig.suptitle("Evolved Card-Counting GA Strategy — Final Population", fontsize=14)
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()
    print(f"Saved {filename}")


def plot_count_comparison(best_chromosome, filename="count_values.png"):
    """Bar chart comparing evolved count values vs Hi-Lo for all 11 ranks."""
    evolved = decode_count_values(best_chromosome)

    x = np.arange(11)
    width = 0.35
    fig, ax = plt.subplots(figsize=(12, 5))
    bars1 = ax.bar(x - width / 2, evolved,     width, label="Evolved", color="steelblue")
    bars2 = ax.bar(x + width / 2, HILO_VALUES, width, label="Hi-Lo",   color="tomato", alpha=0.8)

    ax.set_xticks(x)
    ax.set_xticklabels(RANK_LABELS)
    ax.set_yticks([-1, 0, 1])
    ax.set_yticklabels(["-1", "0", "+1"])
    ax.set_xlabel("Card Rank")
    ax.set_ylabel("Count Value")
    ax.set_title("Evolved Count Values vs Hi-Lo System")
    ax.legend()
    ax.axhline(0, color="black", linewidth=0.8)
    ax.grid(axis="y", alpha=0.3)

    # Annotate bars
    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                f"{int(bar.get_height()):+d}", ha="center", va="bottom", fontsize=9)
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                f"{int(bar.get_height()):+d}", ha="center", va="bottom", fontsize=9)

    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()
    print(f"Saved {filename}")


def plot_bankroll_history(best_chromosome, rng, filename="bankroll_history.png"):
    """Plot bankroll trajectory over 1,000 hands for the best individual."""
    _, history = simulate_session(best_chromosome, n_hands=HANDS_PER_EVAL,
                                  rng=rng, track_history=True)
    plt.figure(figsize=(12, 5))
    plt.plot(range(1, len(history) + 1), history, linewidth=1, color="steelblue")
    plt.axhline(STARTING_BANKROLL, color="gray", linestyle="--", linewidth=1,
                label=f"Start (${STARTING_BANKROLL:.0f})")
    plt.xlabel("Hand Number")
    plt.ylabel("Bankroll ($)")
    plt.title("Best Individual — Bankroll Over 1,000-Hand Session")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()
    print(f"Saved {filename}")


# ── Console Output Helpers ────────────────────────────────────────────────────

def print_count_table(chromosome):
    """Print evolved count values for each rank alongside Hi-Lo reference."""
    evolved = decode_count_values(chromosome)
    print("\nEvolved Count Values vs Hi-Lo:")
    print(f"  {'Rank':<8} {'Evolved':>8} {'Hi-Lo':>8} {'Match':>6}")
    print("  " + "-" * 36)
    for i, label in enumerate(RANK_LABELS):
        match = "✓" if evolved[i] == HILO_VALUES[i] else " "
        print(f"  {label:<8} {evolved[i]:>+8} {HILO_VALUES[i]:>+8} {match:>6}")


def print_bet_table(chromosome):
    """Print evolved bet multipliers for each true-count range."""
    mults = decode_bet_multipliers(chromosome)
    ranges = ["TC ≤ 0", "TC 1–2", "TC 3–4", "TC ≥ 5"]
    print("\nEvolved Bet Multipliers:")
    print(f"  {'Range':<12} {'Multiplier':>12} {'Bet ($)':>10}")
    print("  " + "-" * 36)
    for label, m in zip(ranges, mults):
        print(f"  {label:<12} {m:>12}x  ${m:>8}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    import os
    out_dir = os.path.dirname(os.path.abspath(__file__))

    rng = np.random.default_rng(42)
    population = init_population(rng)

    history = {"min": [], "max": [], "mean": [], "median": []}

    print(f"Card Counting GA — {POP_SIZE} individuals, {GENERATIONS} generations, "
          f"{HANDS_PER_EVAL} hands/eval, {NUM_DECKS}-deck shoe")
    print("-" * 72)

    for gen in range(GENERATIONS):
        fitnesses = np.array([
            evaluate_fitness(population[i], HANDS_PER_EVAL, rng)
            for i in range(POP_SIZE)
        ])

        history["min"].append(fitnesses.min())
        history["max"].append(fitnesses.max())
        history["mean"].append(fitnesses.mean())
        history["median"].append(np.median(fitnesses))

        print(f"Gen {gen:3d} | Min: ${fitnesses.min():8.2f}  "
              f"Mean: ${fitnesses.mean():8.2f}  "
              f"Median: ${np.median(fitnesses):8.2f}  "
              f"Max: ${fitnesses.max():8.2f}")

        if gen < GENERATIONS - 1:
            population = evolve_one_generation(population, fitnesses, rng)

    print("-" * 72)
    best_idx = int(np.argmax(fitnesses))
    best = population[best_idx]
    print(f"Best final bankroll: ${fitnesses[best_idx]:.2f}")

    # Console tables
    print_count_table(best)
    print_bet_table(best)

    # Plots (saved to same directory as this script)
    plot_fitness(history,       filename=os.path.join(out_dir, "fitness_plot.png"))
    plot_strategy_heatmap(population, filename=os.path.join(out_dir, "strategy_heatmap.png"))
    plot_count_comparison(best, filename=os.path.join(out_dir, "count_values.png"))
    plot_bankroll_history(best, rng, filename=os.path.join(out_dir, "bankroll_history.png"))


if __name__ == "__main__":
    main()
