# TLDR: Write an implementation which passes this test in CONSTANT SPACE, while
# treating `min`, `max` and `sum` as black boxes.

def testit(implementation, N):
    assert implementation(RANGE(N), MIN, max, sum) == (0, N-1, N*(N-1)//2)

# Slowed down versions of range and min, simulating sources and consumers which
# take non-trivial time. The CLI provides options for using these instead of
# the real range and max in the timings.
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

# Timing utility
def time(thunk):
    from time import time
    start = time()
    thunk()
    stop  = time()
    return stop - start

# ========= Aside: Deal with CLI arguments =====================================
from sys import argv
usage_message = f"""
ERROR: problem on the command line.
Try one of:
{argv[0]} 100000
{argv[0]} 1000 --slowrange 0.0001
{argv[0]} 1000 --slowmin   0.0001
"""

if len(argv) not in (2, 4): raise SystemExit(usage_message)
N = int(argv[1])

# Default values, may be overridden on CLI using --slowrange or --slowmin
RANGE, MIN = range, min

if len(argv) == 4:
    slow, delay = argv[2:4]
    if slow not in '--slowrange --slowmin'.split():
        raise SystemExit(f'Unknown option: {slow}' + usage_message)
    try:
        delay = float(delay)
    except ValueError:
        raise SystemExit(f'Delay must parse to float but got: {delay}')
    if slow == '--slowrange': RANGE = slowrange(delay)
    if slow == '--slowmin'  : MIN   = slowmin  (delay)

# ====================== Discussion =============================================

# We love iterators because they allow us to process streams of data lazily,
# allowing the processing of huge amounts of data in CONSTANT SPACE:

def source_summary(source, summary):
    return summary(source)

from time import time as tick
start = tick()
source_summary(RANGE(N), MIN)
source_summary(RANGE(N), max)
source_summary(RANGE(N), sum)
stop = tick()
print(f'3 traversals: {N} in {stop - start:6.1f}')

# Each line took a few seconds to execute, but used very little memory.
# However, It did require 3 separate traversals of the source. So this will not
# work if your source is a network connection, data acquisition hardware, etc.

# Here's a version which does it in a single traversal ...

def source_summaries_TEE(source, *summaries):
    from itertools import tee
    #return tuple(summary(source) for (source, summary) in zip(tee(source, len(summaries)), summaries))
    return tuple(map(source_summary, tee(source, len(summaries)),
                                     summaries))

t = time(lambda: testit(source_summaries_TEE, N))
print(f'tee   : {N} in {t:5.1f} s')

# ... but the space usage goes up from `O(1)` to `O(N)`.

# How can you obtain the results in a single traversal with constant memory?

# It is, of course, possible to pass the test given at the top by cheating,
# using knowledge of the specific iterator-consumers that the test uses. But
# that is not the point: `source_summaries` should work with *any* iterator
# consumables such as `set`, `collections.Counter`, `''.join`, including any
# and all that may be written in the future. The implementation must treat them
# as black boxes.

class Link:

    def __init__(self, queue):
        self.queue = queue
        self.maxsize = 0
        self.count = 0
        self.maxwhen = 0

    def __iter__(self):
        return self

    def __next__(self):
        item = self.queue.get()
        if item is FINISHED:
            raise StopIteration
        return item

    def put(self, item):
        self.count += 1
        self.queue.put(item)
        size = self.queue.qsize()
        if size > self.maxsize:
            self.maxsize, self.maxwhen = size, self.count

    def stop(self):
        self.queue.put(FINISHED)
        #print(f'Queue space: {self.maxsize} ({self.maxsize / self.count} N)  after {self.maxwhen / self.count * 100:6.2f} % items')
        print(f'Maximum queue size {self.maxsize} after {self.maxwhen} out of {self.count} ({self.maxwhen / self.count * 100:5.2f} %)')

    def consumer_not_listening_any_more(self):
        self.__class__ = ClosedLink

class ClosedLink(Link):

    def put(self, _): pass
    #def stop(self)  : pass

class FINISHED: pass


def make_thread(link, consumer, future):
    from threading import Thread
    return Thread(target = lambda: on_thread(link, consumer, future))

def on_thread(link, consumer, future):
    future.set_result(consumer(link))
    link.consumer_not_listening_any_more()

def source_summaries_PREEMPTIVE_THREAD(source, *consumers):
    from queue     import SimpleQueue as Queue
    from asyncio   import Future

    links   = tuple(Link(Queue()) for _ in consumers)
    futures = tuple(     Future() for _ in consumers)
    threads = tuple(map(make_thread, links, consumers, futures))

    for thread in threads:
        thread.start()

    for item in source:
        for link in links:
            link.put(item)

    for link in links:
        link.stop()

    for t in threads:
        t.join()

    return tuple(f.result() for f in futures)

t = time(lambda: testit(source_summaries_PREEMPTIVE_THREAD, N))
print(f'thread: {N} in {t:5.1f} s')
######################################################################
def source_summaries_FOLD(source, *consumers):

    from sys import maxsize
    from operator import add

    fn   = { min: min,     max:  max    , sum: add}
    init = { min: maxsize, max: -maxsize, sum: 0}

    # accumulator =  list(map(init.get, consumers))
    # fn          = tuple(map(fn  .get, consumers))

    # Need special case to cater for slowmin
    accumulator =  list(init.get(c, maxsize) for c in consumers)
    fn          = tuple(fn  .get(c, min    ) for c in consumers)

    for item in source:
        for i in range(len(consumers)):
            accumulator[i] = fn[i](accumulator[i], item)
    return tuple(accumulator)

t = time(lambda: testit(source_summaries_FOLD, N))
print(f'fold  : {N} in {t:5.1f} s')
######################################################################


def testit_more_consumers(implementation, N):
    consumers = known_consumers
    assert implementation(range(N), *consumers) == tuple(c(range(N)) for c in consumers)

# def testit(implementation, N):
#     assert implementation(range(N), min, max, sum) == (0, N-1, N*(N-1)//2)

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


from collections import Counter
known_consumers = [tuple, list, set, dict, sorted, min, max, sum, ','.join, Counter, enumerate, lambda x: map(lambda x:x+1, x)]
known_consumers = [exceeds_10, sum, min, max, tuple, list, set, Counter, Bobs_classify, exceeds_10]
#t = time(lambda: testit               (source_summaries_PREEMPTIVE_THREAD, N))
#t = time(lambda: testit_more_consumers(source_summaries_PREEMPTIVE_THREAD, N))
#print(f'link  : {N} in {t:5.1f} s')
