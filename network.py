from collections import namedtuple
from functools   import wraps, reduce
from contextlib  import contextmanager
from asyncio     import Future
from argparse    import Namespace

class network:

    def __init__(self, *components):
        self._pipe = components

    def __call__(self, **kwargs):

        # Fill and check slots
        pipe_after_slot_filling, slots_still_empty = self.fill_slots(**kwargs)
        if slots_still_empty:
            self.raise_unfilled_slots(slots_still_empty)

        # Network validity checks
        self.error_if_sink_missing  (pipe_after_slot_filling)
        self.error_if_source_missing(pipe_after_slot_filling)

        # Extract outputs
        (the_source, *pipe_without_outputs), outputs = self.extract_outputs(pipe_after_slot_filling)

        # Turn components into coroutines
        coroutines = tuple(map(component.dispatch_make_coroutine, pipe_without_outputs))
        the_big_coroutine = combine_coroutines(coroutines)
        push_data_into_coroutine(the_source, the_big_coroutine)
        return Namespace(**{name: future.result() for name, future in outputs})

    @staticmethod
    def extract_outputs(pipe):
        outputs = []
        new_pipe = []

        for item in pipe:

            if isinstance(item, output):
                the_output = item
                future = Future()
                outputs .append((the_output.name  ,              future))
                new_pipe.append( the_output.worker.accept_future(future))
                continue

            # TODO: need to do it recursively for branches

            # Nothing else can contain outputs, so put it in the pipe without further ado
            new_pipe.append(item)

        return tuple(new_pipe), tuple(outputs)

    def fill_slots(self, **slot_values):
        updated_pipe = []
        slots_still_empty = []

        for component in self._pipe:

            # Set slot's value if available; otherwise record it as unfilled
            if isinstance(component, slot):
                the_slot = component
                if the_slot.name in slot_values:
                    updated_pipe.append(slot_values[the_slot.name])
                else:
                    updated_pipe.append(the_slot)
                continue

            # # Branch: fill those slots for which values available; record others as unfilled
            # if isinstance(component, branch):
            #     updated, unfilled = component.fill_slots(**slot_values)
            #     updated_pipe  .append(updated)
            #     slots_still_empty.extend(unfilled)
            #     continue

            # Nothing else can contain slots, so put it in pipe without further ado
            updated_pipe.append(component)

        return tuple(updated_pipe), tuple(slots_still_empty)

    @staticmethod
    def error_if_sink_missing(pipe):
        if not pipe:
            raise NetworkIncomplete(pipe)
        if not isinstance(pipe[-1], (sink, output)):
            raise NoSinkAtEndOfPipe(pipe)

    @staticmethod
    def error_if_source_missing(pipe):
        try:
            iter(pipe[0])
        except TypeError:
            raise NoSourceAtFrontOfPipe(pipe)


class component:

    @staticmethod
    def dispatch_make_coroutine(it):
        if isinstance(it, component):
            return it.make_coroutine()

        # If it's not an instance of component, then make implicit conversions
        # for certain types that play special roles. TODO: move these
        # conversions to network construction time.

        # TODO: list -> branch
        # TODO: tuple -> sink  ('out' makes this work partially)

        if isinstance(it, set):
            return  make_filter(next(iter(it)))

        # Otherwise we assume it's a callable and use it to map
        return make_map(it)


class source:

    def __init__(self, iterable):
        self._source = iterable
src = source


class sink(component):

    coroutine_factory = None

    def __init__(self, binary_function, **kwds):
        self._fn = binary_function
        self._kwds = kwds # so far only used to provide 'initial=' to fold

    def accept_future(self, future):
        coroutine_factory = self.coroutine_factory(self._fn, **self._kwds)
        return sink_and_future(coroutine_factory(future))


class sink_and_future(sink):

    def __init__(self, the_coroutine):
        self.the_coroutine = the_coroutine

    def make_coroutine(self):
        return self.the_coroutine


class fold(sink):

    coroutine_factory = 'bound to reduce_factory after its definition below'


class Get:

    def __getattribute__(self, name):
        return slot(name)
get = Get()


class slot:

    def __init__(self, name):
        self.name = name

class Out:

    def __getattribute__(self, name):
        return output(name)
out = Out()

class output(component):

    def __init__(self, name):
        self.name = name

    def __call__(self, worker, initial=None):
        if isinstance(worker, sink):
            self.worker = worker
        else:
            self.worker = fold(worker, initial=initial)
        return self


class NetworkIncomplete(Exception):
    pass

class NoSourceAtFrontOfPipe(NetworkIncomplete):
    pass

class NoSinkAtEndOfPipe(NetworkIncomplete):
    pass

@contextmanager
def closing(target):
    try:     yield
    finally: target.close()


def make_map(op):
    def map_loop(target):
            with closing(target):
                while True:
                    target.send(op((yield)))
    return coroutine(map_loop)


def make_filter(predicate):
    def filter_loop(target):
        with closing(target):
            while True:
                val = yield
                if predicate(val):
                    target.send(val)
    return coroutine(filter_loop)


def side_effect_sink(unary_function):
    def sink_loop():
        while True:
            unary_function((yield))
    return coroutine(sink_loop)()


def coroutine(generator_function):
    @wraps(generator_function)
    def proxy(*args, **kwds):
        coroutine = generator_function(*args, **kwds)
        next(coroutine)
        return coroutine
    return proxy


def absorb(absorbing_side_effect_unary_function):
    @coroutine_with_future
    def reduce_loop(future):
        try:
            while True:
                last_result = absorbing_side_effect_unary_function((yield))
        finally:
            future.set_result(last_result)
    return reduce_loop


def combine_coroutines(coroutines):
    if not hasattr(coroutines[-1], 'close'):
        raise Exception(f'No sink at end of {coroutines}')
    def apply(arg, fn):
        return fn(arg)
    return reduce(apply, reversed(coroutines))


def push_data_into_coroutine(the_source, coroutine):
    for item in the_source:
        coroutine.send(item)
    coroutine.close()

# def reduce(binary_function, initial):
#     @coroutine_with_future
#     def reduce_loop(future):
#         accumulator = copy.copy(initial)
#         try:
#             while True:
#                 accumulator = binary_function(accumulator, (yield))
#         finally:
#             future.set_result(accumulator)
#     return reduce_loop


def reduce_factory(binary_function, initial=None):
    @coroutine
    def reduce_loop(future):
        if initial is None:
            try:
                accumulator = (yield)
            except StopIteration:
                # TODO: message about not being able to run on an empty stream.
                # Try to link it to variable names in the network?
                pass
        else:
            accumulator = initial
        try:
            while True:
                accumulator = binary_function(accumulator, (yield))
        finally:
            future.set_result(accumulator)
    return reduce_loop

fold.coroutine_factory = staticmethod(reduce_factory)
