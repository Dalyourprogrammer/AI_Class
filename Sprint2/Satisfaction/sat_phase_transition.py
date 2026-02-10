"""
3-CNF-SAT Phase Transition Experiment
"""

import random
import time
import matplotlib.pyplot as plt
from pysat.solvers import Solver


def generate(n, m):
    """
    Generate a random 3-CNF formula.

    Args:
        n: Number of Boolean variables (1 to n)
        m: Clause-to-variable ratio (number of clauses = int(n * m))

    Returns:
        List of clauses in DIMACS format for PySAT.
        Each clause is a list of 3 literals (ints from -n..-1, 1..n).
    """
    n_clauses = int(n * m)
    # Pool of all possible literals: -n,...,-1, 1,...,n
    literals = list(range(-n, 0)) + list(range(1, n + 1))

    clauses = []
    for _ in range(n_clauses):
        # Pick 3 literals with replacement
        clause = random.choices(literals, k=3)
        clauses.append(clause)

    return clauses


def solve(clauses):
    """
    Determine if a 3-CNF formula is satisfiable using DPLL
    (backtracking with unit propagation).

    Args:
        clauses: List of clauses in DIMACS format (list of lists of ints)

    Returns:
        True if satisfiable, False otherwise.
    """
    # Collect all variables
    variables = set()
    for clause in clauses:
        for lit in clause:
            variables.add(abs(lit))

    def is_true(lit, assignment):
        """Check if a literal is true under the current assignment."""
        var = abs(lit)
        if var not in assignment:
            return None  # unassigned
        return assignment[var] if lit > 0 else not assignment[var]

    def dpll(assignment):
        # --- Unit propagation ---
        changed = True
        while changed:
            changed = False
            for clause in clauses:
                unassigned_lits = []
                satisfied = False
                for lit in clause:
                    val = is_true(lit, assignment)
                    if val is True:
                        satisfied = True
                        break
                    elif val is None:
                        unassigned_lits.append(lit)
                if satisfied:
                    continue
                if len(unassigned_lits) == 0:
                    return False  # conflict: all literals false
                if len(unassigned_lits) == 1:
                    # Unit clause: forced assignment
                    lit = unassigned_lits[0]
                    assignment[abs(lit)] = (lit > 0)
                    changed = True

        # --- Check status and find branching variable ---
        branch_var = None
        for clause in clauses:
            satisfied = False
            for lit in clause:
                val = is_true(lit, assignment)
                if val is True:
                    satisfied = True
                    break
                elif val is None and branch_var is None:
                    branch_var = abs(lit)
            if not satisfied and branch_var is None:
                return False  # unsatisfied clause, no vars left

        if branch_var is None:
            return True  # all clauses satisfied

        # --- Branch ---
        for value in [True, False]:
            new_assignment = assignment.copy()
            new_assignment[branch_var] = value
            if dpll(new_assignment):
                return True

        return False

    return dpll({})


def pysat_solve(clauses):
    """Reference solver using PySAT for testing."""
    solver = Solver(name='g3')
    for clause in clauses:
        solver.add_clause(clause)
    result = solver.solve()
    solver.delete()
    return result


def experiment(n_values, m_range, trials, use_pysat=False):
    """
    Run the phase-transition experiment.

    For each n in n_values and each m in m_range, generate `trials` random
    3-CNF formulas and solve them. Record the fraction satisfiable and the
    average solve time.

    Args:
        n_values:  List of variable counts to test.
        m_range:   List/array of clause-to-variable ratios.
        trials:    Number of random instances per (n, m) pair.
        use_pysat: If True, use PySAT solver instead of the custom DPLL.

    Returns:
        dict mapping each n to {
            "m_values": list of m,
            "sat_fracs": list of fraction satisfiable,
            "avg_times": list of average solve time (seconds)
        }
    """
    solver_fn = pysat_solve if use_pysat else solve
    solver_name = "PySAT" if use_pysat else "DPLL"
    results = {}

    for n in n_values:
        sat_fracs = []
        avg_times = []

        print(f"\n--- n = {n} ({solver_name}) ---")
        print(f"{'m':>6}  {'%SAT':>6}  {'avg time (s)':>12}")
        print("-" * 28)

        for m in m_range:
            sat_count = 0
            total_time = 0.0

            for _ in range(trials):
                formula = generate(n, m)
                t0 = time.time()
                result = solver_fn(formula)
                total_time += time.time() - t0
                if result:
                    sat_count += 1

            frac = sat_count / trials
            avg_t = total_time / trials
            sat_fracs.append(frac)
            avg_times.append(avg_t)
            print(f"{m:6.2f}  {frac:6.2%}  {avg_t:12.6f}")

        results[n] = {
            "m_values": list(m_range),
            "sat_fracs": sat_fracs,
            "avg_times": avg_times,
        }

    return results


def plot_results(results, filename="sat_phase_transition.png"):
    """
    Plot fraction satisfiable and average solve time vs m for each n.

    Args:
        results:  Output from experiment().
        filename: Where to save the figure.
    """
    _fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    for n, data in sorted(results.items()):
        ms = data["m_values"]
        ax1.plot(ms, data["sat_fracs"], marker="o", markersize=3, label=f"n={n}")
        ax2.plot(ms, data["avg_times"], marker="o", markersize=3, label=f"n={n}")

    # Theoretical threshold line
    ax1.axvline(x=4.26, color="red", linestyle="--", alpha=0.7, label="m ≈ 4.26")
    ax2.axvline(x=4.26, color="red", linestyle="--", alpha=0.7, label="m ≈ 4.26")

    tick_positions = [x * 0.5 for x in range(2, 17)]  # 1.0, 1.5, ..., 8.0
    ax1.set_xticks(tick_positions)
    ax1.set_xlabel("Clause-to-variable ratio (m)")
    ax1.set_ylabel("Fraction satisfiable")
    ax1.set_title("SAT Phase Transition")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2.set_xticks(tick_positions)
    ax2.set_xlabel("Clause-to-variable ratio (m)")
    ax2.set_ylabel("Average solve time (s)")
    ax2.set_title("Solver Hardness (Computational Cost)")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    print(f"\nPlot saved to {filename}")
    plt.show()


if __name__ == '__main__':
    # ------------------------------------------------------------------
    # Unit tests (existing)
    # ------------------------------------------------------------------
    passed = 0
    failed = 0

    def check(name, clauses, expected):
        global passed, failed
        result = solve(clauses)
        status = "PASS" if result == expected else "FAIL"
        if status == "FAIL":
            failed += 1
        else:
            passed += 1
        print(f"  {status}: {name} -> {result} (expected {expected})")

    print("=== Manual tests ===")
    check("single clause [1,2,3]", [[1, 2, 3]], True)
    check("1-var contradiction", [[1, 1, 1], [-1, -1, -1]], False)
    check("all positive", [[1, 2, 1], [2, 1, 2]], True)
    check("unit chain SAT", [[1, 1, 1], [2, 2, 2], [3, 3, 3]], True)
    check("forced UNSAT", [[1, 1, 1], [2, 2, 2], [-1, -1, -2]], False)
    check("tautology clause", [[1, -1, 2]], True)
    check("empty formula", [], True)

    print("\n=== Random tests: solve() vs PySAT ===")
    n_tests = 100
    mismatches = 0
    for i in range(n_tests):
        n = 10
        m = random.uniform(2.0, 8.0)
        formula = generate(n, m)
        ours = solve(formula)
        ref = pysat_solve(formula)
        if ours != ref:
            mismatches += 1
            failed += 1
            print(f"  MISMATCH test {i}: n={n}, m={m:.2f}, solve={ours}, pysat={ref}")
        else:
            passed += 1
    print(f"  {n_tests - mismatches}/{n_tests} random tests matched PySAT")
    print(f"\n=== Summary: {passed} passed, {failed} failed ===")

    # Sweep m from 1.0 to 8.0 in steps of 0.5
    m_range = [round(1.0 + 0.5 * i, 2) for i in range(15)]  # 1.0, 1.5, ..., 8.0
    trials = 25

    # ------------------------------------------------------------------
    # Phase-transition experiment: n = 10, 25, 50
    # ------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("  PHASE-TRANSITION EXPERIMENT (n = 10, 25, 50)")
    print("=" * 50)

    n_values_small = [10, 25, 50]
    results_small = experiment(n_values_small, m_range, trials)
    plot_results(results_small)

    # ------------------------------------------------------------------
    # Phase-transition experiment: n = 50, 75, 100
    # ------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("  PHASE-TRANSITION EXPERIMENT (n = 50, 75, 100)")
    print("=" * 50)

    n_values_large = [50, 75, 100]
    results_large = experiment(n_values_large, m_range, trials)
    plot_results(results_large, filename="sat_phase_transition_precise.png")
