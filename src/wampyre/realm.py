from .opcodes import OP
from .utils import generate_id


class Realm:
    def __init__(self, realm):
        self.realm = realm

        self.subscriptions = {}
        self.subscription_ids = {}

        self.registrations = {}
        self.registration_ids = {}

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
        subscription_id = generate_id()
        self.subscriptions.setdefault(topic, {})[subscription_id] = session
        self.subscription_ids.setdefault(session, {})[subscription_id] = topic
        return subscription_id

    def unsubscribe(self, session, subscription_id):
        """
        Unsubscribes a client from a subscription_id
        Returns True if unsubscribed, otherwise False
        """
        topic = self.subscription_ids.get(session, {}).get(subscription_id)
        if not topic:
            return False

        del self.subscription_ids[session][subscription_id]
        if not self.subscription_ids[session]:
            del self.subscription_ids[session]

        del self.subscriptions[topic][subscription_id]

        return True

    def publish(self, session, options, topic, args=None, kwargs=None):
        """
        Publish a message to a topic.
        Optionally returns a publication_id.
        """
        publication_id = generate_id()
        if topic in self.subscriptions:
            event_args = []
            if args is not None:
                event_args.append(args)
                if kwargs is not None:
                    event_args.append(kwargs)

            for subscription_id, subscription_session in self.subscriptions[topic].items():
                cmd = [OP.EVENT, subscription_id, publication_id, {}] + event_args
                subscription_session.send(*cmd)

        if options.get('acknowledge'):
            return publication_id

    ### Dealer functionality ###
    def register(self, session, procedure):
        """
        Registers a procedure.
        Returns a registration_id
        """
        if procedure in self.registrations:
            return None

        registration_id = generate_id()

        self.registrations[procedure] = (session, registration_id)
        self.registration_ids.setdefault(session, {})[registration_id] = procedure

        return registration_id

    def unregister(self, session, registration_id):
        """
        Unregisters a procedure.
        """
        procedure = self.registration_ids.get(session, {}).get(registration_id)
        if not procedure:
            return False

        del self.registration_ids[session][registration_id]
        if not self.registration_ids[session]:
            del self.registration_ids[session]

        del self.registrations[procedure]

        return True

    def call(self, session, request_id, procedure, args=None, kwargs=None):
        """
        Call a procedure.
        """
        if procedure not in self.registrations:
            return False

        procedure_session, procedure_registration_id = self.registrations[procedure]

        invocation_args = []
        if args is not None:
            invocation_args.append(args)
            if kwargs is not None:
                invocation_args.append(kwargs)

        invocation_request_id = procedure_session.generate_id()
        cmd = [OP.INVOCATION, invocation_request_id, procedure_registration_id, {}] + invocation_args
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

    def error_invocation(self, session, invocation_id, details, error, args=None, kwargs=None):
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

        if session in self.subscription_ids:
            for subscription_id, topic in self.subscription_ids[session].items():
                del self.subscriptions[topic][subscription_id]
                if not self.subscriptions[topic]:
                    del self.subscriptions[topic]

            del self.subscription_ids[session]

        if session in self.registration_ids:
            for registration_id, procedure in self.registration_ids[session].items():
                del self.registrations[procedure]

            del self.registration_ids[session]

        if session in self.invocations:
            for invocation_id in self.invocations[session]:
                request_id = self.invocation_to_call_id[invocation_id]
                if request_id in self.call_ids:
                    self.error_invocation(session, request_id, {}, 'wamp.error.callee_lost')

            del self.invocations[session]

        if session in self.calls:
            for request_id in self.calls[session]:
                del self.call_ids[request_id]

            del self.calls[session]


class RealmManager:
    def __init__(self):
        self.realms = {}

    def get_realm(self, realm):
        if realm not in self.realms:
            self.realms[realm] = Realm(realm)

        return self.realms[realm]


realm_manager = RealmManager()
