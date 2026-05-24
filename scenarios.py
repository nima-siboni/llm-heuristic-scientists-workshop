"""Problem instances. Each scenario bundles a kitchen and a set of orders."""

from models.for_llm import STATION_CAPACITY
from models.infra   import Order, Scenario


TRAINING = Scenario(
    name    = "training",
    kitchen = dict(STATION_CAPACITY),
    orders  = [
        Order(id=1, arrival=0, due=25, dishes=["burger", "fries"]),
        Order(id=2, arrival=0, due=30, dishes=["steak",  "salad"]),
        Order(id=3, arrival=5, due=35, dishes=["pasta"]),
        Order(id=4, arrival=8, due=40, dishes=["burger", "salad"]),
    ],
)

HIDDEN_TEST = Scenario(
    name    = "hidden_test",
    kitchen = dict(STATION_CAPACITY),
    orders  = [
        Order(id=1, arrival= 0, due=22, dishes=["pasta",  "salad"]),
        Order(id=2, arrival= 0, due=28, dishes=["burger"]),
        Order(id=3, arrival= 3, due=30, dishes=["steak",  "fries", "salad"]),
        Order(id=4, arrival= 6, due=35, dishes=["soup"]),
        Order(id=5, arrival=10, due=45, dishes=["burger", "fries"]),
    ],
)

# Grill-heavy with tight deadlines — designed to punish bottleneck-blind heuristics.
STRESS = Scenario(
    name    = "stress",
    kitchen = dict(STATION_CAPACITY),
    orders  = [
        Order(id=1, arrival=0, due=22, dishes=["burger", "steak"]),
        Order(id=2, arrival=0, due=25, dishes=["steak",  "fries"]),
        Order(id=3, arrival=2, due=28, dishes=["burger"]),
        Order(id=4, arrival=4, due=32, dishes=["steak"]),
        Order(id=5, arrival=6, due=35, dishes=["burger", "salad"]),
    ],
)

ALL_SCENARIOS = [TRAINING, HIDDEN_TEST, STRESS]
