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

        # Check source and sink
        self.error_if_source_or_sink_missing(pipe_after_slot_filling)

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
    def error_if_source_or_sink_missing(pipe):
        if not pipe:
            raise NetworkIncomplete(pipe)
        first, last = pipe[0], pipe[-1]
        if not (isinstance(first,  source          ) and
                isinstance(last , (sink, output)  )):
            raise NetworkIncomplete(pipe)

    @staticmethod
    def compile_one(piece):
        if isinstance(piece, (source, sink)): # TODO: branch, ...
            return piece.compile()
        # Assume it's a callable which should be mapped
        return make_map(piece)


    def set_variables(self, **kwargs):
        # TODO: this should create a new instance rather than mutating the old
        # one. Instances should be persistent.
        for name, value in kwargs.items():
            self.  _bound_variables        [name] = value
            self._unbound_variables.discard(name)

    def set_IN_if_source_at_front(self):
        # Set IN variable if source present
        if self._pipe:
            first = self._pipe[0]
            if isinstance(first, source):
                self.set_variables(IN=first._source)

    def set_OUT_if_sink_at_end(self):
        if self._pipe:
            last = self._pipe[-1]
            if isinstance(last, sink):
                self.set_variables(OUT=last)

class component:

    @staticmethod
    def dispatch_make_coroutine(it):
        if isinstance(it, component):
            return it.make_coroutine()

        # If it's not an instance of component, then make implicit conversions
        # for certain types that play special roles. TODO: move these
        # conversions to network construction time.

        # TODO: set -> filter
        # TODO: tuple -> sink
        # TODO: list -> branch

        # Otherwise we assume it's a callable and use it to map
        return make_map(it)


class source:

    def __init__(self, iterable):
        self._source = iterable
src = source


class sink(component):

    coroutine_factory = None

    def __init__(self, binary_function):
        self._fn = binary_function

    def accept_future(self, future):
        return sink_and_future(self.coroutine_factory(self._fn)(future))


class sink_and_future(sink):

    def __init__(self, the_coroutine):
        self.the_coroutine = the_coroutine

    def make_coroutine(self):
        return self.the_coroutine


class fold(sink):

    coroutine_factory = 'bound to reduce_factory after its definition'


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

    def __call__(self, worker):
        self.worker = worker
        return self


class NetworkIncomplete(Exception):
    pass

    # def __init__(self, unbound_variables):
    #     sorted_unset_variables = ' '.join(sorted(unbound_variables, key=_variable_sort_key))
    #     msg = f'Network cannot run because the following variables are not set: {sorted_unset_variables}'
    #     if 'IN'  in unbound_variables: msg += "\nSet IN  by providing a source."
    #     if 'OUT' in unbound_variables: msg += "\nSet OUT by providing a sink."

    #     super().__init__(msg)
    #     self.unbound_variables = unbound_variables


def _variable_sort_key(name):
    if name == "IN" : return (0,)
    if name == "OUT": return (1,)
    return tuple(map(ord, name))


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
    for item in the_source._source:
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
        try:
            while True:
                accumulator = binary_function(accumulator, (yield))
        finally:
            future.set_result(accumulator)
    return reduce_loop

fold.coroutine_factory = staticmethod(reduce_factory)
