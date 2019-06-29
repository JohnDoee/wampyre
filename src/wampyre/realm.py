import logging

from .opcodes import OP
from .utils import generate_id, URIPattern

logger = logging.getLogger(__name__)


class Realm:
    def __init__(self, realm):
        self.realm = realm

        self.subscriptions = URIPattern(allow_duplicate=True)
        self.registrations = URIPattern(allow_duplicate=False)

        self.calls = {}
        self.call_ids = {}
        self.invocation_to_call_id = {}
        self.invocations = {}

        self.sessions = set()

    ### Broker functionality ###
    def subscribe(self, session, options, topic):
        """
        Subscribes a client to a topic.
        Returns a subscription_id
        """
        return self.subscriptions.register_uri(session, topic, options.get("match"))

    def unsubscribe(self, session, subscription_id):
        """
        Unsubscribes a client from a subscription_id
        Returns True if unsubscribed, otherwise False
        """
        return self.subscriptions.unregister_uri(session, subscription_id)

    def publish(self, options, topic, args=None, kwargs=None):
        """
        Publish a message to a topic.
        Optionally returns a publication_id.
        """
        publication_id = generate_id()
        subscriptions = self.subscriptions.match_uri(topic)
        if subscriptions:
            event_args = []
            if args is not None:
                event_args.append(args)
                if kwargs is not None:
                    event_args.append(kwargs)

            for subscription_session, subscription_id in subscriptions:
                cmd = [
                    OP.EVENT,
                    subscription_id,
                    publication_id,
                    {"topic": topic},
                ] + event_args
                subscription_session.send(*cmd)

        if options.get("acknowledge"):
            return publication_id

    ### Dealer functionality ###
    def register(self, session, options, procedure):
        """
        Registers a procedure.
        Returns a registration_id
        """
        return self.registrations.register_uri(session, procedure, options.get("match"))

    def unregister(self, session, registration_id):
        """
        Unregisters a procedure.
        """
        return self.registrations.unregister_uri(session, registration_id)

    def call(self, session, request_id, procedure, args=None, kwargs=None):
        """
        Call a procedure.
        """
        match = self.registrations.match_uri(procedure)
        if not match:
            return False

        procedure_session, procedure_registration_id = match

        invocation_args = []
        if args is not None:
            invocation_args.append(args)
            if kwargs is not None:
                invocation_args.append(kwargs)

        invocation_request_id = procedure_session.generate_id()
        cmd = [
            OP.INVOCATION,
            invocation_request_id,
            procedure_registration_id,
            {"procedure": procedure},
        ] + invocation_args
        procedure_session.send(*cmd)

        self.calls.setdefault(session, set()).add(request_id)
        self.call_ids[request_id] = session

        self.invocation_to_call_id[invocation_request_id] = request_id
        self.invocations.setdefault(procedure_session, set()).add(invocation_request_id)

        return True

    def yield_(self, session, invocation_id, args=None, kwargs=None):
        """
        Get result from a procedure call.
        """
        if invocation_id not in self.invocation_to_call_id:
            return

        call_id = self.invocation_to_call_id.pop(invocation_id)
        call_session = self.call_ids.pop(call_id)
        self.calls[call_session].discard(call_id)

        call_args = []
        if args is not None:
            call_args.append(args)
            if kwargs is not None:
                call_args.append(kwargs)

        cmd = [OP.RESULT, call_id, {}] + call_args
        call_session.send(*cmd)

    def error_invocation(
        self, session, invocation_id, details, error, args=None, kwargs=None
    ):
        """
        An invocation call failed.
        """
        if invocation_id not in self.invocation_to_call_id:
            return

        call_id = self.invocation_to_call_id.pop(invocation_id)
        call_session = self.call_ids.pop(call_id)
        self.calls[call_session].discard(call_id)

        call_args = []
        if args is not None:
            call_args.append(args)
            if kwargs is not None:
                call_args.append(kwargs)

        cmd = [OP.ERROR, OP.CALL, call_id, {}, error] + call_args
        call_session.send(*cmd)

    ### External management ###
    def session_joined(self, session):
        self.sessions.add(session)

    def session_lost(self, session):
        self.sessions.discard(session)

        self.subscriptions.unregister_session(session)
        self.registrations.unregister_session(session)

        if session in self.invocations:
            for invocation_id in self.invocations[session]:
                request_id = self.invocation_to_call_id[invocation_id]
                if request_id in self.call_ids:
                    self.error_invocation(
                        session, request_id, {}, "wamp.error.callee_lost"
                    )

            del self.invocations[session]

        if session in self.calls:
            for request_id in self.calls[session]:
                del self.call_ids[request_id]

            del self.calls[session]

        if not self.sessions:
            realm_manager.discard_realm(self.realm)


class RealmManager:
    def __init__(self):
        self.realms = {}
        self.callbacks = []

    def get_realm(self, realm):
        if realm not in self.realms:
            self._trigger_callback("create", realm)
            self.realms[realm] = Realm(realm)

        return self.realms[realm]

    def get_realms(self):
        return self.realms.values()

    def discard_realm(self, realm):
        if realm in self.realms:
            self._trigger_callback("discard", realm)
            del self.realms[realm]

    def _trigger_callback(self, callback_type, realm):
        for callback in self.callbacks:
            callback(callback_type=callback_type, realm=realm)

    def register_callback(self, f):
        self.callbacks.append(f)

    def unregister_callback(self, f):
        try:
            self.callbacks.remove(f)
        except ValueError:
            pass


realm_manager = RealmManager()
