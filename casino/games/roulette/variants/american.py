from typing import List
from time import sleep

from casino.types import GameContext
from casino.utils import clear_screen, cprint, cinput
from casino.accounts import Account
from casino.stats import display_stats, GameStats
from ..base import Roulette
from ..constants import (
    AMERICAN_HEADER_OPTIONS,
    AMERICAN_ROULETTE_TABLE,
    STANDARD_AMERICAN_ROULETTE_WHEEL,
)
from ..views import RouletteView


class AmericanRoulette(Roulette):
    """Plays roulette using American rules."""

    def __init__(self, accounts: List[Account]):
        super().__init__(accounts)
        self.wheel = STANDARD_AMERICAN_ROULETTE_WHEEL
        self.valid_numbers = [number for (number, _, _, _) in self.wheel]

        # Colors on wheel. Includes initials
        self.valid_colors = ["red", "green", "black", "r", "g", "b"]

        self.view = RouletteView(AMERICAN_HEADER_OPTIONS, AMERICAN_ROULETTE_TABLE)

    @staticmethod
    def normalize_color(input_value: str) -> str:
        """
        Standardize color input from user.

        `AmericanRoulette` permits the user to input a shorthand version of the color,
        or the name of the color itself. This function standardizes all colors to:

            "red", "green", "black"
        """
        color_map = {
            "r": "red",
            "red": "red",
            "g": "green",
            "green": "green",
            "b": "black",
            "black": "black"
        }
        return color_map.get(input_value.lower(), input_value)

    @staticmethod
    def normalize_type(input_value: str) -> str:
        """
        Standardize bet type from user.

        `AmericanRoulette` permits the user to input a shorthand version of the type of bet they want,
        or the name of the bet type itself. This function standardizes all bet types to:

            "color", "number"
        """
        type_map = {
            "c" : "color",
            "color" : "color",
            "n" : "number",
            "number" : "number"
        }
        return type_map.get(input_value.lower(), input_value)

    def submit_bets(self, ctx: GameContext) -> None | str:
        """
        Instruct users to submit bets.

        This function will ask users if they would like to submit a bet
        on a color or a number.

        - If users pick color, they can pick either red, green, or black
        - If users pick number, they can pick a number to bet on.
        """

        # Loop over all users
        i = 0
        while (i < len(self.accounts)):
            player_balances = 0
            for account in self.accounts:
                player_balances += account.balance
            
            if player_balances == 0:
                cprint("ERROR: All players have gone bankrupt. "
                      "You cannot play any more roulette.")
                sleep(3)
                return "BANKRUPT"

            if (self.accounts[i].balance == 0):
                cprint(f"Skipping player {i+1} because of empty balance...")
                i += 1
                continue

            will_bet = cinput(f"🤵: Would you like to bet, Player {i+1} (y/N): ")

            if will_bet == "" or will_bet.lower() in {"n", "no"}:
                cprint("User skipped betting. Moving to next user...", end="\n\n")
                i += 1
                continue
            elif will_bet.upper() == "Y" or will_bet.upper() == "YES":
                pass
            else:
                cprint("Invalid input. Enter either 'Y' for yes or 'N' for no.")
                continue

            clear_screen()
            self.view.display_topbar(ctx)
            # Input bet amount
            bet_amount = cinput(f"Player {i+1}'s Bet: ")

            # Check bet_amount is a positive integer
            try:
                bet_amount = int(bet_amount)

                if (bet_amount < 0):
                    raise ValueError
            except ValueError:
                cprint(f"ERROR: '{bet_amount}' is not a valid number. "
                      "Please enter a positive integer.", end="\n\n")
                continue

            # Check that account has enough money to bet
            try:
                self.accounts[i].withdraw(bet_amount)
            except ValueError as error:
                if error.args and error.args[0] == "Insufficient balance":
                    print("Insufficient balance to place bet. Please enter a "
                          f"bet less thanor equal to {self.accounts[i].balance}")
                continue

            clear_screen()
            self.view.display_topbar(ctx)
            cprint(f"Successfully withdrew {bet_amount} coins from Player {i+1}.")
            cprint(f"Player {i+1} remaining balance: "
                  f"{self.accounts[i].balance} coins.")

            # Ask for desired bet type
            bet_type = ""
            valid_bet_types = ["C", "COLOR", "N", "NUMBER"]

            while True:
                bet_type = cinput(
                    "🤵: Would you like to bet on a color or a number? (C or N): "
                ).strip()

                if (bet_type.upper() in valid_bet_types):
                    break
                else:
                    print("Error: Invalid bet type. "
                          "Choose either 'color' or 'number'.")

            clear_screen()
            self.view.display_topbar(ctx)

            ############################################################

            # Ask for user's specific bet
            bet_value = ""

            # Color betting
            if bet_type.lower() in {"c", "color"}:
                while True:
                    bet_value = cinput(
                        "Enter color you want to bet on (red, black, green): "
                    )
                    if bet_value.lower() in self.valid_colors:
                        break
                    else:
                        cprint("Error: Chosen color is not red, green, or black.")
            
            # Number betting
            elif bet_type.lower() in {"n", "number"}:
                while True:
                    cprint(AMERICAN_ROULETTE_TABLE)
                    bet_value = cinput("Enter number you would like to bet on: ")

                    if bet_value in self.valid_numbers:
                        break
                    else:
                        cprint("Error: You may only enter one of the following "
                              "numbers.")
                        sorted_numbers = sorted(self.valid_numbers,
                                                key=self.roulette_sort_key)
                        valid_numbers_str = ", ".join(sorted_numbers)
                        cprint("\t" + valid_numbers_str)
         
            # Once values are successfully chosen, save to dictionary
            account_id = str(self.accounts[i].aid)
            self.bets[account_id] = {
                "type"   : self.normalize_type(bet_type.lower()),
                "value"  : self.normalize_color(bet_value.lower()),
                "amount" : bet_amount
            }
            i += 1  # Move to next user

    def payout(self) -> None:
        """
        Pay out all players who picked the right color or number.
        """
        assert self.winning_value is not None
        winning_number = self.winning_value[0]
        winning_color  = self.winning_value[1]

        cprint("Paying out all winners...")
        # Loop over accounts (not bets) so each payout goes to the right player,
        # even if an earlier player skipped betting this round
        for i, account in enumerate(self.accounts):
            bet = self.bets.get(str(account.aid))
            if bet is None:
                continue

            bet_type   = bet["type"]
            bet_value  = bet["value"]
            bet_amount = bet["amount"]

            win_multiplier = 1
            # Check if user won
            if bet_type == "color" and bet_value == winning_color:
                if bet_value == "green":
                    win_multiplier += 35
                else:
                    # Find account and pay back two times original bet
                    win_multiplier += 1
            elif bet_type == "number" and bet_value == winning_number:
                # Find account and pay back 36 times original amount
                win_multiplier += 35

            if win_multiplier > 1:
                win_amount = bet_amount * win_multiplier
                account.deposit(win_amount)
                cprint(f"Player {i+1}: Won {win_amount} coins.")
            else:
                cprint(f"Player {i+1}: Lost {bet_amount} coins.")

        cprint("Finished payout.")


def play_roulette(context: GameContext) -> None:
    continue_game = True

    # Temporary fix
    # TODO: fix argument in play_roulette to only except `List[GameContext]`
    # and not `GameContext`
    contexts = [context]

    # Access account data
    accounts = [account.account for account in contexts]

    if not isinstance(accounts, list):
        raise ValueError("accounts is not a list. "
                         f"accounts is a {type(accounts)}")

    roulette = AmericanRoulette(accounts)
    stats = GameStats("American Roulette", context.account.balance)
    while continue_game:
        roulette.reset_round()
        clear_screen()
        roulette.view.display_topbar(context)

        # Input to stop loop from running constantly
        choice = cinput("Press [Enter] to start a new round and [q] to quit: ")

        if choice.lower() in {"q", "quit"}:
            continue_game = False
            break
        prev_balance = context.account.balance
        status = roulette.submit_bets(context)
        if status == "BANKRUPT":
            break

        roulette.spin_wheel(context)
        roulette.payout()
        if context.account.balance > prev_balance:
            stats.wins += 1
            stats.rounds_played += 1
        elif context.account.balance < prev_balance:
            stats.losses += 1
            stats.rounds_played += 1
        roulette.view.refresh_topbar(context)

        play_again = None

        while True:
            valid_choices = ["N", "NO", "Y", "YES", ""]
            play_again = cinput("🤵: Would you like to play another round (Y/n): ")

            if play_again.upper() not in valid_choices:
                cprint("Please enter 'Yes' or 'No'.")
                continue
            if play_again.lower() in {"n", "no"}:
                #cprint("Quitting roulette...")
                continue_game = False
                break
            elif play_again == "" or play_again.lower() in {"y", "yes"}:
                continue_game = True
                break
    stats.ending_balance = context.account.balance
    display_stats(stats)
    #cprint("Exiting roulette...")
    #sleep(0.5)
