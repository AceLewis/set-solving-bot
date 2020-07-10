import itertools
import operator
import math
import time

from ppadb.client import Client
from PIL import Image
import numpy as np
import cv2
import win32api
import win32con
import pygetwindow as gw
from mss import mss


def shift_roi(roi, shift):
    """Shift the region of interest"""
    return tuple(map(operator.add, roi, shift+shift))


def find_shape(num):
    """Find the shape from the volume"""
    return APPROX_VOLUME[min(APPROX_VOLUME.keys(), key=lambda x: abs(x-num))]


def distance(colour_1, colour_2):
    """Find the 'distance' between two colours"""
    return math.sqrt(sum((x-y)**2 for x, y in zip(colour_1, colour_2)))


def find_closest_colour(input_colour):
    """Find the closest colour in the dictionary"""
    colours = list(COLOUR_DICT.keys())
    closest_colour = sorted(colours,
                            key=lambda colour: distance(colour, input_colour))[0]
    return COLOUR_DICT[closest_colour]


def isolate_background(image):
    """Function to isolate the background, assumes the background is white"""
    # Copy the thresholded image.
    floodfill_image = image.copy()

    h, w = floodfill_image.shape
    mask = np.zeros((h+2, w+2), np.uint8)

    cv2.floodFill(floodfill_image, mask, (0, 0), 255)
    # Get background from these two images
    return image | cv2.bitwise_not(floodfill_image)


def find_fill(fill_percentage):
    """Find the shape from the volume"""
    return APPROX_FILL[min(APPROX_FILL.keys(),
                           key=lambda x: abs(x-fill_percentage))]


def get_card(box):
    """Find details about the card"""
    grey_image = np.array(cv2.cvtColor(np.float32(box), cv2.COLOR_RGB2GRAY),
                          dtype='uint8')
    # Find the colour from the darkest pixel
    _, _, min_loc, _ = cv2.minMaxLoc(grey_image)
    colour_pixel = np.float32(box)[min_loc[1]][min_loc[0]][:3]
    colour_obtained = find_closest_colour(colour_pixel)
    # Threshold the image so white-ish pixels are seperated from all other
    _, thresh = cv2.threshold(grey_image, 240, 255, cv2.THRESH_BINARY_INV)
    # Get background
    background = isolate_background(thresh)
    # Look at strip in background to find the number of shapes from the number
    # of times it changes from black to white
    half_card_strip = background[int(background.shape[0]/2), :]
    number_of_shapes = int(sum(np.roll(half_card_strip, 1) != half_card_strip)/2)
    # Calculate the volume per shape and infer what shape it is
    volume_per_shape = np.sum(background == 255)/number_of_shapes
    shape = find_shape(volume_per_shape)
    # Find the volume inside the shape that is white and infer the fill
    volume_inside_per_shape = np.sum((background-thresh) == 255)/number_of_shapes
    percent_filled = volume_inside_per_shape/volume_per_shape
    fill = find_fill(percent_filled)

    return (number_of_shapes, colour_obtained, fill, shape)


def is_white(pixel):
    """Check if a pixel is white-ish"""
    return all(x > 240 for x in pixel)


def is_it_a_card(box):
    """Check if the image is a card by seeing if the top left pixel and
    bottom right are white."""
    box_size = box.size
    bottom_right = (box_size[0]-1, box_size[1]-1)
    return is_white(box.getpixel((0, 0))) and is_white(box.getpixel(bottom_right))


def is_it_a_deck(box_dict):
    """Check if a deck is on screen"""
    # It is a deck if there are a number of cards divisible by three
    # and the cards are in order. e.g 3 cards are not selected as
    # green but not matching
    cards_found = [is_it_a_card(box) for box in box_dict.values()]
    num_of_cards = sum(cards_found)
    is_a_deck = num_of_cards % 3 == 0 and all(cards_found[0:num_of_cards])
    return num_of_cards*is_a_deck


def get_cards(box_dict):
    """Get information about all the cards"""
    cards = []
    for box in box_dict.values():
        if not is_it_a_card(box):
            # All cards found
            break
        cards.append(get_card(box))
    return cards


def find_missing_card(card_1, card_2):
    """Find the missing card in the set"""
    # Make a set for all possibilities
    number_set = set(range(1, 4))
    colour_set = set(COLOUR_DICT.values())
    filled_set = set(APPROX_FILL.values())
    shape_set = set(APPROX_VOLUME.values())

    # Make set for both cards
    number_set_cards = set([card_1[0], card_2[0]])
    colour_set_cards = set([card_1[1], card_2[1]])
    filled_set_cards = set([card_1[2], card_2[2]])
    shape_set_cards = set([card_1[3], card_2[3]])

    # Find the smallest set;
    # If they are the same the smallest is the set of the cards.
    # If they are different then the smallest set is all possibilities minus the current set.
    matching_num = next(iter(min((number_set-number_set_cards, number_set_cards), key=len)))
    matching_colour = next(iter(min((colour_set-colour_set_cards, colour_set_cards), key=len)))
    matching_filled = next(iter(min((filled_set-filled_set_cards, filled_set_cards), key=len)))
    matching_shape = next(iter(min((shape_set-shape_set_cards, shape_set_cards), key=len)))

    return (matching_num, matching_colour, matching_filled, matching_shape)


def click_location(location):
    """Move to then click on the location"""
    # I do not use pyautogui because it is too slow
    x, y = int(location[0]), int(location[1])
    win32api.SetCursorPos((x, y))
    time.sleep(CLICK_DELAY)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)


def screen_shot_phone(phone_name):
    """Take a screenshot of the phone fromt he live feed from scrcpy
    it is probably best to use the --always-on-top flag."""
    phone_loc = gw.getWindowsWithTitle(phone_name)[0]
    with mss() as sct:
        # Remove the surrounding window to just get the phone screen
        scr = sct.grab({
            'left': phone_loc.left + 10,
            'top': phone_loc.top + 31,
            'width': phone_loc.width - 20,
            'height': phone_loc.height - 45
        })
    return Image.frombytes('RGB', scr.size, scr.bgra,
                           'raw', 'BGRX')


def phone_to_screen(phone_loc, phone_name):
    """Take phone location and convert to screen location"""
    a = gw.getWindowsWithTitle(phone_name)[0]
    return (phone_loc[0]+a.left+10, phone_loc[1]+a.top+31)


def play_the_game(phone_name):
    """Automatically plays the game, assumes cards are present"""
    for _ in range(MAX_NUMBER_OF_PAIRS):
        time.sleep(NEW_CARD_DELAY)
        for _ in range(30):
            pil_img = screen_shot_phone(phone_name)
            box_dict = {num: pil_img.crop(ROI_DICT[num])
                        for num in range(max_number_of_cards)}
            if is_it_a_deck(box_dict):
                break
            time.sleep(0.01)
        else:
            print('Found all cards')
            break

        cards = get_cards(box_dict)

        for card_1, card_2 in itertools.combinations(cards, 2):
            missing_card = find_missing_card(card_1, card_2)
            if missing_card in cards:
                click_location(CARD_CENTRE_DICT[cards.index(card_1)])
                click_location(CARD_CENTRE_DICT[cards.index(card_2)])
                click_location(CARD_CENTRE_DICT[cards.index(missing_card)])
                break


if __name__ == "__main__":
    # Delays, these are needed, you can lower them on faster systems
    # If this does not work due increase the delays.
    # If only one or two cards is selected from a set the CLICK_DELAY is too short.
    # If the game fails on starting the NEW_GAME_DELAY is stoo short. The new game the screen
    # takes longer to load before the cards are visisble.
    # If the it is clicking the wrong cards NEW_CARD_DELAY is too low. This is because it is
    # taking a new screenshot before the input has been registered by the phone.
    CLICK_DELAY = 0.02
    NEW_GAME_DELAY = 0.02
    NEW_CARD_DELAY = 0.03
    number_of_games = 1

    max_number_of_cards = 21  # This is the maximum number of cards that can be shown
    MAX_NUMBER_OF_PAIRS = 27  # 81/3
    # Using names from Wikipedia
    APPROX_FILL = {0: 'solid',
                   0.5: 'open',
                   0.1: 'striped'}

    # These values will change on other phone screen sizes
    size_modifyer = 0.56
    APPROX_VOLUME = {2500*size_modifyer: 'diamond',
                     3300*size_modifyer: 'squiggle',
                     4300*size_modifyer: 'oval'}

    COLOUR_DICT = {(98, 37, 142): 'purple',
                   (231, 3, 7): 'red',
                   (3, 96, 56): 'green'}

    # Connect to the phone
    adb = Client(host='127.0.0.1', port=5037)
    devices = adb.devices()

    if not devices:
        raise Exception('No device attached.')

    device = devices[0]

    my_phone_name = device.get_properties()['ro.product.model']

    if not gw.getWindowsWithTitle(my_phone_name):
        raise Exception('Connect phone via scrcpy.')

    # Get bounding box for the first card. Shift this for all other cards
    top_left_card = (4, 123, 170, 211)
    # Distance between cards in pixels
    right = 177
    down = 98

    ROI_DICT = {num: shift_roi(top_left_card, [(num % 3)*right, math.floor(num/3)*down])
                for num in range(max_number_of_cards)}
    CARD_CENTRE_DICT = {i: phone_to_screen((sum(j[0::2])/2, sum(j[1::2])/2), my_phone_name)
                        for i, j in ROI_DICT.items()}

    restart_location = phone_to_screen((80, 840), my_phone_name)
    start_location = phone_to_screen((250, 505), my_phone_name)  # Find all
    # start_location = phone_to_screen((250, 600), my_phone_name)  # Find 10
    click_location(start_location)

    for game_number in range(number_of_games):
        play_the_game(my_phone_name)
        if game_number != number_of_games - 1:
            click_location(restart_location)
