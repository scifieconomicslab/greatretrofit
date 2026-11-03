mall changes, large effect:

Replace random (aspiration / 100) with random-float (aspiration / 100) in all three places. Then make aspiration a trait each household draws once at creation, so some sellers are persistently greedy and others eager to close.
Draw affordability per household from a truncated normal around the slider value, instead of assigning 33% to everyone in assign-income.
Draw initial capital from a lognormal or Pareto that is independent of income, so wealth and income can diverge.
Re-enable the commented-out searchLength line. Each seeker should see only a random sample of listings, not the whole market, which breaks the pile-on to the same top houses.

Medium:

Give each house independent attributes (size, age, location amenity) and build the initial stock without the one-to-one house-household mapping, so supply and demand start mismatched.
Give each household its own taste weights over those attributes plus a random taste shock, and have seekers choose by utility minus cost instead of by maximum quality.
Let buyers bid below the asking price based on their own willingness to pay, and let sellers hold a reservation price below which they refuse. That makes bargaining and failed negotiations possible.
Make the demand signal local. Compute time on market per neighbourhood instead of using the global highDemand and lowDemand multipliers, so a hot area and a cold area can diverge.

Let heterogeneity regenerate during the run:

Replace the uniform n-of exit draw with a per-household hazard of selling or moving that depends on age, income shocks and financial stress.
Add an income process: a lifecycle profile by age plus an AR(1) shock on log income, with occasional unemployment spells.
Add births, deaths, household formation and inheritance of houses. This is the ODD's own first extension and it stops the system relaxing to a steady state.
Add consumption and capital dynamics that can push savings down as well as up, so households do not all drift to cash purchases.

Credit and banking:

Give banks different LTV caps and rate spreads, and let borrowers choose the best offer.
Make lending depend on the borrower, using a payment-to-income cap and a risk premium that rises with LTV.
Add default and foreclosure. At the moment a household that cannot pay simply carries on, so there is no way for a crash to propagate through bank balance sheets.
Let banks adjust their own LTV and rates in response to recent price growth and losses, which is the mechanism behind credit-driven bubbles.

Market realism:

Add heterogeneous expectations, with some households extrapolating recent price growth and others anchoring on fundamental value (price to rent).
Add the investment market from the ODD: landlords buy when expected net rental yield beats a hurdle that varies by household, and sell when it does not.
Add transaction costs, moving costs and vacancy periods, so churn is not free.
Let the stock evolve: depreciation, maintenance, demolition, and construction that responds to price relative to build cost with a lag.
Make the interbank rate and income growth time-varying, with at least one exogenous shock scenario to test against.

Check that it worked

Add monitors for the Gini of wealth, price dispersion within and between neighbourhoods, share of cash buyers, and the spread of time on market. Record them before and after each change so you can see which fix actually moved heterogeneity.
Calibrate the income and wealth distributions to empirical data for the region you care about, then compare simulated price and rent dispersion against observed figures.
