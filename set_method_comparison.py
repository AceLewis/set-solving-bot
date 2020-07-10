import itertools
import random
import timeit
from statistics import mean

import matplotlib.pyplot as plt
import numpy as np


def random_deck():
    """Return a randomly shuffled deck"""
    all_cards = list(itertools.product(range(3), repeat=4))
    random.shuffle(all_cards)
    return all_cards


def random_cards(num):
    """Returns the first 'num' cards of a shuffled deck"""
    return random_deck()[:num]


def is_set(three_cards):
    """Checks if three cards form a valid set, they are if there are 1 or 3
    different things for each property so if the set length is 2 then it
    is not valid."""
    return all(len(set(x)) != 2 for x in zip(*three_cards))


def find_set_brute_force_all(cards):
    """Finds all valid sets using brute force"""
    return tuple(cards for cards in itertools.combinations(cards, 3) if is_set(cards))


def find_set_brute_force(cards):
    """Finds the first valid set using brute force"""
    return next(cards for cards in itertools.combinations(cards, 3) if is_set(cards))


def find_missing_card(card_1, card_2):
    """Find the missing card, any two cards in the deck has once card that
    it matches with. this finds that card."""
    return tuple(next(iter((set(x), set(range(3))-x)[len(x)-1]))
                 for x in map(set, zip(card_1, card_2)))


def find_set_missing_method_all(cards):
    """Find the all the sets using the find missing card method"""
    sets = []
    for card_1, card_2 in itertools.combinations(cards, 2):
        missing_card = find_missing_card(card_1, card_2)
        if missing_card in cards:
            card_set = set((card_1, card_2, missing_card,))
            if card_set not in sets:
                sets.append(card_set)
    return tuple(map(tuple, sets))


def find_set_missing_method(cards):
    """Find the first set using the find missing card method"""
    for card_1, card_2 in itertools.combinations(cards, 2):
        missing_card = find_missing_card(card_1, card_2)
        if missing_card in cards:
            return (card_1, card_2, missing_card,)
    # If no sets found return None
    return None


def get_cards_with_a_set(number_of_cards):
    """Get random cards that have a valid set in them"""
    while True:
        cards = random_cards(number_of_cards)
        # find_set_missing_method returns None when no set is there
        if find_set_missing_method(cards):
            return cards


def time_method(method, num_of_cards):
    """Return the time for the method"""
    some_cards = get_cards_with_a_set(num_of_cards)
    # After you have the cards then time the method
    starttime = timeit.default_timer()
    method(some_cards)
    return timeit.default_timer() - starttime


def avg_time_method(method, num_of_cards, num_of_attempts):
    """Return the average time for the method"""
    return mean(time_method(method, num_of_cards) for _ in range(num_of_attempts))


def avg_time_range(test_range, method, num_of_attempts):
    """Get the average time over the range for the method"""
    return [avg_time_method(method, x, num_of_attempts) for x in test_range]


num_of_attempts = 10000
# Test range 1 to 18. 21 cards can be shown but the probability very low.
test_range = range(3, 19)
plot_name = f"brute_force_vs_missing_4_{num_of_attempts}"

# Get the average time for both methods
brute_force = np.array(avg_time_range(test_range, find_set_brute_force, num_of_attempts))
missing_method = np.array(avg_time_range(test_range, find_set_missing_method, num_of_attempts))

# Plot the data
fig, ax = plt.subplots()
# I am using milliseconds because the time taken is very fast
line_1, = ax.plot(test_range, brute_force*1000)
line_1.set_label('Brute force method')
line_2, = ax.plot(test_range, missing_method*1000)
line_2.set_label('Missing method')


ax.legend()
ax.set(xlabel='Number of cards', ylabel='Average time (ms)',
       title=f'Average time taken to find a set vs number of cards')
ax.grid()
plt.savefig(f'{plot_name}.png', dpi=300)
plt.savefig(f'{plot_name}_transparent.png', dpi=300, transparent=True)
plt.savefig(f'{plot_name}.svg', dpi=300)
plt.savefig(f'{plot_name}_transparent.svg', dpi=300, transparent=True)
# plt.show()