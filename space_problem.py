# TLDR: Write an implementation which passes this test in CONSTANT SPACE, while
# treating `min`, `max` and `sum` as black boxes.

def testit(implementation, N):
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

def source_summaries(source, *summaries):
    from itertools import tee
    return tuple(map(source_summary, tee(source, len(summaries)),
                                     summaries))

from time import time
start = time()
testit(source_summaries, N)
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

class Link:

    def __init__(self, queue):
        self.queue = queue

    def __iter__(self):
        return self

    def __next__(self):
        item = self.queue.get()
        if item is FINISHED:
            raise StopIteration
        return item

    def put(self, item):
        self.queue.put(item)

    def stop(self):
        self.queue.put(FINISHED)

    def consumer_not_listening_any_more(self):
        self.__class__ = ClosedLink

class ClosedLink:

    def put(self, _): pass
    def stop(self)  : pass

class FINISHED: pass


def make_thread(link, consumer, future):
    from threading import Thread
    return Thread(target = lambda: on_thread(link, consumer, future))

def on_thread(link, consumer, future):
    future.set_result(consumer(link))
    print(f'{consumer.__name__} DETACHING')
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

N = 10 ** 7
#print(source_summaries_PREEMPTIVE_THREAD(range(N), min, max, sum))

def time(thunk):
    from time import time
    start = time()
    thunk()
    stop  = time()
    return stop - start

N = 10 ** 7
t = time(lambda: testit(source_summaries, N))
print(f'old: {N} in {t:5.1f} s')

t = time(lambda: testit(source_summaries_PREEMPTIVE_THREAD, N))
print(f'new: {N} in {t:5.1f} s')


from collections import Counter
known_consumers = [tuple, list, set, dict, sorted, min, max, sum, ','.join, Counter, enumerate, lambda x: map(lambda x:x+1, x)]

from random import choices


def testitR(implementation, N):
    consumers = known_consumers #choices(known_consumers, k=3)
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

known_consumers = [sum, min, max, tuple, list, set, Counter, Bobs_classify, Janes_criterion]
testitR(source_summaries_PREEMPTIVE_THREAD, 1000)
print('OK')
