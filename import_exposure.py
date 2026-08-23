import pandas as pd


# ============================================================
# INDIA IMPORT EXPOSURE MODEL
# ============================================================

print("Loading India import exposure model...")


# ------------------------------------------------------------
# IMPORT SECTOR EXPOSURE
# ------------------------------------------------------------
# Exposure score:
# 0   = very low exposure
# 100 = very high exposure
#
# These are intentionally rule-based and interpretable.
# They can later be replaced with official trade-share data.
# ------------------------------------------------------------

IMPORT_EXPOSURE = {
    "Energy": {
        "exposure": 90,
        "description": "High dependence on imported crude oil, petroleum and gas."
    },

    "Electronics": {
        "exposure": 75,
        "description": "Significant dependence on imported electronics and components."
    },

    "Fertilizers": {
        "exposure": 70,
        "description": "Import dependence for key fertilizer inputs."
    },

    "Critical Minerals": {
        "exposure": 65,
        "description": "Exposure to globally concentrated mineral supply chains."
    },

    "Machinery": {
        "exposure": 60,
        "description": "Dependence on imported industrial machinery and equipment."
    },

    "Pharmaceutical Inputs": {
        "exposure": 55,
        "description": "Exposure to imported pharmaceutical raw materials and intermediates."
    },

    "Food Commodities": {
        "exposure": 40,
        "description": "Moderate exposure to disruptions in selected food supply chains."
    },

    "Textiles": {
        "exposure": 30,
        "description": "Lower relative geopolitical import exposure."
    }
}


# ------------------------------------------------------------
# GEOPOLITICAL REGION → SECTOR CONNECTION
# ------------------------------------------------------------

REGION_SECTOR_WEIGHTS = {
    "Middle East": {
        "Energy": 1.00,
        "Food Commodities": 0.30
    },

    "Russia": {
        "Energy": 0.90,
        "Fertilizers": 0.80,
        "Critical Minerals": 0.60
    },

    "China": {
        "Electronics": 0.90,
        "Critical Minerals": 0.90,
        "Machinery": 0.80,
        "Pharmaceutical Inputs": 0.50
    },

    "Europe": {
        "Machinery": 0.70,
        "Pharmaceutical Inputs": 0.60,
        "Electronics": 0.40
    },

    "Africa": {
        "Critical Minerals": 0.80,
        "Food Commodities": 0.50
    },

    "United States": {
        "Electronics": 0.50,
        "Machinery": 0.70,
        "Pharmaceutical Inputs": 0.40
    }
}


# ------------------------------------------------------------
# RISK CATEGORY
# ------------------------------------------------------------

def risk_category(score):

    if score < 40:
        return "LOW"

    elif score < 70:
        return "MEDIUM"

    else:
        return "HIGH"


# ------------------------------------------------------------
# CALCULATE IMPORT RISK
# ------------------------------------------------------------

def calculate_import_risk(
    geopolitical_risk,
    region
):

    if region not in REGION_SECTOR_WEIGHTS:
        print(f"\nWarning: no sector mapping for {region}")
        return pd.DataFrame()

    results = []

    sector_weights = REGION_SECTOR_WEIGHTS[region]

    for sector, region_weight in sector_weights.items():

        exposure = IMPORT_EXPOSURE[sector]["exposure"]

        # Combine:
        #
        # geopolitical risk
        #        ×
        # sector exposure
        #        ×
        # regional relevance
        #
        # Normalized back to 0-100.

        import_risk = (
            geopolitical_risk
            * (exposure / 100)
            * region_weight
        )

        results.append({
            "sector": sector,
            "exposure": exposure,
            "geopolitical_risk": geopolitical_risk,
            "region_weight": region_weight,
            "import_risk": import_risk,
            "category": risk_category(import_risk),
            "description": IMPORT_EXPOSURE[sector]["description"]
        })

    return pd.DataFrame(results)


# ============================================================
# DEMO
# ============================================================

if __name__ == "__main__":

    # Current geopolitical risk coming from your
    # existing 60/40 GDELT + sentiment model.

    geopolitical_risk = 62.73

    region = "Middle East"

    print("\n==========================================")
    print("       INDIA IMPORT EXPOSURE")
    print("==========================================")

    print(f"Geopolitical Risk : {geopolitical_risk:.2f}")
    print(f"Region            : {region}")

    results = calculate_import_risk(
        geopolitical_risk,
        region
    )

    if not results.empty:

        print("\n------------------------------------------")
        print("         SECTOR IMPORT RISK")
        print("------------------------------------------")

        for _, row in results.iterrows():

            print(
                f"{row['sector']:<25} "
                f"{row['import_risk']:>6.2f} "
                f"{row['category']}"
            )

        print("\n------------------------------------------")
        print("              DETAILS")
        print("------------------------------------------")

        for _, row in results.iterrows():

            print(f"\n{row['sector']}")
            print(f"Risk       : {row['import_risk']:.2f}")
            print(f"Category   : {row['category']}")
            print(f"Exposure   : {row['exposure']}")
            print(f"Relevance  : {row['region_weight']:.2f}")
            print(f"Reason     : {row['description']}")