from app.tools.impl import budget_split, make_report, sponsorship_package, timeline
from app.tools.schemas import (
    BudgetSplitRequest,
    ReportRequest,
    SponsorshipPackageRequest,
    TimelineRequest,
)


def test_budget_split_sums_to_total():
    req = BudgetSplitRequest(
        total_krw=30_000_000,
        paid_ads_ratio=0.4,
        content_ratio=0.3,
        community_ratio=0.2,
        contingency_ratio=0.1,
    )
    res = budget_split(req)
    assert res.total == 30_000_000
    assert res.ads_paid + res.content_prod + res.community + res.contingency == 30_000_000


def test_timeline_generates_requested_weeks():
    req = TimelineRequest(start_date="2026-05-01", weeks=3)
    res = timeline(req)
    assert res.weeks == 3
    assert len(res.items) == 3
    assert res.items[0].week == 1


def test_sponsorship_package_descending_prices():
    req = SponsorshipPackageRequest(total_target_krw=60_000_000, tier_count=3, org_type="festival")
    res = sponsorship_package(req)
    assert len(res.tiers) == 3
    assert sum(t.price_krw for t in res.tiers) == 60_000_000
    assert res.tiers[0].price_krw >= res.tiers[1].price_krw >= res.tiers[2].price_krw


def test_make_report_returns_markdown():
    req = ReportRequest(
        campaign_title="Q2 Campaign",
        period="2026-05-01~2026-05-14",
        budget_total_krw=30_000_000,
        kpis=["CTR", "Tickets"],
        highlights=["CTR 3.2% 달성"],
    )
    res = make_report(req)
    assert "Q2 Campaign" in res.markdown
