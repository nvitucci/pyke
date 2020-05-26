# $Id: special.py 4dca5ad0f397 2010-03-10 mtnyogi $
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

import subprocess
import contextlib
from pyke import knowledge_base, rule_base

# claim_goal, fact, prove_all, gather_all

class special_knowledge_base(knowledge_base.knowledge_base):
    def __init__(self, engine):
        super(special_knowledge_base, self).__init__(engine, 'special')

    def add_fn(self, fn):
        if fn.name in self.entity_lists:
            raise KeyError("%s.%s already exists" % (self.name, fn.name))
        self.entity_lists[fn.name] = fn

    def print_stats(self, f):
        pass

class special_fn(knowledge_base.knowledge_entity_list):
    def __init__(self, special_base, name):
        super(special_fn, self).__init__(name)
        special_base.add_fn(self)

    def lookup(self, bindings, pat_context, patterns):
        raise AssertionError("special.%s may not be used in forward chaining "
                             "rules" % self.name)

    def prove(self, bindings, pat_context, patterns):
        raise AssertionError("special.%s may not be used in backward chaining "
                             "rules" % self.name)

class special_both(special_fn):
    def prove(self, bindings, pat_context, patterns):
        return self.lookup(bindings, pat_context, patterns)

class claim_goal(special_fn):
    r'''
        >>> class stub(object):
        ...     def add_fn(self, fn): pass
        >>> cg = claim_goal(stub())
        >>> mgr = cg.prove(None, None, None)
        >>> gen = iter(mgr.__enter__())
        >>> next(gen)
        >>> next(gen)
        Traceback (most recent call last):
            ...
        pyke.rule_base.StopProof
        >>> mgr.__exit__(None, None, None)
        >>> cg.lookup(None, None, None)
        Traceback (most recent call last):
            ...
        AssertionError: special.claim_goal may not be used in forward chaining rules
    '''
    def __init__(self, special_base):
        super(claim_goal, self).__init__(special_base, 'claim_goal')

    def prove(self, bindings, pat_context, patterns):
        def gen():
            yield
            raise rule_base.StopProof

        return contextlib.closing(gen())

def run_cmd(pat_context, cmd_pat, cwd_pat=None, stdin_pat=None):
    r'''
        >>> from pyke import pattern
        >>> run_cmd(None, pattern.pattern_literal(('true',)))
        (0, '', '')
        >>> run_cmd(None, pattern.pattern_literal(('false',)))
        (1, '', '')
        >>> ret, out, err = run_cmd(None, pattern.pattern_literal(('pwd',)))
        >>> ret
        0
        >>> err
        ''
        >>> import os
        >>> cwd = os.getcwd() + '\n'
        >>> out == cwd
        True
        >>> run_cmd(None, pattern.pattern_literal(('pwd',)),
        ...         pattern.pattern_literal('/home/bruce'))
        (0, '/home/bruce\n', '')
    '''
    stdin = None
    if stdin_pat is not None:
        data = stdin_pat.as_data(pat_context)
        if data is not None:
            stdin = data.encode()
    process = subprocess.Popen(cmd_pat.as_data(pat_context),
                               bufsize=-1,
                               universal_newlines=True,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               cwd= None if cwd_pat is None
                                         else cwd_pat.as_data(pat_context))
    out, err = process.communicate(stdin)
    return process.returncode, out, err

class check_command(special_both):
    r'''
        >>> from pyke import pattern, contexts
        >>> class stub(object):
        ...     def add_fn(self, fn): pass
        >>> cc = check_command(stub())
        >>> ctxt = contexts.simple_context()
        >>> mgr = cc.lookup(ctxt, ctxt, (pattern.pattern_literal(('true',)),))
        >>> gen = iter(mgr.__enter__())
        >>> next(gen)
        >>> ctxt.dump()
        >>> next(gen)
        Traceback (most recent call last):
            ...
        StopIteration
        >>> ctxt.dump()
        >>> mgr.__exit__(None, None, None)
        >>> mgr = cc.lookup(ctxt, ctxt, (pattern.pattern_literal(('false',)),))
        >>> gen = iter(mgr.__enter__())
        >>> next(gen)
        Traceback (most recent call last):
            ...
        StopIteration
        >>> ctxt.dump()
        >>> mgr.__exit__(None, None, None)
        >>> mgr = cc.prove(ctxt, ctxt, (pattern.pattern_literal(('true',)),))
        >>> gen = iter(mgr.__enter__())
        >>> next(gen)
        >>> ctxt.dump()
        >>> next(gen)
        Traceback (most recent call last):
            ...
        StopIteration
        >>> ctxt.dump()
        >>> mgr.__exit__(None, None, None)
    '''
    def __init__(self, special_base):
        super(check_command, self).__init__(special_base, 'check_command')

    def lookup(self, bindings, pat_context, patterns):
        if len(patterns) < 1: return knowledge_base.Gen_empty
        retcode, out, err = run_cmd(pat_context, patterns[0],
                                    patterns[1] if len(patterns) > 1
                                                else None,
                                    patterns[2] if len(patterns) > 2
                                                else None)
        if retcode: return knowledge_base.Gen_empty
        return knowledge_base.Gen_once

class command(special_both):
    r'''
        >>> from pyke import pattern, contexts
        >>> class stub(object):
        ...     def add_fn(self, fn): pass
        >>> c = command(stub())
        >>> ctxt = contexts.simple_context()
        >>> mgr = c.lookup(ctxt, ctxt,
        ...                (contexts.variable('ans'),
        ...                 pattern.pattern_literal(('echo', 'hi'))))
        >>> gen = iter(mgr.__enter__())
        >>> next(gen)
        >>> ctxt.dump()
        ans: ('hi',)
        >>> next(gen)
        Traceback (most recent call last):
            ...
        StopIteration
        >>> ctxt.dump()
        >>> mgr.__exit__(None, None, None)
        >>> mgr = c.lookup(ctxt, ctxt,
        ...                (contexts.variable('ans'),
        ...                 pattern.pattern_literal(('cat',)),
        ...                 pattern.pattern_literal(None),
        ...                 pattern.pattern_literal('line1\nline2\nline3\n')))
        >>> gen = iter(mgr.__enter__())
        >>> next(gen)
        >>> ctxt.dump()
        ans: ('line1', 'line2', 'line3')
        >>> next(gen)
        Traceback (most recent call last):
            ...
        StopIteration
        >>> ctxt.dump()
        >>> mgr.__exit__(None, None, None)
    '''
    def __init__(self, special_base):
        super(command, self).__init__(special_base, 'command')

    def lookup(self, bindings, pat_context, patterns):
        if len(patterns) < 2: return knowledge_base.Gen_empty
        retcode, out, err = run_cmd(pat_context, patterns[1],
                                    patterns[2] if len(patterns) > 2
                                                else None,
                                    patterns[3] if len(patterns) > 3
                                                else None)
        if retcode != 0:
            raise subprocess.CalledProcessError(
                                retcode,
                                ' '.join(patterns[1].as_data(pat_context)))
        def gen():
            mark = bindings.mark(True)
            try:
                outlines = tuple(out.rstrip('\n').split('\n'))
                if patterns[0].match_data(bindings, pat_context, outlines):
                    bindings.end_save_all_undo()
                    yield
                else:
                    bindings.end_save_all_undo()
            finally:
                bindings.undo_to_mark(mark)

        return contextlib.closing(gen())

class general_command(special_both):
    r'''
        >>> from pyke import pattern, contexts
        >>> class stub(object):
        ...     def add_fn(self, fn): pass
        >>> gc = general_command(stub())
        >>> ctxt = contexts.simple_context()
        >>> ctxt.dump()
        >>> mgr = gc.lookup(ctxt, ctxt,
        ...                 (contexts.variable('ans'),
        ...                  pattern.pattern_literal(('echo', 'hi'))))
        >>> gen = iter(mgr.__enter__())
        >>> next(gen)
        >>> ctxt.dump()
        ans: (0, 'hi\n', '')
        >>> next(gen)
        Traceback (most recent call last):
            ...
        StopIteration
        >>> ctxt.dump()
        >>> mgr.__exit__(None, None, None)
    '''
    def __init__(self, special_base):
        super(general_command, self).__init__(special_base, 'general_command')

    def lookup(self, bindings, pat_context, patterns):
        if len(patterns) < 2: return knowledge_base.Gen_empty
        ans = run_cmd(pat_context, patterns[1],
                      patterns[2] if len(patterns) > 2 else None,
                      patterns[3] if len(patterns) > 3 else None)

        def gen():
            mark = bindings.mark(True)
            try:
                if patterns[0].match_data(bindings, pat_context, ans):
                    bindings.end_save_all_undo()
                    yield
                else:
                    bindings.end_save_all_undo()
            finally:
                bindings.undo_to_mark(mark)

        return contextlib.closing(gen())

def create_for(engine):
    special_base = special_knowledge_base(engine)
    claim_goal(special_base)
    check_command(special_base)
    command(special_base)
    general_command(special_base)


