# $Id: contexts.py 081917d30609 2010-03-05 mtnyogi $
# coding=utf-8
# 
# Copyright © 2007-2008 Bruce Frederiksen
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
    A context is used to store all of a rule's pattern variable bindings for a
    specific rule invocation during inferencing (both forward-chaining and
    backward-chaining rules).

        >>> from pyke import pattern
        >>> c = simple_context()
        >>> var = variable('foo')
        >>> var
        $foo
        >>> var.name
        'foo'
        >>> c.bind(var.name, c, 123)
        True
        >>> c.lookup(var)
        (123, None)
        >>> c.lookup_data(var.name)
        123
    
    This is a shallow binding scheme which must "unbind" variables when a
    rule is done.  Each time a rule is invoked, a new context object is
    created to store the bindings for the variables in that rule.  When the
    rule is done, this context is abandoned; so the variables bound there
    do not need to be individually unbound.  But bindings done to
    variables in other contexts _do_ need to be individually unbound.
    These bindings happen when a variable in the calling rule, which must
    be bound in that rule's context, is matched to a non-variable pattern (i.e.,
    pattern_literal or pattern_tuple) in the called rule's context.

    For example, a caller, rule A, has its own context:

        >>> A_context = simple_context()

    and a pattern of $foo within a subgoal in its 'when' clause:

        >>> A_pattern = variable('foo')

    In proving this subgoal, rule B is being tried.  A new context is
    created for rule B:

        >>> B_context = simple_context()

    Rule B has a literal 123 in its 'proven' clause:

        >>> B_pattern = pattern.pattern_literal(123)

    Now B's 'proven' clause is pattern matched to A's subgoal, which
    results in:

        >>> B_pattern.match_pattern(B_context, B_context, A_pattern, A_context)
        True

    The pattern matches!  But the $foo variable belongs to A, so it must be
    bound in A's context, not B's.

        >>> A_context.lookup(A_pattern)
        (123, None)
        >>> B_context.lookup(A_pattern)
        Traceback (most recent call last):
            ...
        KeyError: '$foo not bound'

    This is done by using the current rule's context as a controlling context
    for all the bindings that occur within that rule.  If the binding is for
    a variable in another context, the controlling context remembers the
    binding in its undo_list.  When the rule is finished, it executes a 'done'
    method on its context which undoes all of the bindings in its undo_list.

        >>> B_context.done()
        >>> A_context.lookup(A_pattern)
        Traceback (most recent call last):
            ...
        KeyError: '$foo not bound'

    Thus, in binding a variable to a value, there are three contexts
    involved:

        controlling_context.bind(variable, variable_context,
                                 value [, value_context])

    The value_context must be omitted if value is any python data, and
    must be included if value is a pattern (including another variable).

    Variables are bound to as just strings so that they can be accessed
    easily from python code without needing the variable objects.

        >>> A_context.bind('foo', A_context, 123)
        True
        >>> A_context.lookup_data('foo')
        123
    
    But to differentiate variables from string literals in the patterns,
    variables are special objects.  When a variable is bound as data (to
    another variable), it is bound as a variable object (again, to
    differentiate it from plain python strings).

        >>> a_var = variable('a_var')
        >>> a_var
        $a_var
        >>> b_var = variable('b_var')
        >>> b_var
        $b_var
        >>> B_context.bind(b_var.name, B_context, a_var, A_context)
        True
        >>> B_context.lookup(b_var)
        Traceback (most recent call last):
            ...
        KeyError: '$a_var not bound'
        >>> ans = B_context.lookup(b_var, True)
        >>> ans                                 # doctest: +ELLIPSIS
        ($a_var, <pyke.contexts.simple_context object at ...>)
        >>> ans[1] is A_context
        True
    
    But to differentiate variables from string literals in the patterns,
    variables are special objects.  When a variable is bound as data (to
    another variable), it is bound as a variable object (again, to
    differentiate it from plain python strings).

        >>> type(ans[0])
        <class 'pyke.contexts.variable'>

    The anonymous variables have names starting with '_'.  Binding
    requests on anonymous variables are silently ignored.

        >>> anonymous('_ignored')
        $_ignored
        >>> A_context.bind('_bogus', A_context, 567)
        False
        >>> A_context.lookup_data('_bogus')
        Traceback (most recent call last):
            ...
        KeyError: '$_bogus not bound'
        >>> A_context.lookup_data('_bogus', True)
        '$_bogus'
"""

import sys

from pyke import pattern, unique

_Not_found = unique.unique('Not_found')

# Set to a sequence (or frozenset) of variable names to trace their bindings:
debug = ()

class simple_context(object):
    def __init__(self):
        self.bindings = {}
        self.undo_list = []
        self.save_all_undo_count = 0

    def dump(self):
        for var_name in sorted(self.bindings.keys()):
            print("%s: %s" % (var_name, repr(self.lookup_data(var_name, True))))

    def bind(self, var_name, var_context, val, val_context = None):
        """ val_context must be None iff val is not a pattern.
            Returns True if a new binding was created.
        """
        assert not isinstance(val, pattern.pattern) \
                   if val_context is None \
                   else isinstance(val, pattern.pattern)
        if var_name[0] == '_': return False
        if var_context is self:
            assert var_name not in self.bindings
            if val_context is not None:
                val, val_context = val_context.lookup(val, True)
            if val_context == var_context and isinstance(val, variable) and \
               val.name == var_name:
                # binding $x to $x; no binding necessary!
                return False
            if var_name in debug:
                if val_context:
                    sys.stderr.write("binding %s in %s to %s in %s\n" %
                        (var_name, var_context, val, val_context))
                else:
                    sys.stderr.write("binding %s in %s to %s\n" %
                        (var_name, var_context, val))
            self.bindings[var_name] = (val, val_context)
            if self.save_all_undo_count:
                self.undo_list.append((var_name, self))
            return True
        ans = var_context.bind(var_name, var_context, val, val_context)
        if ans: self.undo_list.append((var_name, var_context))
        return ans

    def is_bound(self, var):
        val, where = var, self
        while where is not None and isinstance(val, variable):
            ans = where.bindings.get(val.name)
            if ans is None: return False
            val, where = ans
        # where is None or not isinstance(val, variable)
        return where is None or val.is_data(where)

    def lookup_data(self, var_name, allow_vars = False, final = None):
        """ Converts the answer into data only (without any patterns in it).
            If there are unbound variables anywhere in the data, a KeyError is
            generated.
        """
        if final is not None:
            val = final.get((var_name, self), _Not_found)
            if val is not _Not_found: return val
        binding = self.bindings.get(var_name)
        if binding is None:
            if allow_vars: return "$" + var_name
            raise KeyError("$%s not bound" % var_name)
        val, context = binding
        if context is not None:
            val = val.as_data(context, allow_vars, final)
        if isinstance(val, bc_context): val = val.create_plan(final)
        if final is not None: final[var_name, self] = val
        return val

    def lookup(self, var, allow_variable_in_ans = False):
        """ Returns value, val_context.
            Returns (var, self) if not bound and allow_variable_in_ans, else
            raises KeyError.
        """
        val, where = var, self
        while where is not None and isinstance(val, variable):
            ans = where.bindings.get(val.name)
            if ans is None: break
            val, where = ans
        else:
            # where is None or not isinstance(val, variable)
            return val, where
        # where is not None and isinstance(val, variable)
        if allow_variable_in_ans: return val, where
        raise KeyError("%s not bound" % str(val))

    def mark(self, save_all_undo = False):
        if save_all_undo: self.save_all_undo_count += 1
        return len(self.undo_list)

    def end_save_all_undo(self):
        assert self.save_all_undo_count > 0
        self.save_all_undo_count -= 1

    def undo_to_mark(self, mark, *var_names_to_undo):
        for var_name, var_context in self.undo_list[mark:]:
            var_context._unbind(var_name)
        del self.undo_list[mark:]
        for var_name in var_names_to_undo:
            self._unbind(var_name)

    def done(self):
        """ Unbinds all variables bound through 'self's 'bind' method.
            The assumption here is that 'self' is being abandoned, so we don't
            need to worry about self.bindings.
        """
        for var_name, var_context in self.undo_list:
            var_context._unbind(var_name)

    def _unbind(self, var_name):
        del self.bindings[var_name]

class bc_context(simple_context):
    def __init__(self, rule):
        super(bc_context, self).__init__()
        self.rule = rule

    def name(self): return self.rule.name

    def __repr__(self):
        return "<bc_context for %s at 0x%x>" % (self.name(), id(self))

    def create_plan(self, final = None):
        if final is None: final = {}
        return self.rule.make_plan(self, final)

class variable(pattern.pattern):
    """ The code to force variables of the same name to be the same object is
        probably not needed anymore...
    """
    Variables = {}

    def __new__(cls, name):
        var = cls.Variables.get(name)
        if var is None:
            var = super(variable, cls).__new__(cls)
            cls.Variables[name] = var
        return var

    def __init__(self, name):
        self.name = name

    def __repr__(self): return '$' + self.name

    def lookup(self, my_context, allow_variable_in_ans = False):
        return my_context.lookup(self, allow_variable_in_ans)

    def match_data(self, bindings, my_context, data):
        if self.name in debug:
            sys.stderr.write("%s.match_data(%s, %s, %s)\n" %
                (self, bindings, my_context, data))
        var, var_context = my_context.lookup(self, True)
        if isinstance(var, variable):
            bindings.bind(var.name, var_context, data)
            return True
        if self.name in debug:
            sys.stderr.write("%s.match_data: lookup got %s in %s\n" %
                (self, var, var_context))
        if var_context is None: return var == data
        return var.match_data(bindings, var_context, data)

    def simple_match_pattern(self, bindings, my_context, pattern_b, b_context):
        var, var_context = my_context.lookup(self, True)
        if isinstance(var, variable):
            bindings.bind(var.name, var_context, pattern_b, b_context)
            return True
        if var_context is None:
            return pattern_b.match_data(bindings, b_context, var)
        return var.simple_match_pattern(bindings, var_context,
                                        pattern_b, b_context)

    def match_pattern(self, bindings, my_context, pattern_b, b_context):
        var, var_context = my_context.lookup(self, True)
        if isinstance(var, variable):
            bindings.bind(var.name, var_context, pattern_b, b_context)
            return True
        if var_context is None:
            return pattern_b.match_data(bindings, b_context, var)
        return var.match_pattern(bindings, var_context, pattern_b, b_context)

    def as_data(self, my_context, allow_vars = False, final = None):
        return my_context.lookup_data(self.name, allow_vars, final)

    def is_data(self, my_context):
        return my_context.is_bound(self)

class anonymous(variable):
    def __init__(self, name):
        assert name[0] == '_', \
               "anonymous variables must start with '_', not %s" % name
        super(anonymous, self).__init__(name)

    def lookup(self, my_context, allow_variable_in_ans = False):
        if allow_variable_in_ans: return self, my_context
        raise KeyError("$%s not bound" % self.name)

    def match_data(self, bindings, my_context, data):
        return True

    def match_pattern(self, bindings, my_context, pattern_b, b_context):
        return True

    def as_data(self, my_context, allow_vars = False, final = None):
        if allow_vars: return "$%s" % self.name
        raise KeyError("$%s not bound" % self.name)

    def is_data(self, my_context):
        return False

