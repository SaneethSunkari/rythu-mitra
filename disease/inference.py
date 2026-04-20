"""Disease image interpretation and farmer-facing reply generation."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.nizamabad_district import CROPS
from disease.model import DEFAULT_CLASS_NAMES, DiseaseModel


KVK_CONTACT_NUMBER = "08462-226360"
DEFINITIVE_THRESHOLD = 0.80
CAVEAT_THRESHOLD = 0.60
DISEASE_LABEL_MAP = {
    "paddy_blast": ("paddy", "blast"),
    "paddy_brown_spot": ("paddy", "brown_spot"),
    "paddy_blb": ("paddy", "blb"),
    "turmeric_rhizome_rot": ("turmeric", "rhizome_rot"),
    "turmeric_leaf_blotch": ("turmeric", "leaf_blotch"),
    "maize_fall_army_worm": ("maize", "fall_army_worm"),
    "maize_northern_leaf_blight": ("maize", "northern_leaf_blight"),
}


def interpret_confidence(score: float) -> str:
    """Map a model confidence score to a response tier."""

    if score >= DEFINITIVE_THRESHOLD:
        return "definitive"
    if score >= CAVEAT_THRESHOLD:
        return "caveat"
    return "refer_to_kvk"


def diagnose_disease_image(
    image_bytes: bytes,
    *,
    crop_hint: str | None = None,
    model: DiseaseModel | None = None,
) -> dict:
    inference_model = model or DiseaseModel(class_names=DEFAULT_CLASS_NAMES)
    prediction = inference_model.predict(image_bytes, crop_hint=crop_hint)
    quality = prediction.get("quality", {})

    if prediction["status"] == "poor_quality":
        reply = (
            "Photo clear ga ledu naanna. Leaf/mokka ni daylight lo దగ్గరగా okka photo mariyu full plant okka photo pampandi. "
            f"Urgent aithe KVK {KVK_CONTACT_NUMBER} ki call cheyyandi."
        )
        return {
            **prediction,
            "tier": "poor_quality",
            "reply_text": reply,
        }

    if prediction["status"] == "model_unavailable":
        reply = (
            "Photo vachesindi naanna, kani ee runtime lo trained disease weights load avvaledu. "
            f"Nenu guess cheyyatam correct kaadu. KVK {KVK_CONTACT_NUMBER} ki photo chupinchi confirm cheyyandi."
        )
        return {
            **prediction,
            "tier": "refer_to_kvk",
            "reply_text": reply,
        }

    label = prediction.get("predicted_label")
    crop_slug, disease_key = DISEASE_LABEL_MAP.get(label, (None, None))
    confidence = float(prediction.get("confidence", 0.0))
    tier = interpret_confidence(confidence)

    if not crop_slug or not disease_key:
        return {
            **prediction,
            "tier": "refer_to_kvk",
            "reply_text": (
                f"Photo chusanu naanna, kani exact class match clear ga raadhu. "
                f"KVK {KVK_CONTACT_NUMBER} ki okasari chupinchi confirm cheyyandi."
            ),
        }

    disease = CROPS[crop_slug].get("common_diseases", {}).get(disease_key, {})
    telugu_name = disease.get("telugu", disease_key.replace("_", " "))
    treatment = disease.get("treatment")
    cost = disease.get("cost_per_acre")

    if tier == "definitive":
        reply = (
            f"Naanna, photo batti idi {telugu_name} laga kanipisthundi. "
            f"Confidence approx {round(confidence * 100)}%. "
            f"Treatment: {treatment}. "
            f"Approx spray/drainage cost ₹{int(cost or 0):,}/acre."
        )
    elif tier == "caveat":
        reply = (
            f"Naanna, photo batti {telugu_name} chance undi kani nenu full ga confirm cheyyalenu "
            f"({round(confidence * 100)}% confidence). "
            f"Treatment side {treatment}. "
            f"Symptoms fast spread ayithe KVK {KVK_CONTACT_NUMBER} ki okasari chupinchandi."
        )
    else:
        reply = (
            f"Photo chusanu naanna, kani confidence {round(confidence * 100)}% matrame undi. "
            f"Guess cheyyatam correct kaadu. KVK {KVK_CONTACT_NUMBER} ki photo chupinchi confirm cheyyandi."
        )

    return {
        **prediction,
        "tier": tier,
        "crop": crop_slug,
        "disease_key": disease_key,
        "disease_telugu_name": telugu_name,
        "treatment": treatment,
        "cost_per_acre": cost,
        "reply_text": reply,
        "quality": quality,
    }
