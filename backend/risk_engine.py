# risk_engine.py
# Calculates the overall prototype risk level from the current zone states.
# All inputs are simulated — this is NOT a validated collision-prediction system.

from typing import Optional

# Ordered from least to most severe
RISK_ORDER = ["SAFE", "WARNING", "DANGER", "CRITICAL"]


def compute_overall_status(zone_risk_levels: list[str]) -> str:
    """
    Return the highest risk level present across all zones.

    Example:
        compute_overall_status(["SAFE", "WARNING", "DANGER"])  -> "DANGER"
        compute_overall_status(["SAFE", "SAFE", "SAFE"])       -> "SAFE"
    """
    if not zone_risk_levels:
        return "SAFE"

    highest = "SAFE"
    for level in zone_risk_levels:
        if RISK_ORDER.index(level) > RISK_ORDER.index(highest):
            highest = level

    return highest


def zone_risk_from_event(event: dict) -> str:
    """
    Extract the risk level string from a detector event dict.
    Defaults to SAFE if the key is missing or invalid.
    """
    risk = event.get("risk", "SAFE")
    return risk if risk in RISK_ORDER else "SAFE"


def build_status_summary(zones: list[dict]) -> dict:
    """
    Given a list of zone state dicts (from CameraManager),
    return a summary dict that includes the overall status and per-zone info.

    This is what GET /api/status returns.
    """
    risk_levels = [z.get("risk_level", "SAFE") for z in zones]
    overall = compute_overall_status(risk_levels)

    return {
        "overall_status": overall,
        "active_zones":   sum(1 for z in zones if z.get("status") == "connected"),
        "detection_count": sum(1 for z in zones if z.get("detected_object") is not None),
        "zones": {
            z["id"]: {
                "risk_level":      z.get("risk_level", "SAFE"),
                "detected_object": z.get("detected_object"),
                "confidence":      z.get("confidence"),
            }
            for z in zones
        },
        "source": "SIMULATED_BACKEND",
    }
