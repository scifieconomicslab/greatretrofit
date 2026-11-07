"""SM-4 (issue #2): what the means test does today, and that the pack text says exactly that.

The behaviour is pinned, not endorsed: whether the means test SHOULD restrict the rebate is an open design decision (issue #2 stays open).
Python and JS apply the same rule: outside the cut-off a household buys on the market at the vendor price, with no rebate and no public payment.
"""
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from node_util import needs_node, run_node
from retrofit_v3 import Params, run_simulation

ROOT = Path(__file__).resolve().parents[2]
BASE = Params(n_buildings=60, horizon_months=84, credit_access="open", deduction_rate=0.5, means_test=True, means_test_max_quintile=2, savings_scale=3.0)


def _counts(ev):
    return dict(n=len(ev), rebate_above_cut=sum(1 for e in ev if e.quintile > 2 and e.rebate > 0), rebate_inside=sum(1 for e in ev if e.quintile <= 2 and e.rebate > 0),
                market_above_cut=sum(1 for e in ev if e.quintile > 2 and not e.subsidised and e.rebate == 0), subsidised_above_cut=sum(1 for e in ev if e.quintile > 2 and e.subsidised))


def test_means_test_restricts_the_rebate_too():
    c = _counts(run_simulation(replace(BASE, delivery_mode="rebate_market")).events)
    assert c["rebate_inside"] > 0 and c["market_above_cut"] > 0       # both groups occur, so the test is not vacuous
    assert c["rebate_above_cut"] == 0 and c["subsidised_above_cut"] == 0


@pytest.mark.parametrize("mode", ["passthrough", "public_service"])
def test_means_test_restricts_pay_direct_and_public_service(mode):
    r = run_simulation(replace(BASE, delivery_mode=mode))
    above = [e for e in r.events if e.quintile > 2]
    assert above and all(not e.subsidised and e.state_pays_now == 0 and e.rebate == 0 for e in above)
    assert any(e.quintile <= 2 and e.subsidised and e.state_pays_now > 0 for e in r.events)


def test_without_the_means_test_the_rebate_reaches_every_quintile():
    ev = run_simulation(replace(BASE, means_test=False, delivery_mode="rebate_market")).events
    assert any(e.quintile > 2 and e.rebate > 0 for e in ev)


def test_pack_text_says_the_rebate_is_restricted():
    help_ = yaml.safe_load((ROOT / "packs/great-retrofit/pack.yaml").read_text())["params"]["means_test"]["help"].lower()
    assert "does not apply" not in help_
    assert "rebate" in help_ and "pay-direct" in help_ and "public service" in help_
    assert "market" in help_ and "no rebate" in help_


@needs_node
def test_js_applies_the_same_rule():
    py = _counts(run_simulation(replace(BASE, delivery_mode="rebate_market")).events)
    assert run_node("means_test_rebate.js") == py
