from collections import namedtuple
from functools   import wraps
from asyncio     import Future

class network:

    def __init__(self):
        self._ret = 'OUT'
        #self._dag = DAG()
        self.  _bound_variables = {}
        self._unbound_variables = {'IN', 'OUT'}

    def __call__(self):
        if self._unbound_variables:
            raise NetworkIncomplete(self._unbound_variables)
        the_coroutine, future = self._bound_variables['OUT']()
        for item in self._bound_variables['IN']:
            the_coroutine.send(item)
        the_coroutine.close()
        return future.result()

    def add_source(self, iterable):
        # TODO: this should create a new instance rather than mutating the old
        # one. Instances should be persistent.
        self.  _bound_variables        ['IN'] = iterable
        self._unbound_variables.discard('IN')

    def add_reduce_wi_sink(self, binary_function):
        # TODO: this should create a new instance rather than mutating the old
        # one. Instances should be persistent.
        self.  _bound_variables        ['OUT'] = reduce_wi_factory(binary_function)
        self._unbound_variables.discard('OUT')




class NetworkIncomplete(Exception):

    def __init__(self, unbound_variables):
        sorted_unset_variables = ' '.join(sorted(unbound_variables, key=_variable_sort_key))
        msg = f'Network cannot run because the following variables are not set: {sorted_unset_variables}'
        if 'IN'  in unbound_variables: msg += "\nSet IN  by providing a source."
        if 'OUT' in unbound_variables: msg += "\nSet OUT by providing a sink."

        super().__init__(msg)
        self.unbound_variables = unbound_variables


def _variable_sort_key(name):
    if name == "IN" : return (0,)
    if name == "OUT": return (1,)
    return tuple(map(ord, name))




def sink(unary_function):
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


def coroutine_with_future(generator_function):
    @wraps(generator_function)
    def proxy(*args, **kwds):
        future = Future()
        coroutine = generator_function(future, *args, **kwds)
        next(coroutine)
        return CoroutineWithFuture(coroutine, future)
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


def reduce_wi_factory(binary_function):
    @coroutine_with_future
    def reduce_loop(future):
        try:
            accumulator = (yield)
        except StopIteration:
            # TODO: message about not being able to run on an empty stream. Try
            # to link it to variable names in the network?
            pass
        try:
            while True:
                accumulator = binary_function(accumulator, (yield))
        finally:
            future.set_result(accumulator)
    return reduce_loop


CoroutineWithFuture = namedtuple('CoroutineWithFuture', 'coroutine future')
