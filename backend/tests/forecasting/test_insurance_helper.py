"""F15 insurance helper: guidance gated by officer verification; yield context labelled."""

from app.schemes.insurance import build_helper, guidance_items


def test_every_guidance_item_has_source_and_three_languages() -> None:
    items = guidance_items()
    assert {"premium", "loss_intimation", "claims_assessment"} <= {i["id"] for i in items}
    for i in items:
        assert i["source_url"].startswith("https://") and set(i["text"]) == {"en", "hi", "te"}


def test_farmers_see_no_guidance_until_pmfby_is_verified() -> None:
    h = build_helper(scheme=None, verified=False, officer=False, language="te", yield_card=None)
    assert h["guidance"] == [] and h["status"] == "pending_officer_verification"
    assert h["official_portal"] == "https://pmfby.gov.in/"


def test_officers_see_drafts_with_their_open_questions() -> None:
    h = build_helper(scheme=None, verified=False, officer=True, language="en", yield_card=None)
    loss = next(i for i in h["guidance"] if i["id"] == "loss_intimation")
    assert "72 hours" in loss["text"] and loss["needs_official_source"]


def test_yield_context_is_never_presented_as_official() -> None:
    h = build_helper(scheme={"key": "pmfby"}, verified=True, officer=False, language="hi",
                     yield_card={"predicted_yield": 2.0, "official": True})
    assert h["yield_context"]["official"] is False
    assert "YES-TECH" in h["yield_context"]["notice"]
    assert all("needs_official_source" not in i for i in h["guidance"])  # farmer view
