# asimov/playingcard/cards.py
"""
Shared playing card utilities.

Provides constants and card image loading for both detection
and floating card overlay modules.
"""

from typing import Optional

import os
import cv2
import numpy as np

from asimov.base.common import get_safe_path
from asimov.base import conf


# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUITS = ["hearts", "diamonds", "clubs", "spades"]

RANK_DISPLAY = {
    "A": "Ace", "2": "Two", "3": "Three", "4": "Four", "5": "Five",
    "6": "Six", "7": "Seven", "8": "Eight", "9": "Nine", "10": "Ten",
    "J": "Jack", "Q": "Queen", "K": "King"
}

RANK_FILENAME = {
    "A": "ace", "J": "jack", "Q": "queen", "K": "king"
}

SUIT_DISPLAY = {
    "hearts": "Hearts", "diamonds": "Diamonds",
    "clubs": "Clubs", "spades": "Spades"
}

SUIT_SYMBOLS = {
    "hearts": "♥", "diamonds": "♦", "clubs": "♣", "spades": "♠"
}


# ------------------------------------------------------------
# Path construction
# ------------------------------------------------------------

def get_card_path(rank: str, suit: str, basedir: Optional[str] = None, set_name: Optional[str] = None) -> str:
    """
    Get the full path to a card image file.

    Args:
        rank: Card rank (e.g., "A", "2", "10", "K")
        suit: Card suit (e.g., "hearts", "spades")
        basedir: Base directory (defaults to conf.PLAYINGCARD.BASEDIR)
        set_name: Card set name (defaults to conf.PLAYINGCARD.SET_NAME)

    Returns:
        Full path to the card PNG file
    """
    if basedir is None:
        basedir = conf.PLAYINGCARD.get("BASEDIR", "$HOME/projects/playingcarddata")
    if set_name is None:
        set_name = conf.PLAYINGCARD.get("SET_NAME", "bicycle")

    basedir = os.path.expandvars(os.path.expanduser(basedir))
    rank_name = RANK_FILENAME.get(rank, rank.lower())
    filename = f"{rank_name}_of_{suit}.png"

    return get_safe_path(basedir, "sets", set_name, filename)


def get_card_url(rank: str, suit: str) -> str:
    """
    Get a display-friendly URL or identifier for the card.
    """
    symbol = SUIT_SYMBOLS.get(suit, "?")
    return f"{rank}{symbol}"


# ------------------------------------------------------------
# Card image loading
# ------------------------------------------------------------

_card_cache = {}  # path -> RGBA image


def load_card_image(rank: str, suit: str, basedir: Optional[str] = None, set_name: Optional[str] = None) -> Optional[np.ndarray]:
    """
    Load a card image as RGBA numpy array.

    Args:
        rank: Card rank (e.g., "A", "2", "10", "K")
        suit: Card suit (e.g., "hearts", "spades")
        basedir: Base directory (defaults to conf.PLAYINGCARD.BASEDIR)
        set_name: Card set name (defaults to conf.PLAYINGCARD.SET_NAME)

    Returns:
        RGBA numpy array (H, W, 4), or None if not found
    """
    path = get_card_path(rank, suit, basedir, set_name)

    if path in _card_cache:
        return _card_cache[path]

    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        return None

    # Ensure RGBA
    if img.shape[2] == 3:
        alpha = np.full(img.shape[:2], 255, dtype=np.uint8)
        img = np.dstack((img, alpha))

    _card_cache[path] = img
    return img


def clear_cache():
    """Clear the card image cache."""
    global _card_cache
    _card_cache.clear()


def get_cache_size() -> int:
    """Return number of cached card images."""
    return len(_card_cache)


# ------------------------------------------------------------
# Validation
# ------------------------------------------------------------

def is_valid_rank(rank: str) -> bool:
    """Check if rank is valid."""
    return rank in RANKS


def is_valid_suit(suit: str) -> bool:
    """Check if suit is valid."""
    return suit in SUITS


def is_valid_card(rank: str, suit: str) -> bool:
    """Check if rank and suit combination is valid."""
    return is_valid_rank(rank) and is_valid_suit(suit)


def parse_card_string(card_str: str) -> tuple[str, str] | None:
    """
    Parse a card string like "queen_of_spades" or "Q♠" into (rank, suit).

    Returns:
        Tuple of (rank, suit) or None if invalid
    """
    card_str = card_str.lower().strip()

    # Try "rank_of_suit" format
    if "_of_" in card_str:
        parts = card_str.split("_of_")
        if len(parts) == 2:
            rank, suit = parts
            rank = rank.upper()
            if is_valid_card(rank, suit):
                return rank, suit

    # Try symbol format (e.g., "Q♠", "10♥")
    for rank in RANKS:
        for suit, symbol in SUIT_SYMBOLS.items():
            if card_str == f"{rank}{symbol}".lower():
                return rank, suit

    return None
