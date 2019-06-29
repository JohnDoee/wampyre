import logging
import random

logger = logging.getLogger(__name__)


def generate_id():
    return random.randint(1, 2 ** 53)


class TraverseDict(dict):
    def __init__(self, uri_fragment, parent=None, *args, **kwargs):
        self.uri_fragment = uri_fragment
        self.parent = parent
        self.sessions = []
        super().__init__(*args, **kwargs)

    def register_session(self, session, pattern_id):
        logger.debug(f"Registering session {session}/{pattern_id} to {self.uri}")
        self.sessions.append((session, pattern_id))

    def unregister_session(self, session, pattern_id):
        if (session, pattern_id) in self.sessions:
            logger.debug(
                f"Unregistering session {session}/{pattern_id} from {self.uri}"
            )
            self.sessions.remove((session, pattern_id))

        self.cleanup()

    def has_sessions(self):
        return bool(self.sessions)

    def cleanup(self, source_uri=None):
        if source_uri is not None and source_uri in self:
            del self[source_uri]

        if self.parent is not None and not self.sessions and not self:
            self.parent.cleanup(self.uri_fragment)

    @property
    def uri(self):
        d = self
        uri = []
        while d.parent:
            uri.append(d.uri_fragment)
            d = d.parent

        return ".".join(uri[::-1])


class URIPattern:
    def __init__(self, allow_duplicate):
        self.allow_duplicate = allow_duplicate
        self.dict = TraverseDict(None)
        self.sessions = {}

    def traverse_patterns(self, uri_fragments, pattern, create=False):
        uri_fragment = uri_fragments.pop(0)
        if create and uri_fragment not in pattern:
            pattern[uri_fragment] = TraverseDict(uri_fragment, parent=pattern)

        patterns = []
        if not create:
            if "" in pattern and uri_fragments:
                logger.debug(
                    f"{pattern.uri} - Wildcard match, using it with pattern: {uri_fragments}"
                )
                patterns += self.traverse_patterns(list(uri_fragments), pattern[""])

            if "*" in pattern:
                patterns.append(pattern["*"])

        if uri_fragment in pattern:
            if uri_fragments:
                return (
                    self.traverse_patterns(
                        list(uri_fragments), pattern[uri_fragment], create=create
                    )
                    + patterns
                )
            else:
                return [pattern[uri_fragment]] + patterns
        else:
            return patterns

    def register_uri(self, session, uri, match):
        pattern_id = generate_id()

        uri_fragments = uri.split(".")

        if match == "prefix":
            uri_fragments = uri_fragments + ["*"]

        pattern = self.traverse_patterns(uri_fragments, self.dict, create=True)[0]
        if not self.allow_duplicate and pattern.has_sessions():
            return None
        pattern.register_session(session, pattern_id)
        self.sessions.setdefault(session, {})[pattern_id] = pattern

        return pattern_id

    def unregister_uri(self, session, pattern_id):
        session_uris = self.sessions.setdefault(session, {})

        if pattern_id not in session_uris:
            return False

        pattern = session_uris[pattern_id]
        pattern.unregister_session(session, pattern_id)
        del session_uris[pattern_id]

        return True

    def unregister_session(self, session):
        if session not in self.sessions:
            return False

        session_uris = self.sessions.pop(session)
        for pattern_id, pattern in session_uris.items():
            pattern.unregister_session(session, pattern_id)

        return True

    def match_uri(self, uri):
        patterns = self.traverse_patterns(uri.split("."), self.dict)
        if self.allow_duplicate:
            return [s for p in patterns for s in p.sessions]
        elif patterns and patterns[0].has_sessions():
            return patterns[0].sessions[0]
        else:
            return None
