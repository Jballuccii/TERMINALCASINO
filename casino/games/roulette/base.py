import random
from abc import ABC, abstractmethod
from typing import List, Optional

from casino.types import GameContext
from casino.utils import cprint
from casino.accounts import Account
from .constants import TOTAL_ROTATIONS
from .views import RouletteView


class Roulette(ABC):
    """
    Abstract base class to play roulette.

    Only contains base functions to run roulette. To create a variant of
    roulette, inherit from this class, set `wheel`, `valid_numbers` and
    `view` in `__init__`, and implement `submit_bets()` and `payout()`.

    Attributes:
        wheel (list[tuple[str, str, int, int]]): The roulette wheel, where each
            entry is a tuple like ("0", "green", row, col).
        accounts (list[Account]): List of all player accounts.
        view (RouletteView): Draws the game in the terminal.
        bets (dict[str, dict[str, str, int]]): Maps each account UUID to a bet record.

        Each key is a unique account UUID, and each value is a dictionary with the fields:
            {
                "type": bet_type,
                "value": bet_value,
                "amount": bet_amount
            }

        Example:
            {
                "uuid_1": {"type": "color", "value": "red", "amount": 100},
                "uuid_2": {"type": "number", "value": "00", "amount": 50}
            }
    """
    view: RouletteView

    def __init__(self, accounts: List[Account]) -> None:
        """
        Initializes roulette
        """
        # Will be populated with numbers and colors
        self.wheel = list[tuple[str, str, int, int]]()
        self.valid_numbers = []

        self.accounts = accounts
        
        # Current round's bets
        self.bets = {}
        self.winning_value: Optional[tuple[str, str, int, int]] = None

    @staticmethod
    def roulette_sort_key(value : str) -> int:
        """
        Sorts values in roulette. Used as a key in the `sorted()` function.
        """
        if value == "0":
            return -1
        elif value == "00":
            return 0
        return int(value)

    def spin_wheel(self, ctx: GameContext) -> tuple[str, str, int, int]:
        """
        Pick a winning color and number.

        Returns:
            tuple[str, str]: A tuple containing:
                - str: The winning number (e.g., "28", "00", "0")
                - str: The winning color (either "red", "green", or "black")
        """

        random_index = random.randint(0, len(self.wheel) - 1)
        self.winning_value = self.wheel[random_index]

        wheel_sequence = [num for num, _, _, _ in self.wheel]

        # do TOTAL_ROTATIONS number of rotations before landing on number
        sequence = (wheel_sequence * TOTAL_ROTATIONS) + wheel_sequence[:random_index + 1]
        self.view.wheel_animation(ctx, self.wheel, sequence)

        winning_number = self.winning_value[0]
        winning_color  = self.winning_value[1]

        cprint(f"Winning number: {winning_number}")
        cprint(f"Winning color: {winning_color}")

        return self.winning_value

    def reset_round(self) -> None:
        self.bets.clear()
        self.winning_value = None

    @abstractmethod
    def submit_bets(self, ctx: GameContext) -> None | str:
        """
        Instruct users to submit bets.

        Returns "BANKRUPT" if every player is out of money.
        """
        pass

    @abstractmethod
    def payout(self) -> None:
        """
        Pay out all players who won their bet.
        """
        pass
