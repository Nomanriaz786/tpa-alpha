from admin_api import subscribers as subscribers_api


def test_build_subscriber_where_sql_qualifies_active_filter():
    where_sql, params = subscribers_api.build_subscriber_where_sql(search=None, active_only=True)

    assert where_sql == " WHERE subscribers.is_active = TRUE AND subscribers.expires_at > NOW()"
    assert params == {}


def test_build_subscriber_where_sql_includes_search_across_subscriber_fields():
    where_sql, params = subscribers_api.build_subscriber_where_sql(search="noman", active_only=False)

    assert "subscribers.discord_username ILIKE :search" in where_sql
    assert "subscribers.discord_id ILIKE :search" in where_sql
    assert "subscribers.tradingview_username ILIKE :search" in where_sql
    assert "subscribers.email ILIKE :search" in where_sql
    assert "member_affiliate.code ILIKE :search" in where_sql
    assert params == {"search": "%noman%"}
