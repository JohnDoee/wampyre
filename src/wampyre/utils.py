import random
import re


def generate_id():
    return random.randint(1, 2 ** 53)


def uri_pattern_to_prefix(uri):
    return re.compile(r'^%s.*$' % (re.escape(uri), ))


def uri_pattern_to_wildcard(uri):
    return re.compile(r'^%s$' % (re.escape(uri).replace(r'\.\.', r'\.[0-9a-z_]+\.'), ))
