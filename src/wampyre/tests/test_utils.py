from ..utils import URIPattern


def test_uri_pattern_no_duplicate():
    pattern = URIPattern(False)

    pattern_s1_p1 = pattern.register_uri("testsession1", "a1.b2.c3.d4.e55", "exact")
    pattern_s2_p1 = pattern.register_uri("testsession2", "a1.b2.c3", "prefix")
    pattern_s3_p1 = pattern.register_uri("testsession3", "a1.b2.c3.d4", "prefix")
    pattern_s4_p1 = pattern.register_uri("testsession4", "a1.b2..d4.e5", "wildcard")
    pattern_s5_p1 = pattern.register_uri("testsession5", "a1.b2.c33..e5", "wildcard")
    pattern_s6_p1 = pattern.register_uri("testsession6", "a1.b2..d4.e5..g7", "wildcard")
    pattern_s7_p1 = pattern.register_uri("testsession7", "a1.b2..d4..f6.g7", "wildcard")

    assert pattern.match_uri("a1.b2.c3.d4.e55") == ("testsession1", pattern_s1_p1)
    assert pattern.match_uri("a1.b2.c3.d98.e74") == ("testsession2", pattern_s2_p1)
    assert pattern.match_uri("a1.b2.c3.d4.e325") == ("testsession3", pattern_s3_p1)
    assert pattern.match_uri("a1.b2.c55.d4.e5") == ("testsession4", pattern_s4_p1)
    assert pattern.match_uri("a1.b2.c33.d4.e5") == ("testsession5", pattern_s5_p1)
    assert pattern.match_uri("a1.b2.c88.d4.e5.f6.g7") == ("testsession6", pattern_s6_p1)
    assert pattern.match_uri("a2.b2.c2.d2.e2") is None

    assert not pattern.register_uri("testsession10", "a1.b2.c3.d4.e55", "exact")


def test_uri_pattern_duplicate():
    pattern = URIPattern(True)

    pattern_s1_p1 = pattern.register_uri("testsession1", "a1.b2.c3.d4.e55", "exact")
    pattern_s2_p1 = pattern.register_uri("testsession2", "a1.b2.c3", "prefix")
    pattern_s3_p1 = pattern.register_uri("testsession3", "a1.b2..d4.e5", "wildcard")
    pattern_s4_p1 = pattern.register_uri("testsession4", "a1.b2..d4.e5..g7", "wildcard")

    assert sorted(pattern.match_uri("a1.b2.c3.d4.e55")) == [
        ("testsession1", pattern_s1_p1),
        ("testsession2", pattern_s2_p1),
    ]
    assert sorted(pattern.match_uri("a1.b2.c55.d4.e5")) == [
        ("testsession3", pattern_s3_p1)
    ]
    assert sorted(pattern.match_uri("a1.b2.c3.d4.e5")) == [
        ("testsession2", pattern_s2_p1),
        ("testsession3", pattern_s3_p1),
    ]
    assert sorted(pattern.match_uri("a2.b2.c2.d2.e2")) == []


def test_uri_unregister():
    pattern = URIPattern(True)

    pattern_s1_p1 = pattern.register_uri("testsession1", "a1.b2.c3.d4.e55", "exact")
    pattern_s1_p2 = pattern.register_uri("testsession1", "a1.b2.c3.d4.e56", "exact")
    pattern_s1_p3 = pattern.register_uri("testsession1", "a1.b2.c3", "prefix")
    pattern_s2_p1 = pattern.register_uri("testsession2", "a1.b2.c3.d4.e56", "exact")
    pattern_s2_p2 = pattern.register_uri("testsession2", "a1.b2.c3.d4", "prefix")

    assert pattern.unregister_uri("testsession1", pattern_s1_p1)
    assert sorted(pattern.match_uri("a1.b2.c3.d4.e55")) == [
        ("testsession1", pattern_s1_p3),
        ("testsession2", pattern_s2_p2),
    ]
    assert pattern.unregister_session("testsession1")
    assert sorted(pattern.match_uri("a1.b2.c3.d4.e55")) == [
        ("testsession2", pattern_s2_p2)
    ]
    assert pattern.unregister_session("testsession2")
