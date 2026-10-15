# camera_manager.py
# OmniScan Phase 3
#
# Manages zone state for all four OmniScan camera zones.
# Phase 3 adds:
#   - A `mode` field per zone ("simulated" | "real")
#   - Helper to update the FRONT zone from a YOLO detection result
#   - A `source` field that is "YOLO_REAL" for the webcam zone
#
# The three non-FRONT zones remain simulated throughout Phase 3.

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


ZONES = ["FRONT", "REAR", "LEFT", "RIGHT"]

ZONE_LABELS = {
    "FRONT": "Front Camera",
    "REAR":  "Rear Camera",
    "LEFT":  "Left Camera",
    "RIGHT": "Right Camera",
}


@dataclass
class CameraZone:
    """
    Represents the current state of one camera zone.
    In Phase 3, FRONT can be "real" (webcam + YOLO) while the others stay
    "simulated".
    """
    id: str
    label: str
    status: str = "connected"           # "connected" | "disconnected"
    risk_level: str = "SAFE"            # SAFE | WARNING | DANGER | CRITICAL
    detected_object: Optional[str] = None
    confidence: Optional[int] = None
    last_detection_time: Optional[str] = None
    source: str = "SIMULATED_BACKEND"   # "SIMULATED_BACKEND" | "YOLO_REAL"
    mode: str = "simulated"             # "simulated" | "real"
    # Phase 3 extras (only populated for the FRONT/real zone)
    detections: list = field(default_factory=list)  # raw YOLO detection list
    frame_width: int = 640
    frame_height: int = 480

    def to_dict(self) -> dict:
        """Return a plain dictionary suitable for JSON serialisation."""
        return {
            "id":                  self.id,
            "label":               self.label,
            "status":              self.status,
            "risk_level":          self.risk_level,
            "detected_object":     self.detected_object,
            "confidence":          self.confidence,
            "last_detection_time": self.last_detection_time,
            "source":              self.source,
            "mode":                self.mode,
            "detections":          self.detections,
            "frame_width":         self.frame_width,
            "frame_height":        self.frame_height,
        }


class CameraManager:
    """
    Holds the current state of all four camera zones.
    Provides methods to read and update individual zones.
    """

    def __init__(self):
        # Build initial state for all zones
        self._zones: dict[str, CameraZone] = {
            zone_id: CameraZone(id=zone_id, label=ZONE_LABELS[zone_id])
            for zone_id in ZONES
        }

    def get_all_zones(self) -> list[dict]:
        """Return a list of all zone states as dictionaries."""
        return [zone.to_dict() for zone in self._zones.values()]

    def get_zone(self, zone_id: str) -> Optional[dict]:
        """Return a single zone's state, or None if the ID is invalid."""
        zone = self._zones.get(zone_id.upper())
        return zone.to_dict() if zone else None

    def update_zone(
        self,
        zone_id: str,
        risk_level: str,
        detected_object: Optional[str],
        confidence: Optional[int],
    ) -> None:
        """
        Apply a simulated detection update to one zone.
        Called by the simulation loop inside main.py.
        Only affects zones that are in "simulated" mode.
        """
        zone = self._zones.get(zone_id.upper())
        if zone is None:
            return
        if zone.mode == "real":
            # Don't overwrite a real zone with simulated data
            return

        zone.risk_level      = risk_level
        zone.detected_object = detected_object
        zone.confidence      = confidence
        zone.source          = "SIMULATED_BACKEND"

        if detected_object:
            zone.last_detection_time = datetime.now().strftime("%I:%M:%S %p")

    def update_zone_from_yolo(self, yolo_result: dict) -> None:
        """
        Update the FRONT zone using a result dict produced by YOLODetector.detect().
        Only the FRONT zone can enter "real" mode in Phase 3.
        """
        zone = self._zones.get("FRONT")
        if zone is None:
            return

        zone.risk_level          = yolo_result.get("risk", "SAFE")
        zone.detected_object     = yolo_result.get("object")
        zone.confidence          = yolo_result.get("confidence")
        zone.source              = "YOLO_REAL"
        zone.mode                = "real"
        zone.detections          = yolo_result.get("detections", [])
        zone.status              = "connected"
        zone.frame_width         = yolo_result.get("frame_width", 640)
        zone.frame_height        = yolo_result.get("frame_height", 480)

        if zone.detected_object:
            zone.last_detection_time = yolo_result.get("timestamp", datetime.now().strftime("%I:%M:%S %p"))

    def set_front_mode(self, mode: str) -> None:
        """
        Switch the FRONT zone between "real" and "simulated" mode.
        Called when the user starts/stops webcam capture.
        """
        zone = self._zones.get("FRONT")
        if zone is None:
            return
        zone.mode   = mode
        zone.source = "YOLO_REAL" if mode == "real" else "SIMULATED_BACKEND"
        if mode == "simulated":
            # Clear YOLO-populated fields
            zone.risk_level      = "SAFE"
            zone.detected_object = None
            zone.confidence      = None
            zone.detections      = []

    def set_front_status(self, status: str) -> None:
        """Update the connection status of the FRONT zone."""
        zone = self._zones.get("FRONT")
        if zone:
            zone.status = status

    def reset_all(self) -> None:
        """Reset all zones back to their initial SAFE state."""
        for zone in self._zones.values():
            zone.risk_level      = "SAFE"
            zone.detected_object = None
            zone.confidence      = None
            zone.last_detection_time = None
            zone.mode            = "simulated"
            zone.source          = "SIMULATED_BACKEND"
            zone.detections      = []
