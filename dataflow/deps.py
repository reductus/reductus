# This program is public domain
# Author: Paul Kienzle
"""
Dependency calculator.
"""
from __future__ import print_function

def processing_order(pairs, n=0):
    """
    Order the work in a workflow.

    Given a set of n items to evaluate numbered from zero through n-1,
    and dependency pairs


    :Parameters:

    *pairs* : [(int, int), ...]

        Pairwise dependencies amongst items.

    *n* : int

        Number of items, or 0 if we don't care about any item that is not
        mentioned in the list of pairs

    :Returns:

    *order* : [int, ...]

        Permutation which satisfies the partial order requirements.

    """
    order = _dependencies(pairs)
    if n:
        if any(id >= n for id in order):
            raise ValueError("Not all dependencies are in the set")
        rest = set(range(n)) - set(order)
    else:
        rest = set(k for p in pairs for k in p) - set(order)
    #print "order",order,"from",pairs
    return order + list(rest)


def _dependencies(pairs):
    # type: (List[Tuple[int, int]]) -> List[int]
    emptyset = set()
    order = []  # type: List[int]
    pairs = [(a, b) for a, b in pairs]
    if not pairs:
        return order

    # Break pairs into left set and right set
    left, right = (set(s) for s in zip(*pairs))
    while pairs:
        #print "within",pairs
        # Find which items only occur on the right
        independent = right - left
        if independent == emptyset:
            cycleset = ", ".join(str(s) for s in left)
            raise ValueError("Cyclic dependencies amongst %s" % cycleset)

        # The possibly resolvable items are those that depend on the independents
        dependent = set(a for a, b in pairs if b in independent)
        pairs = [(a, b) for a, b in pairs if b not in independent]
        if not pairs:
            resolved = dependent
        else:
            left, right = (set(s) for s in zip(*pairs))
            resolved = dependent - left
        #print "independent",independent,"dependent",dependent,"resolvable",resolved
        order += resolved
        #print("new order",order)
    order.reverse()
    return order


# ========= Test code ========
def _check(msg, pairs, n):
    """
    Verify that the list n contains the given items, and that the list
    satisfies the partial ordering given by the pairs in partial order.
    """
    order = processing_order(pairs, n=n)
    if len(set(order)) != n:
        raise RuntimeError("%s is missing items" % msg)
    for lo, hi in pairs:
        if order.index(lo) >= order.index(hi):
            raise RuntimeError("%s expect %s before %s in %s for %s"
                               % (msg, lo, hi, order, pairs))
    print("%s %s"%(msg, str(order)))


def test():
    import numpy as np

    # No dependencies
    _check("test empty", [], 9)

    # No chain dependencies
    _check("test2", [(4, 1), (3, 2), (7, 6)], 9)

    # Some chain dependencies
    pairs = [(4, 0), (0, 1), (1, 2), (7, 0), (3, 5)]
    _check("test1", pairs, 9)
    _check("test1 numpy", np.array(pairs), 9)

    # Cycle test
    pairs = [(1, 4), (4, 3), (4, 5), (5, 1)]
    try:
        _ = processing_order(pairs, n=9)
    except ValueError:
        pass
    else:
        raise Exception("test3 expect ValueError exception for %s" % (pairs,))

    # large test for gross speed check
    A = np.random.randint(4000, size=(1000, 2))
    A[:, 1] += 4000  # Avoid cycles
    _check("test-large", A, 8000)

    # depth tests
    k = 200
    A = np.array([range(0, k), range(1, k + 1)]).T
    _check("depth-1", A, 201)

    A = np.array([range(1, k + 1), range(0, k)]).T
    _check("depth-2", A, 201)


if __name__ == "__main__":
    test()
