"""Recipes and station capacities.

A dish is a linear chain of tasks. Each task is (name, duration, required_station).
Within a dish, task[i] depends on task[i-1]. There are no cross-dish dependencies.
"""

DISHES = {
    "burger": [
        ("prep_patty",      3, "prep"),
        ("grill_patty",     8, "grill"),
        ("toast_bun",       2, "oven"),
        ("assemble_burger", 2, "plating"),
    ],
    "fries": [
        ("cut_potatoes", 3, "prep"),
        ("fry_potatoes", 5, "fryer"),
        ("season_fries", 1, "plating"),
    ],
    "salad": [
        ("chop_veg",    4, "prep"),
        ("mix_salad",   2, "prep"),
        ("plate_salad", 1, "plating"),
    ],
    "steak": [
        ("season_steak", 2,  "prep"),
        ("grill_steak",  12, "grill"),
        ("rest_steak",   5,  "waiting"),
        ("plate_steak",  2,  "plating"),
    ],
    "pasta": [
        ("boil_pasta",    8, "stove"),
        ("cook_sauce",    6, "stove"),
        ("combine_pasta", 2, "stove"),
        ("plate_pasta",   1, "plating"),
    ],
    "soup": [
        ("chop_veg_soup", 3,  "prep"),
        ("simmer_soup",   10, "stove"),
        ("plate_soup",    1,  "plating"),
    ],
}

# "waiting" represents passive steps (resting meat, cooling) — no chef occupied.
DEFAULT_STATIONS = {
    "prep":    2,
    "grill":   1,
    "oven":    1,
    "fryer":   1,
    "stove":   1,
    "plating": 1,
    "waiting": 99,
}
