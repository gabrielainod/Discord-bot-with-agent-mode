"""Word games: Hangman, Wordle, Word Scramble, Trivia."""
from __future__ import annotations

import re
from typing import Optional

from ..core.types import Control, InvalidAction, ModalSpec, Option, Result, Select, ViewModel
from ..data import words as DATA
from ..render import boards as B
from ..render import theme as T
from .base import Game

ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
GREEN = (52, 211, 153)
YELLOW = (255, 199, 84)
GREY = (70, 80, 100)
RED = (248, 113, 113)


# ================================================================== HANGMAN 🪢
class Hangman(Game):
    key = "hangman"
    name = "Hangman"
    tagline = "Six mistakes and the rope wins"
    emoji = "🪢"
    rules = "Guess letters to reveal the hidden word. Six wrong letters and the round is lost — right letters keep your turn."
    MAX_LIVES = 6

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.word, self.hint = self.rng.choice(DATA.HANGMAN_WORDS)
        self.word = self.word.lower()
        self.guessed: set[str] = set()
        self.lives = self.MAX_LIVES
        self.turn_seat = 0
        self.done = False
        self.win_seat: Optional[int] = None
        self.reason = ""
        self.last_letter: Optional[str] = None
        self.last_good: Optional[bool] = None
        self.found = [0 for _ in self.players]

    def is_over(self) -> bool:
        return self.done

    def result(self) -> Optional[Result]:
        if not self.done:
            return None
        return Result(self.win_seat, self.reason)

    def _mask(self) -> str:
        return " ".join(ch.upper() if ch in self.guessed or not ch.isalpha() else "_" for ch in self.word)

    def status(self) -> str:
        if self.done:
            return self.reason
        return f"{self.pname(self.turn_seat)} to guess · {self.lives} lives"

    def prompt(self) -> str:
        return "Pick a letter. Correct letters keep your turn."

    def act(self, seat: int, action: str) -> str:
        if self.done:
            raise InvalidAction("Round over.")
        if seat != self.turn_seat:
            raise InvalidAction("Not your turn.")
        if not action.startswith("g") or len(action) < 2:
            raise InvalidAction("Pick a letter.")
        letter = action[1].lower()
        if not letter.isalpha() or len(letter) != 1:
            raise InvalidAction("Letters only.")
        if letter in self.guessed:
            raise InvalidAction(f"{letter.upper()} was already guessed.")
        self.guessed.add(letter)
        self.last_letter = letter
        if letter in self.word:
            self.last_good = True
            self.found[seat] += self.word.count(letter)
            if all(ch in self.guessed or not ch.isalpha() for ch in self.word):
                self.done, self.win_seat = True, seat
                self.reason = f"{self.pname(seat)} cracked the word “{self.word.upper()}”."
                return self.reason
            return f"{self.pname(seat)} found “{letter.upper()}”"
        self.last_good = False
        self.lives -= 1
        if self.lives <= 0:
            self.done = True
            self.win_seat = self.other(seat)
            self.reason = f"Six misses. The word was “{self.word.upper()}”."
            return f"{self.pname(seat)} misses — the rope wins"
        self.turn_seat = self.other(seat)
        return f"{self.pname(seat)} misses — {self.lives} lives left"

    def legal_actions(self, seat: int) -> list[str]:
        if self.done or seat != self.turn_seat:
            return []
        return [f"g{c}" for c in ALPHA.lower() if c not in self.guessed]

    def ai_action(self, seat: int, difficulty: int) -> Optional[str]:
        pool = [c for c in ALPHA.lower() if c not in self.guessed]
        if not pool:
            return None
        if difficulty >= 3:
            # choose the most frequent letter among words matching the pattern
            pattern = [c if c in self.guessed else None for c in self.word]
            freq: dict[str, int] = {}
            for w, _ in DATA.HANGMAN_WORDS:
                if len(w) != len(self.word):
                    continue
                if any(pattern[i] and w[i] != pattern[i] for i in range(len(w))):
                    continue
                if any(ch in self.guessed and ch not in self.word for ch in w):
                    continue
                for ch in set(w):
                    if ch not in self.guessed:
                        freq[ch] = freq.get(ch, 0) + 1
            if freq:
                return "g" + max(freq, key=lambda k: freq[k])
        common = "etaoinshrdlucmfwypvbgkjqxz"
        for c in common:
            if c in pool:
                return "g" + c
        return "g" + self.rng.choice(pool)

    def view(self, seat: int) -> ViewModel:
        free = [c for c in ALPHA if c.lower() not in self.guessed]
        sels = []
        if free and not self.done and seat == self.turn_seat:
            first = [c for c in free if c <= "M"]
            second = [c for c in free if c > "M"]
            if first:
                sels.append(Select("Letters A – M", [Option(f"g{c.lower()}", c) for c in first], row=0))
            if second:
                sels.append(Select("Letters N – Z", [Option(f"g{c.lower()}", c) for c in second], row=1))
        return self._self_view(seat, selects=sels)

    def draw(self, f) -> None:
        x0, y0, x1, y1 = f.board
        stages = self.MAX_LIVES - self.lives
        # gallows (kept inside its own column on the left)
        gx = x0 + 70
        gy = y0 + 250
        f.d.line((gx - 40, gy, gx + 70, gy), fill=(92, 74, 58), width=9)
        f.d.line((gx, gy, gx, y0 + 30), fill=(92, 74, 58), width=9)
        f.d.line((gx, y0 + 30, gx + 90, y0 + 30), fill=(92, 74, 58), width=9)
        f.d.line((gx + 90, y0 + 30, gx + 90, y0 + 62), fill=(120, 96, 70), width=5)
        hx, hy = gx + 90, y0 + 80
        ink = (232, 238, 248)
        if stages >= 1:
            f.d.ellipse((hx - 26, hy - 26, hx + 26, hy + 26), outline=ink, width=5)
        if stages >= 2:
            f.d.line((hx, hy + 26, hx, hy + 130), fill=ink, width=5)
        if stages >= 3:
            f.d.line((hx, hy + 50, hx - 38, hy + 90), fill=ink, width=5)
        if stages >= 4:
            f.d.line((hx, hy + 50, hx + 38, hy + 90), fill=ink, width=5)
        if stages >= 5:
            f.d.line((hx, hy + 130, hx - 34, hy + 172), fill=ink, width=5)
        if stages >= 6:
            f.d.line((hx, hy + 130, hx + 34, hy + 172), fill=ink, width=5)
        if stages >= 6:
            T.cross(f.d, (hx - 9, hy - 9), 6, (248, 113, 113), 2)
            T.cross(f.d, (hx + 9, hy - 9), 6, (248, 113, 113), 2)
            f.d.arc((hx - 12, hy + 4, hx + 12, hy + 20), 20, 160, fill=(248, 113, 113), width=3)

        # word slots
        wx = x0 + 230
        max_w = x1 - wx - 20
        n = len(self.word)
        slot_w = min(64, (max_w - (n - 1) * 10) / n)
        wy = y0 + 108
        for i, ch in enumerate(self.word):
            sx = wx + i * (slot_w + 10)
            box = (sx, wy, sx + slot_w, wy + slot_w * 1.25)
            revealed = ch in self.guessed
            f.d.rounded_rectangle(box, radius=10, fill=(30, 36, 50) if not revealed else (37, 58, 56),
                                  outline=(52, 62, 84) if not revealed else GREEN, width=2)
            if revealed:
                f.text(B.mid(box), ch.upper(), int(slot_w * 0.62), T.TEXT, bold=True, anchor="mm")
            elif self.done:
                f.text(B.mid(box), ch.upper(), int(slot_w * 0.62), (120, 60, 70), bold=True, anchor="mm")

        f.pill((wx, y0 + 46), f"HINT · {self.hint}", 15, fg=T.GOLD, bg=(46, 38, 22))
        # lives
        for i in range(self.MAX_LIVES):
            cx = wx + i * 30
            alive = i < self.lives
            T.disc(f.d, (cx + 10, y0 + 232), 10, (52, 211, 153) if alive else (58, 40, 46), shade=False)
        f.text((wx + self.MAX_LIVES * 30 + 6, y0 + 224), f"{self.lives} lives", 14, T.DIM, bold=True)

        # keyboard
        ky = y0 + 300
        kw = (x1 - x0 - 24) / 13
        for i, c in enumerate(ALPHA):
            row, col = divmod(i, 13)
            x = x0 + 12 + col * kw
            y = ky + row * (kw * 0.82 + 6)
            box = (x, y, x + kw - 6, y + kw * 0.82)
            if c.lower() in self.guessed:
                good = c.lower() in self.word
                fill = (32, 66, 56) if good else (56, 34, 40)
                fg = GREEN if good else (170, 96, 104)
                outline = GREEN if good else (120, 60, 70)
            else:
                fill, fg, outline = (30, 35, 48), T.MUTED, (44, 52, 70)
            f.d.rounded_rectangle(box, radius=7, fill=fill, outline=outline, width=1)
            f.text(B.mid(box), c, 15, fg, bold=True, anchor="mm")


# =================================================================== WORDLE 🟩
class Wordle(Game):
    key = "wordle"
    name = "Wordle"
    tagline = "Six guesses, shared secret"
    emoji = "🟩"
    rules = "Both players chase the same five-letter secret. Six guesses each, alternating turns. Green = right spot, yellow = wrong spot."
    TRIES = 6

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.secret = self.rng.choice(DATA.FIVE_LETTER).lower()
        self.guesses: list[list[str]] = [[] for _ in self.players]
        self.results: list[list[list[str]]] = [[] for _ in self.players]
        self.turn_seat = 0
        self.done = False
        self.win_seat: Optional[int] = None
        self.reason = ""

    def is_over(self) -> bool:
        return self.done

    def result(self) -> Optional[Result]:
        if not self.done:
            return None
        return Result(self.win_seat, self.reason)

    def status(self) -> str:
        if self.done:
            return self.reason
        left = self.TRIES - len(self.guesses[self.turn_seat])
        return f"{self.pname(self.turn_seat)} · {left} guesses left"

    def prompt(self) -> str:
        return "Tap Type guess and send a five-letter word."

    @staticmethod
    def score(guess: str, secret: str) -> list[str]:
        out = ["grey"] * 5
        pool = list(secret)
        for i in range(5):
            if guess[i] == secret[i]:
                out[i] = "green"
                pool[i] = None
        for i in range(5):
            if out[i] == "green":
                continue
            if guess[i] in pool:
                out[i] = "yellow"
                pool[pool.index(guess[i])] = None
        return out

    def act(self, seat: int, action: str) -> str:
        if self.done:
            raise InvalidAction("Round over.")
        if seat != self.turn_seat:
            raise InvalidAction("Not your turn.")
        word = action[1:].strip().lower() if action.startswith("g") else ""
        if not re.fullmatch(r"[a-z]{5}", word):
            raise InvalidAction("Five letters, A to Z only.")
        self.guesses[seat].append(word)
        res = self.score(word, self.secret)
        self.results[seat].append(res)
        if word == self.secret:
            self.done, self.win_seat = True, seat
            self.reason = f"{self.pname(seat)} cracked it in {len(self.guesses[seat])} guesses."
            return f"{self.pname(seat)} cracks the word: {word.upper()}"
        if all(len(g) >= self.TRIES for g in self.guesses):
            self.done = True
            self.win_seat = None
            self.reason = f"Out of guesses. The word was “{self.secret.upper()}”."
            return "Both players ran out of guesses"
        if len(self.guesses[seat]) < self.TRIES:
            pass
        self.turn_seat = self.other(seat)
        hits = sum(1 for r in res if r == "green")
        return f"{word.upper()} · {hits}/5 exact"

    def legal_actions(self, seat: int) -> list[str]:
        return []  # free text only

    def ai_action(self, seat: int, difficulty: int) -> Optional[str]:
        used = {g for gs in self.guesses for g in gs}
        scored = {g: self.score(g, self.secret) for g in used}
        cands = []
        for w in DATA.FIVE_LETTER:
            ok = True
            for g, res in scored.items():
                if self.score(g, w) != res:
                    ok = False
                    break
            if ok:
                cands.append(w)
        pool = cands or DATA.FIVE_LETTER
        if difficulty <= 2 and self.rng.random() < 0.35:
            return "g" + self.rng.choice(DATA.FIVE_LETTER)
        if difficulty >= 3 and cands:
            return "g" + cands[0]
        return "g" + self.rng.choice(pool)

    def view(self, seat: int) -> ViewModel:
        modal = None
        if not self.done and seat == self.turn_seat:
            modal = ModalSpec("g", "Your guess", "Five-letter word", "crane", "", 5, "Type guess", "⌨️", 0)
        return self._self_view(seat, modal=modal)

    def draw(self, f) -> None:
        x0, y0, x1, y1 = f.board
        tw = 46
        gap = 6
        n = len(self.players)
        total = n * (5 * tw + 4 * gap) + (n - 1) * 40
        start = (x0 + x1) / 2 - total / 2
        for s in range(n):
            gx = start + s * (5 * tw + 4 * gap + 40)
            p = self.players[s]
            active = (not self.done) and s == self.turn_seat
            f.text((gx, y0 - 2), p.short(14).upper(), 14, p.color if active else T.MUTED, bold=True)
            left = self.TRIES - len(self.guesses[s])
            f.text((gx + 5 * tw + 4 * gap, y0 - 2), f"{left} left", 12, T.DIM, bold=True, anchor="ra")
            for r in range(self.TRIES):
                for c in range(5):
                    tx = gx + c * (tw + gap)
                    ty = y0 + 26 + r * (tw + gap)
                    box = (tx, ty, tx + tw, ty + tw)
                    if r < len(self.guesses[s]):
                        letter = self.guesses[s][r][c].upper()
                        state = self.results[s][r][c]
                        col = {"green": GREEN, "yellow": YELLOW}.get(state, GREY)
                        f.d.rounded_rectangle(box, radius=8, fill=col, outline=col)
                        f.text(B.mid(box), letter, 24, (14, 18, 26), bold=True, anchor="mm")
                    else:
                        fill = (30, 36, 50) if r != len(self.guesses[s]) or not active else (36, 43, 60)
                        f.d.rounded_rectangle(box, radius=8, fill=fill, outline=(48, 57, 78), width=2)
                        if r == len(self.guesses[s]) and active:
                            f.d.rounded_rectangle(box, radius=8, outline=p.color, width=2)
        # keyboard strip
        ky = y1 - 26
        kw = (x1 - x0) / 26
        for i, ch in enumerate(ALPHA):
            state = "unused"
            for s in range(len(self.players)):
                for r, guess in enumerate(self.guesses[s]):
                    if ch.lower() in guess:
                        st = self.results[s][r][guess.index(ch.lower())]
                        if st == "green" or (st == "yellow" and state != "green"):
                            state = "green" if st == "green" else "yellow"
                        elif state == "unused":
                            state = "grey"
            col = {"green": GREEN, "yellow": YELLOW, "grey": (52, 60, 78), "unused": (28, 33, 45)}[state]
            box = (x0 + i * kw + 2, ky - 16, x0 + i * kw + kw - 2, ky + 16)
            f.d.rounded_rectangle(box, radius=5, fill=col)
            fg = (14, 18, 26) if state in ("green", "yellow") else (110, 122, 144)
            f.text(B.mid(box), ch, 14, fg, bold=True, anchor="mm")


# ========================================================== WORD SCRAMBLE 🔤
class Scramble(Game):
    key = "scramble"
    name = "Word Scramble"
    tagline = "Unscramble before your rival"
    emoji = "🔤"
    rules = "A word arrives scrambled with a hint. Type the answer to score. Wrong answers pass the turn — the word stays."
    ROUNDS_WORDS = 8

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.queue = self.rng.sample(DATA.SCRAMBLE_WORDS, min(self.ROUNDS_WORDS, len(DATA.SCRAMBLE_WORDS)))
        self.index = 0
        self.points = [0 for _ in self.players]
        self.turn_seat = 0
        self.done = False
        self.win_seat: Optional[int] = None
        self.solved: list[tuple[str, int]] = []
        self.attempts = 0
        self.last: Optional[tuple[str, int, bool]] = None

    @property
    def word(self) -> str:
        return self.queue[min(self.index, len(self.queue) - 1)][0]

    @property
    def hint(self) -> str:
        return self.queue[min(self.index, len(self.queue) - 1)][1]

    def scrambled(self) -> str:
        w = self.word
        letters = list(w)
        for _ in range(30):
            self.rng.shuffle(letters)
            if "".join(letters) != w:
                break
        return "".join(letters)

    def is_over(self) -> bool:
        return self.done

    def result(self) -> Optional[Result]:
        if not self.done:
            return None
        top = max(self.points)
        w = [i for i, v in enumerate(self.points) if v == top]
        if len(w) == 1:
            return Result(w[0], f"Words solved: {self.points[0]} – {self.points[1]}.")
        return Result(None, "Both unscrambled the same number of words.")

    def status(self) -> str:
        if self.done:
            return f"All words played · {self.points[0]}–{self.points[1]}"
        return f"{self.pname(self.turn_seat)} · word {self.index + 1}/{len(self.queue)}"

    def prompt(self) -> str:
        return "Tap Type answer and write the real word."

    def act(self, seat: int, action: str) -> str:
        if self.done:
            raise InvalidAction("All words played.")
        if seat != self.turn_seat:
            raise InvalidAction("Not your turn.")
        guess = (action[1:] if action.startswith("g") else action).strip().lower()
        if not guess:
            raise InvalidAction("Type a word.")
        self.attempts += 1
        correct = guess == self.word.lower()
        if correct:
            self.points[seat] += 1
            self.solved.append((self.word, seat))
            self.index += 1
            self.last = (self.word, seat, True)
            if self.index >= len(self.queue):
                self.done = True
                top = max(self.points)
                w = [i for i, v in enumerate(self.points) if v == top]
                self.win_seat = w[0] if len(w) == 1 else None
                return f"{self.pname(seat)} solves the last word"
            return f"{self.pname(seat)} unscrambles “{self.word.upper()}”"
        self.last = (guess, seat, False)
        self.turn_seat = self.other(seat)
        return f"{self.pname(seat)} misses “{guess.upper()}”"

    def ai_action(self, seat: int, difficulty: int) -> Optional[str]:
        if difficulty >= 4 or self.rng.random() < 0.55 + difficulty * 0.1:
            return "g" + self.word
        return "g" + self.scrambled()

    def view(self, seat: int) -> ViewModel:
        modal = None
        if not self.done and seat == self.turn_seat:
            modal = ModalSpec("g", "Unscramble", "Your answer", self.hint, "", 30, "Type answer", "⌨️", 0)
        return self._self_view(seat, modal=modal)

    def draw(self, f) -> None:
        x0, y0, x1, y1 = f.board
        sc = self.scrambled().upper()
        n = len(sc)
        tw = min(84, (708 - 40 - (n - 1) * 10) / n)
        total = n * tw + (n - 1) * 10
        sx = (x0 + x1) / 2 - total / 2
        ty = y0 + 60
        for i, ch in enumerate(sc):
            box = (sx + i * (tw + 10), ty, sx + i * (tw + 10) + tw, ty + tw * 1.2)
            f.d.rounded_rectangle(box, radius=12, fill=(35, 41, 58), outline=(62, 72, 96), width=2)
            f.d.rounded_rectangle((box[0] + 3, box[1] + 3, box[2] - 3, box[1] + 7), radius=3, fill=(56, 66, 90))
            f.text(B.mid(box), ch, int(tw * 0.55), T.TEXT, bold=True, anchor="mm")
        f.pill(((x0 + x1) / 2 - 70, ty + tw * 1.2 + 26), f"HINT · {self.hint}", 16, fg=T.GOLD, bg=(46, 38, 22))
        y = ty + tw * 1.2 + 92
        T.divider(f.d, x0 + 20, y, x1 - 20)
        y += 20
        f.text((x0 + 20, y), "SCORES", 13, T.DIM, bold=True)
        for i, p in enumerate(self.players):
            bx = x0 + 20 + i * 250
            f.d.rounded_rectangle((bx, y + 26, bx + 220, y + 74), radius=12, fill=T.CARD_LO, outline=p.color if i == self.turn_seat and not self.done else T.LINE_SOFT)
            f.text((bx + 14, y + 50), p.short(14), 15, T.MUTED, bold=True, anchor="lm")
            f.text((bx + 206, y + 50), str(self.points[i]), 24, T.TEXT, bold=True, anchor="rm")
        if self.solved:
            f.text((x0 + 20, y + 92), "SOLVED · " + ", ".join(w.upper() for w, _ in self.solved[-3:]), 12, (72, 84, 104), bold=True)


# ================================================================== TRIVIA 🧠
class Trivia(Game):
    key = "trivia"
    name = "Trivia"
    tagline = "Five questions, zero mercy"
    emoji = "🧠"
    rules = "Five questions, alternating turns. Pick the right answer to score. Most correct answers takes the round."
    max_players = 4
    N_QUESTIONS = 5

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.questions = self.rng.sample(DATA.TRIVIA, min(self.N_QUESTIONS, len(DATA.TRIVIA)))
        self.index = 0
        self.points = [0 for _ in self.players]
        self.turn_seat = 0
        self.done = False
        self.win_seat: Optional[int] = None
        self.last: Optional[tuple[int, int, bool]] = None

    @property
    def current(self):
        return self.questions[min(self.index, len(self.questions) - 1)]

    def is_over(self) -> bool:
        return self.done

    def result(self) -> Optional[Result]:
        if not self.done:
            return None
        top = max(self.points)
        w = [i for i, v in enumerate(self.points) if v == top]
        if len(w) == 1:
            return Result(w[0], f"Correct answers: {' – '.join(str(p) for p in self.points)}")
        return Result(None, "A tie on correct answers.")

    def status(self) -> str:
        if self.done:
            return "Final question answered"
        return f"{self.pname(self.turn_seat)} · question {self.index + 1}/{len(self.questions)}"

    def prompt(self) -> str:
        return "Tap the answer you believe."

    def act(self, seat: int, action: str) -> str:
        if self.done:
            raise InvalidAction("Quiz finished.")
        if seat != self.turn_seat:
            raise InvalidAction("Not your turn.")
        if not action.startswith("a") or not action[1:].isdigit():
            raise InvalidAction("Pick an option.")
        pick = int(action[1:])
        q, opts, answer = self.current
        if not 0 <= pick < len(opts):
            raise InvalidAction("No such option.")
        correct = pick == answer
        if correct:
            self.points[seat] += 1
        self.last = (seat, pick, correct)
        self.index += 1
        if self.index >= len(self.questions):
            self.done = True
            top = max(self.points)
            w = [i for i, v in enumerate(self.points) if v == top]
            self.win_seat = w[0] if len(w) == 1 else None
            return f"{self.pname(seat)} {'scores' if correct else 'misses'} — quiz over"
        self.turn_seat = self.other(seat)
        return f"{self.pname(seat)} answers {'correctly' if correct else 'wrong'}"

    def ai_action(self, seat: int, difficulty: int) -> Optional[str]:
        q, opts, answer = self.current
        if self.rng.random() < {1: 0.35, 2: 0.55, 3: 0.78, 4: 0.94}.get(difficulty, 0.55):
            return f"a{answer}"
        wrong = [i for i in range(len(opts)) if i != answer]
        return f"a{self.rng.choice(wrong)}"

    def view(self, seat: int) -> ViewModel:
        q, opts, answer = self.current
        btns = [Control(f"a{i}", f"{chr(65 + i)} · {o}"[:76], "", "primary", i) for i, o in enumerate(opts)]
        return self._self_view(seat, btns)

    def draw(self, f) -> None:
        x0, y0, x1, y1 = f.board
        q, opts, answer = self.current
        # question card
        box = (x0 + 10, y0 + 6, x1 - 10, y0 + 128)
        f.d.rounded_rectangle(box, radius=16, fill=(30, 36, 52), outline=(48, 58, 80), width=2)
        f.text((box[0] + 20, box[1] + 16), f"QUESTION {min(self.index + 1, len(self.questions))}", 12, T.DIM, bold=True)
        y = box[1] + 40
        for line in T.wrap(q, 24, box[2] - box[0] - 40, bold=True, max_lines=3):
            f.text((box[0] + 20, y), line, 24, T.TEXT, bold=True)
            y += 31
        # options
        oy = box[3] + 16
        oh = (y1 - oy - 10) / 4 - 8
        for i, opt in enumerate(opts):
            ob = (x0 + 10, oy + i * (oh + 8), x1 - 10, oy + i * (oh + 8) + oh)
            is_right = i == answer
            fill, outline, fg = (31, 37, 52), (46, 55, 76), T.TEXT
            if self.last:
                seat, pick, correct = self.last
                if is_right:
                    fill, outline, fg = (28, 62, 54), GREEN, (200, 255, 235)
                elif pick == i:
                    fill, outline, fg = (62, 34, 42), RED, (255, 200, 200)
            f.d.rounded_rectangle(ob, radius=12, fill=fill, outline=outline, width=2)
            f.d.rounded_rectangle((ob[0] + 10, ob[1] + (oh - 30) / 2, ob[0] + 40, ob[1] + (oh + 30) / 2), radius=8, fill=(44, 52, 72))
            f.text((ob[0] + 25, B.mid(ob)[1]), chr(65 + i), 17, T.MUTED, bold=True, anchor="mm")
            f.text((ob[0] + 54, B.mid(ob)[1]), T.ellipsize(opt, 19, ob[2] - ob[0] - 80), 19, fg, bold=True, anchor="lm")
