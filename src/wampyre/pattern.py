import re

from .opcodes import OP


class UnknownPatternException(Exception):
    pass


class Pattern:
    uri_pattern = re.compile(r"^([0-9a-z_]+\.)*([0-9a-z_]+)$")
    min_id = 1
    max_id = 2 ** 53

    def __init__(self, *pattern):
        self.pattern = pattern
        self.opcodes = {opcode for (opcode_name, opcode) in OP.__dict__.items() if not opcode_name.startswith('_')}

    def __call__(self, *args):
        if len(args) > len(self.pattern):
            return False

        for i, arg_pattern in enumerate(self.pattern):
            optional = arg_pattern.endswith('?')
            arg_pattern = arg_pattern.rstrip('?')
            system = arg_pattern.endswith('!')
            arg_pattern = arg_pattern.rstrip('!')

            if len(args) <= i:
                if optional:
                    return True
                else:
                    return False

            value = args[i]

            if arg_pattern == 'uri':
                if not isinstance(value, str) or not self.uri_pattern.match(value):
                    return False
                if not system and value.split('.')[0] == 'wamp':
                    return False
            elif arg_pattern == 'id':
                if not isinstance(value, int) or value < self.min_id or value > self.max_id:
                    return False
            elif arg_pattern == 'opcode':
                if value not in self.opcodes:
                    return False
            elif arg_pattern == 'dict':
                if not isinstance(value, dict):
                    return False
            elif arg_pattern == 'list':
                if not isinstance(value, list) and not isinstance(value, tuple):
                    return False
            else:
                raise UnknownPatternException('%s is not a known pattern matcher' % (arg_pattern, ))

        return True