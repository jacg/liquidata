# TLDR: Write an implementation which passes this test in CONSTANT SPACE, while
# treating `min`, `max` and `sum` as black boxes.

def testit(implementation, N):
    from time import sleep

    def slowrange(t):
        def slowrange(N):
            for x in range(N):
                sleep(t)
                yield x
        return slowrange

    def slowmin(T):
        from sys import maxsize
        lo = maxsize
        def slowmin(iterable):
            nonlocal lo
            for item in iterable:
                sleep(T)
                if item < lo:
                    lo = item
            return lo
        return slowmin

    delay = 0.00000000001

    #assert implementation(range(N), max, sum, slowmin(delay)) == (N-1, N*(N-1)//2, 0)
    #assert implementation(slowrange(delay)(N), min, max, sum) == (0, N-1, N*(N-1)//2)
    assert implementation(range(N), min, max, sum) == (0, N-1, N*(N-1)//2)

# Discussion

# We love iterators because they allow us to process streams of data lazily,
# allowing the processing of huge amounts of data in CONSTANT SPACE.

def source_summary(source, summary):
    return summary(source)

N = 1 #10 ** 8
print(source_summary(range(N), min))
print(source_summary(range(N), max))
print(source_summary(range(N), sum))

# Each line took a few seconds to execute, but used very little memory.
# However, It did require 3 separate traversals of the source. So this will not
# work if your source is a network connection, data acquisition hardware, etc.

# Here's a version which does it in a single traversal ...

def source_summaries_TEE(source, *summaries):
    from itertools import tee
    #return tuple(summary(source) for (source, summary) in zip(tee(source, len(summaries)), summaries))
    return tuple(map(source_summary, tee(source, len(summaries)),
                                     summaries))

class safeteeobject(object):
    """tee object wrapped to make it thread-safe"""
    def __init__(self, teeobj, lock):
        self.teeobj = teeobj
        self.lock = lock
    def __iter__(self):
        return self
    def __next__(self):
        with self.lock:
            return next(self.teeobj)
    def __copy__(self):
        return safeteeobject(self.teeobj.__copy__(), self.lock)

def safetee(iterable, n=2):
    """tuple of n independent thread-safe iterators"""
    from threading import Lock
    from itertools import tee
    lock = Lock()
    return tuple(safeteeobject(teeobj, lock) for teeobj in tee(iterable, n))

def source_summaries_SAFE_TEE(source, *summaries):
    from itertools import tee
    #return tuple(summary(source) for (source, summary) in zip(safetee(source, len(summaries)), summaries))
    return tuple(map(source_summary, safetee(source, len(summaries)),
                                     summaries))


from time import time
start = time()
testit(source_summaries_TEE, N)
stop = time()
print(f'OK: {N} in {stop - start}')
# ... but the space usage goes up from `O(1)` to `O(N)`.

# How can you obtain the results in a single traversal with constant memory?

# It is, of course, possible to pass the test given at the top by cheating,
# using knowledge of the specific iterator-consumers that the test uses. But
# that is not the point: `source_summaries` should work with *any* iterator
# consumables such as `set`, `collections.Counter`, `''.join`, including any
# and all that may be written in the future. The implementation must treat them
# as black boxes.


def make_thread(link, consumer, future):
    from threading import Thread
    return Thread(target = lambda: on_thread(link, consumer, future))

def on_thread(source_tee, consumer, future):
    future.set_result(consumer(source_tee))

def source_summaries_TEE_ON_THREAD(source, *consumers):
    from asyncio   import Future
    from itertools import tee

    futures = tuple(Future() for _ in consumers)
    sources = tee(source, len(consumers))
    sources = safetee(source, len(consumers))
    threads = tuple(map(make_thread, sources, consumers, futures))

    for thread in threads: thread.start()
    for thread in threads: thread.join()

    return tuple(map(Future.result, futures))
    return tuple(f.result() for f in futures)

def time(thunk):
    from time import time
    start = time()
    thunk()
    stop  = time()
    return stop - start

######################################################################
def source_summaries_FOLD(source, *consumers):

    from sys import maxsize
    from operator import add

    fn   = { min: min,     max:  max    , sum: add}
    init = { min: maxsize, max: -maxsize, sum: 0}

    accumulator =  list(map(init.get, consumers))
    fn          = tuple(map(fn  .get, consumers))

    for item in source:
        for i in range(len(consumers)):
            accumulator[i] = fn[i](accumulator[i], item)
    return tuple(accumulator)
######################################################################

N = 10 ** 5

t = time(lambda: testit(source_summaries_TEE_ON_THREAD, N))
print(f'teeTHR: {N} in {t:5.1f} s')

t = time(lambda: testit(source_summaries_TEE, N))
print(f'tee   : {N} in {t:5.1f} s')

# t = time(lambda: testit(source_summaries_PREEMPTIVE_THREAD, N))
# print(f'thread: {N} in {t:5.1f} s')

# t = time(lambda: testit(source_summaries_FOLD, N))
# print(f'fold  : {N} in {t:5.1f} s')



def testitR(implementation, N):
    consumers = known_consumers
    assert implementation(range(N), *consumers) == tuple(c(range(N)) for c in consumers)

def testit(implementation, N):
    assert implementation(range(N), min, max, sum) == (0, N-1, N*(N-1)//2)

def Bobs_classify(iterable):
    small = medium = big = 0
    for item in iterable:
        if   item <  10: small  += 1
        elif item < 100: medium += 1
        else           : big    += 1
    return small, medium, big

def exceeds_10(iterable):
    for item in iterable:
        if item > 10:
            return True
    return False


# from collections import Counter
# known_consumers = [tuple, list, set, dict, sorted, min, max, sum, ','.join, Counter, enumerate, lambda x: map(lambda x:x+1, x)]
# known_consumers = [exceeds_10, sum, min, max, tuple, list, set, Counter, Bobs_classify, exceeds_10]
# testitR(source_summaries_PREEMPTIVE_THREAD, 1000)
# print('OK')
