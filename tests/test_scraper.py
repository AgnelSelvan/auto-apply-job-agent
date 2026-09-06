from apply_for_job.scraper import parse_time_ago

def test_parse_time_ago_hours():
    assert parse_time_ago("5 hours ago") == 5
    assert parse_time_ago("1 hour ago") == 1

def test_parse_time_ago_days():
    assert parse_time_ago("2 days ago") == 48

def test_parse_time_ago_unknown():
    assert parse_time_ago("just now") == 999999
