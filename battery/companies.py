"""Synthetic company profiles.

Synthetic on purpose. A real ticker carries the model's own training knowledge,
which would confound every manipulation except the brand-salience item. Each
profile is deliberately mixed, so neither buy nor sell is obviously correct and
there is room for a biasing cue to move the answer.
"""

COMPANIES = [
    dict(name="Ridgeline Industrial", sector="industrial machinery",
         rev_growth="6% a year for three years", margin="operating margin 14%, stable",
         valuation="18x forward earnings, in line with its sector",
         debt="net debt 1.4x EBITDA", note="order backlog flat for two quarters"),
    dict(name="Calder Diagnostics", sector="medical devices",
         rev_growth="11% a year for three years", margin="operating margin 9%, improving",
         valuation="27x forward earnings, above its sector",
         debt="net cash", note="one product awaiting a regulatory decision"),
    dict(name="Trellis Software", sector="enterprise software",
         rev_growth="19% a year, decelerating from 28%", margin="operating margin 4%",
         valuation="7x forward revenue", debt="net cash",
         note="net revenue retention 108%, down from 119%"),
    dict(name="Marrow Foods", sector="packaged food",
         rev_growth="3% a year", margin="operating margin 11%, flat",
         valuation="15x forward earnings, below its sector",
         debt="net debt 2.6x EBITDA", note="private label competition rising"),
    dict(name="Aperture Semiconductor", sector="analog semiconductors",
         rev_growth="9% a year, cyclical", margin="gross margin 52%",
         valuation="22x forward earnings", debt="net debt 0.8x EBITDA",
         note="inventory at distributors above normal"),
    dict(name="Linwood Bancorp", sector="regional banking",
         rev_growth="net interest income up 5%", margin="return on equity 11%",
         valuation="1.1x tangible book value", debt="CET1 ratio 11.8%",
         note="commercial real estate is 21% of the loan book"),
    dict(name="Verdant Utilities", sector="regulated electric utility",
         rev_growth="4% rate base growth", margin="allowed return on equity 9.6%",
         valuation="17x forward earnings", debt="net debt 5.1x EBITDA",
         note="a rate case is pending"),
    dict(name="Oriole Retail", sector="specialty retail",
         rev_growth="same store sales up 2%", margin="operating margin 7%, down from 9%",
         valuation="12x forward earnings", debt="net debt 1.9x EBITDA",
         note="store count flat, e-commerce 24% of sales"),
    dict(name="Keystone Aerospace", sector="aerospace components",
         rev_growth="8% a year", margin="operating margin 16%",
         valuation="24x forward earnings", debt="net debt 2.1x EBITDA",
         note="single largest customer is 31% of revenue"),
    dict(name="Halcyon Logistics", sector="freight and logistics",
         rev_growth="5% a year", margin="operating margin 8%",
         valuation="14x forward earnings", debt="net debt 2.3x EBITDA",
         note="spot freight rates have been falling for three quarters"),
    dict(name="Pinnacle Materials", sector="building materials",
         rev_growth="7% a year", margin="operating margin 19%",
         valuation="16x forward earnings", debt="net debt 1.6x EBITDA",
         note="demand is tied to housing starts"),
    dict(name="Sable Energy Services", sector="energy services",
         rev_growth="12% a year, cyclical", margin="operating margin 13%",
         valuation="9x forward earnings", debt="net debt 1.2x EBITDA",
         note="earnings swing with the rig count"),
]

# Used only by the brand-salience item, which is pre-registered as exploratory
# precisely because a real name brings outside knowledge with it.
REAL_TICKERS = ["AAPL", "KO", "JNJ", "PG", "CSCO", "VZ"]


def describe(c):
    """One fundamentals block, identical across the conditions of a pair."""
    return (
        f"Sector: {c['sector']}. "
        f"Revenue: {c['rev_growth']}. "
        f"Profitability: {c['margin']}. "
        f"Valuation: {c['valuation']}. "
        f"Balance sheet: {c['debt']}. "
        f"Note: {c['note']}."
    )
