from typing import List, Optional
from time import sleep

from casino.types import GameContext
from casino.utils import clear_screen, cprint, cinput
from casino.accounts import Account
from casino.stats import display_stats, GameStats
from ..base import Roulette
from ..constants import (
    EUROPEAN_HEADER_OPTIONS,
    EUROPEAN_ROULETTE_TABLE,
    STANDARD_EUROPEAN_ROULETTE_WHEEL,
    RED_NUMBERS,
    DOZENS,
    COLUMNS,
    MULTIPLIER_LOSS,
    MULTIPLIER_EVEN_MONEY,
    MULTIPLIER_TWO_TO_ONE,
    MULTIPLIER_STRAIGHT_UP,
)
from ..views import RouletteView


class EuropeanRoulette(Roulette):
    """Plays roulette using European rules."""

    def __init__(self, accounts: List[Account]):
        super().__init__(accounts)
        self.wheel = STANDARD_EUROPEAN_ROULETTE_WHEEL
        self.valid_numbers = [number for (number, _, _, _) in self.wheel]

        self.view = RouletteView(EUROPEAN_HEADER_OPTIONS, EUROPEAN_ROULETTE_TABLE)

    def spin_wheel(self, ctx: GameContext) -> tuple[str, str, int, int]:
        """
        Spin the wheel, then show the player what they bet on.
        """
        winning_value = super().spin_wheel(ctx)

        account_id = str(ctx.account.aid)
        bet = self.bets.get(account_id)
        if bet is None:
            cprint("Your bet: (none)")
        else:
            cprint(f"Your bet: {self._format_bet(bet)}")

        return winning_value

    def submit_bets(self, ctx: GameContext) -> None | str:
        """
        Instruct users to submit bets.

        This function will ask users if they would like to submit a bet
        on a color or a number.

        - If users pick color, they can pick either red or black
        - If users pick number, they can pick a number to bet on.
        """

        # Loop over all users
        player_index = 0
        while player_index < len(self.accounts):
            if self._all_players_bankrupt():
                cprint("🤵: All players have gone bankrupt. "
                       "You cannot play any more roulette.")
                sleep(3)
                return "BANKRUPT"

            if self.accounts[player_index].balance == 0:
                cprint(f"Skipping player {player_index + 1} because of empty balance...")
                player_index += 1
                continue

            will_bet = self.view.prompt_with_error(
                ctx=ctx,
                prompt=f"🤵: Would you like to bet, Player {player_index + 1} (y/N): ",
                validator=lambda a: a in {"", "y", "yes", "n", "no"},
                error_text="Invalid input. Enter either 'Y' for yes or 'N' for no.",
                render_table=False,
                transform=lambda s: s.strip().lower(),
            )

            if will_bet in {"", "n", "no"}:
                cprint("User skipped betting. Moving to next user...", end="\n\n")
                player_index += 1
                continue
            else:
                pass

            bet_amount = self._prompt_bet_amount(ctx, player_index)

            # Ask for desired bet type
            area = self._prompt_bet_area(ctx)

            clear_screen()
            self.view.display_topbar(ctx)

            # Color or number betting
            if area == "inside":
                bet_type = "inside_number"
                bet_value = self._prompt_inside_number(ctx)
            else:
                bet_type = self._prompt_outside_type(ctx)
                bet_value = self._prompt_outside_value(ctx, bet_type)

            # Once values are successfully chosen, save to dictionary
            self._save_bet(player_index, bet_type, bet_value, bet_amount)
            player_index += 1  # Move to next user

    def _all_players_bankrupt(self) -> bool:
        return sum(a.balance for a in self.accounts) == 0

    def _prompt_bet_amount(self, ctx: GameContext, player_index: int) -> int:
        """Ask for bet amount, validate it, withdraw it, and return the amount (or None on error)."""
        balance = self.accounts[player_index].balance

        raw = self.view.prompt_with_error(
            ctx=ctx,
            prompt=f"Player {player_index + 1}'s Bet: ",
            validator=lambda s: s.isdigit() and 0 < int(s) <= balance,
            error_text=f"Please enter a positive integer up to {balance}.",
            render_table=False,
            transform=lambda s: s.strip(),
        )

        bet_amount = int(raw)
        self.accounts[player_index].withdraw(bet_amount)

        self.view.render_header(ctx)
        return bet_amount

    def _prompt_bet_area(self, ctx: GameContext) -> str:
        """Return 'inside' or 'outside'."""
        ans = self.view.prompt_with_error(
            ctx=ctx,
            prompt="🤵: Choose your bet area: [I]nside (single number) / [O]utside: ",
            validator=lambda a: a in {"i", "inside", "o", "outside"},
            error_text="Choose 'I' for inside or 'O' for outside.",
            render_table=False,
            transform=lambda s: s.strip().lower(),
        )
        if ans in {"i", "inside"}:
            return "inside"
        else:
            return "outside"

    def _prompt_inside_number(self, ctx: GameContext) -> str:
        """Inside bet: straight-up number (0-36)."""
        return self.view.prompt_with_error(
            ctx=ctx,
            prompt="🤵: Enter number you would like to bet on: ",
            validator=lambda a: a in self.valid_numbers,
            error_text="Invalid number. Choose from 0-36",
            render_table=True,
            transform=lambda s: s.strip(),
        )

    def _prompt_outside_type(self, ctx: GameContext) -> str:
        """Return outside bet type identifier."""
        mapping = {
            "1": "outside_color",
            "2": "outside_parity",
            "3": "outside_highlow",
            "4": "outside_dozen",
            "5": "outside_column",
        }

        last_error = ""
        while True:
            self.view.render_outside_bets_menu(ctx)
            if last_error:
                cprint(last_error)

            choice = cinput("🤵: Choose option (1-5): ").strip()
            if choice in mapping:
                return mapping[choice]
            last_error = "Choose a number from 1 to 5."

    def _prompt_outside_value(self, ctx: GameContext, bet_type: str) -> str:
        """Prompt for the value of an outside bet."""
        if bet_type == "outside_color":
            ans = self.view.prompt_with_error(
                ctx=ctx,
                prompt="🤵: Choose color [R]ed / [B]lack: ",
                validator=lambda a: a in {"r", "red", "b", "black"},
                error_text="Choose red or black.",
                render_table=False,
                transform=lambda s: s.strip().lower(),
            )
            if ans in {"r", "red"}:
                return "red"
            else:
                return "black"

        if bet_type == "outside_parity":
            ans = self.view.prompt_with_error(
                ctx=ctx,
                prompt="🤵: Choose [O]dd / [E]ven: ",
                validator=lambda a: a in {"o", "odd", "e", "even"},
                error_text="Choose odd or even.",
                render_table=False,
                transform=lambda s: s.strip().lower(),
            )
            if ans in {"o", "odd"}:
                return "odd"
            else:
                return "even"

        if bet_type == "outside_highlow":
            ans = self.view.prompt_with_error(
                ctx=ctx,
                prompt="🤵: Choose [L]ow (1-18) / [H]igh (19-36): ",
                validator=lambda a: a in {"l", "low", "h", "high"},
                error_text="Choose low or high.",
                render_table=True,
                transform=lambda s: s.strip().lower(),
            )
            if ans in {"l", "low"}:
                return "low"
            else:
                return "high"

        if bet_type == "outside_column":
            ans = self.view.prompt_with_error(
                ctx=ctx,
                prompt="🤵: Choose column: [1]=1st [2]=2nd [3]=3rd: ",
                validator=lambda a: a in {"1", "2", "3"},
                error_text="Choose 1, 2, or 3.",
                render_table=True,
                transform=lambda s: s.strip().lower(),
            )
            return ans

        if bet_type == "outside_dozen":
            ans = self.view.prompt_with_error(
                ctx=ctx,
                prompt="🤵: Choose dozen: [1]=1-12 [2]=13-24 [3]=25-36: ",
                validator=lambda a: a in {"1", "2", "3"},
                error_text="Choose 1, 2, or 3.",
                render_table=True,
                transform=lambda s: s.strip().lower(),
            )
            return ans

        raise ValueError(f"Unknown outside bet type: {bet_type}")

    def _save_bet(self, player_index: int, bet_type: str, bet_value: str, bet_amount: int) -> None:
        account_id = str(self.accounts[player_index].aid)
        self.bets[account_id] = {
            "type": bet_type,
            "value": bet_value,
            "amount": bet_amount
        }

    def _format_bet(self, bet: dict) -> str:
        t = bet["type"]
        v = bet["value"]
        a = bet["amount"]

        if t == "inside_number":
            return f"{a} on number {v}"

        if t == "outside_color":
            return f"{a} on {v} (color)"

        if t == "outside_parity":
            return f"{a} on {v} (parity)"

        if t == "outside_highlow":
            return f"{a} on {v} (high/low)"

        if t == "outside_dozen":
            label = {"1": "1-12", "2": "13-24", "3": "25-36"}[v]
            return f"{a} on dozen {v} ({label})"

        if t == "outside_column":
            return f"{a} on column {v}"

        return f"{a} on {t}:{v}"

    def payout(self) -> None:
        assert self.winning_value is not None
        winning_number = self.winning_value[0]

        accounts_by_id = {
            str(a.aid): (a, index + 1)
            for index, a in enumerate(self.accounts)}

        cprint("Paying out all winners...")
        is_zero = (winning_number == "0")
        winning_int = None if is_zero else int(winning_number)
        for account_id, bet in self.bets.items():
            entry = accounts_by_id.get(account_id)
            if entry is None:
                continue

            account, player_number = entry
            bet_type = bet["type"]
            bet_value = bet["value"]
            bet_amount = bet["amount"]

            win_multiplier = self._compute_win_multiplier(
                bet_type=bet_type,
                bet_value=bet_value,
                winning_number=winning_number,
                winning_int=winning_int,
                is_zero=is_zero
            )

            if win_multiplier > 1:
                win_amount = bet_amount * win_multiplier
                account.deposit(win_amount)
                cprint(f"Player {player_number}: Won {win_amount} coins.")
            else:
                cprint(f"Player {player_number}: Lost {bet_amount} coins.")

        cprint("Finished payout.")

    def _compute_win_multiplier(self, bet_type: str, bet_value: str, winning_number: str,
                                winning_int: Optional[int], is_zero: bool) -> int:
        """
        Return total payout multiplier including stake return.
        - 1 means loss (stake not returned; it was already withdrawn)
        - 2 means even-money win (1:1 payout + stake)
        - 3 means 2:1 payout + stake
        - 36 means 35:1 payout + stake
        """
        # Inside: straight-up (35:1 payout)
        if bet_type == "inside_number":
            if bet_value == winning_number:
                return MULTIPLIER_STRAIGHT_UP
            return MULTIPLIER_LOSS

        # Outside bets lose on zero
        if is_zero or winning_int is None:
            return MULTIPLIER_LOSS

        n = winning_int

        if bet_type == "outside_color":
            if (bet_value == "red" and n in RED_NUMBERS) or (bet_value == "black" and n not in RED_NUMBERS):
                return MULTIPLIER_EVEN_MONEY
        elif bet_type == "outside_parity":
            if (bet_value == "odd" and n % 2 == 1) or (bet_value == "even" and n % 2 == 0):
                return MULTIPLIER_EVEN_MONEY
        elif bet_type == "outside_highlow":
            if (bet_value == "low" and 1 <= n <= 18) or (bet_value == "high" and 19 <= n <= 36):
                return MULTIPLIER_EVEN_MONEY
        elif bet_type == "outside_column":
            if n in COLUMNS[bet_value]:
                return MULTIPLIER_TWO_TO_ONE
        elif bet_type == "outside_dozen":
            if n in DOZENS[bet_value]:
                return MULTIPLIER_TWO_TO_ONE

        return MULTIPLIER_LOSS    # Unknown bet type (treat as loss)


def play_european_roulette(context: GameContext) -> None:
    # Temporary fix
    # TODO: fix argument in play_roulette to only except `List[GameContext]`
    # and not `GameContext`

    # Access account data
    accounts = [context.account]
    roulette = EuropeanRoulette(accounts)
    stats = GameStats("European Roulette", context.account.balance)
    while True:
        roulette.reset_round()
        roulette.view.render_header(context)

        # Input to stop loop from running constantly
        choice = cinput("Press [Enter] to start a new round and [q] to quit: ").strip().lower()

        if choice in {"q", "quit"}:
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

        # play again?
        play_again = cinput("🤵: Would you like to play another round (Y/n): ").strip().lower()
        if play_again in {"", "y", "yes"}:
            pass  # next round
        elif play_again in {"n", "no"}:
            break
        else:
            play_again = roulette.view.prompt_with_error(
                ctx=context,
                prompt="🤵: Would you like to play another round (Y/n): ",
                validator=lambda a: a in {"", "y", "yes", "n", "no"},
                error_text="Please enter 'Yes' or 'No'.",
                render_table=False,
                transform=lambda s: s.strip().lower(),
            )
            if play_again in {"n", "no"}:
                break
    stats.ending_balance = context.account.balance
    display_stats(stats)
