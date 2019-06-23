from ..utils import uri_pattern_to_prefix, uri_pattern_to_wildcard


def test_uri_pattern_to_prefix():
    register_uri_pattern = uri_pattern_to_prefix("com.myapp.myobject1")

    assert register_uri_pattern.match("com.myapp.myobject1.myprocedure1")
    assert register_uri_pattern.match("com.myapp.myobject1-mysubobject1")
    assert register_uri_pattern.match("com.myapp.myobject1.mysubobject1.myprocedure1")
    assert register_uri_pattern.match("com.myapp.myobject1")

    assert not register_uri_pattern.match("com.myapp.myobject2")
    assert not register_uri_pattern.match("com.myapp.myobject")

    subscribe_uri_pattern = uri_pattern_to_prefix("com.myapp.topic.emergency")

    assert subscribe_uri_pattern.match("com.myapp.topic.emergency.11")
    assert subscribe_uri_pattern.match("com.myapp.topic.emergency-low")
    assert subscribe_uri_pattern.match("com.myapp.topic.emergency.category.severe")
    assert subscribe_uri_pattern.match("com.myapp.topic.emergency")


def test_uri_pattern_to_wildcard():
    register_uri_pattern = uri_pattern_to_wildcard("com.myapp..myprocedure1")

    assert register_uri_pattern.match("com.myapp.myobject1.myprocedure1")
    assert register_uri_pattern.match("com.myapp.myobject2.myprocedure1")

    assert not register_uri_pattern.match(
        "com.myapp.myobject1.myprocedure1.mysubprocedure1"
    )
    assert not register_uri_pattern.match("com.myapp.myobject1.myprocedure2")
    assert not register_uri_pattern.match("com.myapp2.myobject1.myprocedure1")

    subscribe_uri_pattern = uri_pattern_to_wildcard("com.myapp..userevent")

    assert subscribe_uri_pattern.match("com.myapp.foo.userevent")
    assert subscribe_uri_pattern.match("com.myapp.bar.userevent")
    assert subscribe_uri_pattern.match("com.myapp.a12.userevent")

    assert not subscribe_uri_pattern.match("com.myapp.foo.userevent.bar")
    assert not subscribe_uri_pattern.match("com.myapp.foo.user")
    assert not subscribe_uri_pattern.match("com.myapp2.foo.userevent")
