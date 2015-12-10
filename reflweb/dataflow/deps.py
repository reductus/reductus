# This program is public domain
# Author: Paul Kienzle
"""
Functions for manipulating dependencies.
"""

def processing_order(n, pairs):
    """
    Order the work in a workflow.

    Given a set of n items to evaluate numbered from zero through n-1,
    and dependency pairs 


    :Parameters:

    *n* : int

        Number of items

    *pairs* : [(int, int), ...]

        Pairwise dependencies amongst items.

    :Returns:

    *order* : [int, ...]

        Permutation which satisfies the partial order requirements.

    """
    order = _dependencies(pairs)
    if any(id >= n for id in order):
        raise ValueError("Not all dependencies are in the set")
    rest = set(range(n)) - set(order)
    #print "order",order,"from",pairs
    return order + list(rest)

def _dependencies(pairs):
    #print "order_dependencies",pairs
    emptyset = set()
    order = []

    # Break pairs into left set and right set
    left, right = [set(s) for s in zip(*pairs)] if pairs != [] else ([], [])
    while pairs != []:
        #print "within",pairs
        # Find which items only occur on the right
        independent = right - left
        if independent == emptyset:
            cycleset = ", ".join(str(s) for s in left)
            raise ValueError, "Cyclic dependencies amongst %s" % cycleset

        # The possibly resolvable items are those that depend on the independents
        dependent = set([a for a, b in pairs if b in independent])
        pairs = [(a, b) for a, b in pairs if b not in independent]
        if pairs == []:
            resolved = dependent
        else:
            left, right = [set(s) for s in zip(*pairs)]
            resolved = dependent - left
        #print "independent",independent,"dependent",dependent,"resolvable",resolved
        order += resolved
        #print "new order",order
    order.reverse()
    return order




# ========= Test code ========
def _check(msg, n, pairs):
    """
    Verify that the list n contains the given items, and that the list
    satisfies the partial ordering given by the pairs in partial order.
    """
    order = processing_order(n, pairs)
    if len(set(order)) != n:
        raise RuntimeError("%s is missing items" % msg)
    for lo, hi in pairs:
        if order.index(lo) >= order.index(hi):
            raise RuntimeError("%s expect %s before %s in %s for %s"
                               % (msg, lo, hi, order, pairs))
    print msg, order

def test():
    import numpy

    # No dependencies
    _check("test empty", 9, [])

    # No chain dependencies
    _check("test2", 9, [(4, 1), (3, 2), (7, 6)])

    # Some chain dependencies
    pairs = [(4, 0), (0, 1), (1, 2), (7, 0), (3, 5)]
    _check("test1", 9, pairs)
    _check("test1 numpy", 9, numpy.array(pairs))

    # Cycle test
    pairs = [(1, 4), (4, 3), (4, 5), (5, 1)]
    try: _ = processing_order(9, pairs)
    except ValueError: pass
    else: raise Exception, "test3 expect ValueError exception for %s" % (pairs,)

    # large test for gross speed check
    A = numpy.random.randint(4000, size=(1000, 2))
    A[:, 1] += 4000  # Avoid cycles
    _check("test-large", 8000, A)

    # depth tests
    k = 200
    A = numpy.array([range(0, k), range(1, k + 1)]).T
    _check("depth-1", 201, A)

    A = numpy.array([range(1, k + 1), range(0, k)]).T
    _check("depth-2", 201, A)

if __name__ == "__main__":
    test()
