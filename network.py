class network:

    def __init__(self):
        self._src = None
        self._ret = None
        #self._dag = DAG()
        self._bound_variables = {}
        self._unbound_variables = {'IN', 'OUT'}

    def __call__(self):
        raise NetworkIncomplete(self._unbound_variables)

    def add_source(self, iterable):
        # TODO: this should create a new instance rather than mutating the old
        # one. Instances should be persistent.
        self._src = iterable
        self._unbound_variables.discard('IN')

    def add_sink(self, unary_function):
        # TODO: this should create a new instance rather than mutating the old
        # one. Instances should be persistent.
        self._sink = unary_function
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
