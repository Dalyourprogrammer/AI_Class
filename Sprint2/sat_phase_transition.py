"""
3-CNF-SAT Phase Transition Experiment
"""

import random
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


if __name__ == '__main__':
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

    # --- Manual tests on small, known instances ---
    print("=== Manual tests ===")

    # Single clause, trivially SAT
    check("single clause [1,2,3]", [[1, 2, 3]], True)

    # x must be true AND x must be false -> UNSAT
    check("1-var contradiction", [[1, 1, 1], [-1, -1, -1]], False)

    # Two vars, all positive -> SAT (just set both true)
    check("all positive", [[1, 2, 1], [2, 1, 2]], True)

    # Forced chain: x1=T, x2=T, x3=T ... all consistent
    check("unit chain SAT", [[1, 1, 1], [2, 2, 2], [3, 3, 3]], True)

    # Forced values that conflict with a clause
    # x1=T, x2=T forced, but clause requires all false
    check("forced UNSAT", [[1, 1, 1], [2, 2, 2], [-1, -1, -2]], False)

    # Tautology clause (contains x and -x) is always SAT
    check("tautology clause", [[1, -1, 2]], True)

    # Empty formula -> trivially SAT
    check("empty formula", [], True)

    # --- Automated: compare solve() vs PySAT on random instances ---
    print("\n=== Random tests: solve() vs PySAT ===")
    n_tests = 100
    mismatches = 0
    for i in range(n_tests):
        # Small instances near the phase transition for a mix of SAT/UNSAT
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
