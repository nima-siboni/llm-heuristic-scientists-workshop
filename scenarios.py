"""Problem instances. Each scenario bundles a kitchen and a set of orders."""

from kitchen import DEFAULT_STATIONS


TRAINING = {
    "name":    "training",
    "kitchen": dict(DEFAULT_STATIONS),
    "orders": [
        {"id": 1, "arrival": 0, "due": 25, "dishes": ["burger", "fries"]},
        {"id": 2, "arrival": 0, "due": 30, "dishes": ["steak",  "salad"]},
        {"id": 3, "arrival": 5, "due": 35, "dishes": ["pasta"]},
        {"id": 4, "arrival": 8, "due": 40, "dishes": ["burger", "salad"]},
    ],
}

HIDDEN_TEST = {
    "name":    "hidden_test",
    "kitchen": dict(DEFAULT_STATIONS),
    "orders": [
        {"id": 1, "arrival":  0, "due": 22, "dishes": ["pasta",  "salad"]},
        {"id": 2, "arrival":  0, "due": 28, "dishes": ["burger"]},
        {"id": 3, "arrival":  3, "due": 30, "dishes": ["steak",  "fries", "salad"]},
        {"id": 4, "arrival":  6, "due": 35, "dishes": ["soup"]},
        {"id": 5, "arrival": 10, "due": 45, "dishes": ["burger", "fries"]},
    ],
}

# Grill-heavy with tight deadlines — designed to punish bottleneck-blind heuristics.
STRESS = {
    "name":    "stress",
    "kitchen": dict(DEFAULT_STATIONS),
    "orders": [
        {"id": 1, "arrival": 0, "due": 22, "dishes": ["burger", "steak"]},
        {"id": 2, "arrival": 0, "due": 25, "dishes": ["steak",  "fries"]},
        {"id": 3, "arrival": 2, "due": 28, "dishes": ["burger"]},
        {"id": 4, "arrival": 4, "due": 32, "dishes": ["steak"]},
        {"id": 5, "arrival": 6, "due": 35, "dishes": ["burger", "salad"]},
    ],
}

ALL_SCENARIOS = [TRAINING, HIDDEN_TEST, STRESS]
