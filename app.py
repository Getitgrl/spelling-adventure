import html
import random

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Spelling Adventure",
    page_icon="🪄",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DEFAULT_WORDS = [
    "disconnect",
    "disobey",
    "nondairy",
    "nonremovable",
    "nonstick",
    "rearrange",
    "refreeze",
    "uncooked",
    "unidentified",
    "untangle",
]

GAME_MODES = [
    "🔊 Hear It & Spell It",
    "🧩 Unscramble",
    "🔤 Missing Letters",
    "🎯 Pick the Correct Spelling",
]


# -------------------- Helpers --------------------
def normalize_words(raw):
    """Accept one word per line or comma-separated words; normalize and deduplicate."""
    words = []
    for item in raw.replace(",", "\n").splitlines():
        word = item.strip().lower()
        if word:
            words.append(word)
    return list(dict.fromkeys(words))


def speak(text):
    """Use the browser's built-in speech synthesis."""
    safe_text = (
        text.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\n", " ")
    )
    components.html(
        f"""
        <script>
        const msg = new SpeechSynthesisUtterance('{safe_text}');
        msg.rate = 0.78;
        msg.pitch = 1.0;
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(msg);
        </script>
        """,
        height=0,
    )


def scrambled_word(word):
    if len(word) < 2:
        return word

    letters = list(word)
    for _ in range(50):
        random.shuffle(letters)
        candidate = "".join(letters)
        if candidate != word:
            return candidate

    return word[::-1]


def masked_word(word):
    """Show roughly one-third of the letters, always including first and last."""
    if len(word) <= 2:
        return " ".join("_" for _ in word)

    visible = {0, len(word) - 1}
    target_visible = max(2, round(len(word) * 0.35))
    internal = list(range(1, len(word) - 1))
    random.shuffle(internal)

    for index in internal:
        if len(visible) >= target_visible:
            break
        visible.add(index)

    return " ".join(
        letter if index in visible else "_"
        for index, letter in enumerate(word)
    )


def make_misspellings(target, valid_words):
    """Create believable wrong spellings of the target without using another valid list word."""
    variants = set()
    vowels = "aeiou"

    # Swap adjacent letters.
    for i in range(len(target) - 1):
        if target[i] != target[i + 1]:
            chars = list(target)
            chars[i], chars[i + 1] = chars[i + 1], chars[i]
            variants.add("".join(chars))

    # Remove one internal letter.
    for i in range(1, max(1, len(target) - 1)):
        candidate = target[:i] + target[i + 1:]
        if candidate:
            variants.add(candidate)

    # Double one internal letter.
    for i in range(1, max(1, len(target) - 1)):
        variants.add(target[:i] + target[i] + target[i:])

    # Replace a vowel.
    for i, char in enumerate(target):
        if char in vowels:
            for replacement in vowels:
                if replacement != char:
                    variants.add(target[:i] + replacement + target[i + 1:])

    # A couple of prefix-style mistakes are especially useful for this week's list.
    common_prefixes = ("dis", "non", "re", "un")
    for prefix in common_prefixes:
        if target.startswith(prefix) and len(target) > len(prefix) + 1:
            base = target[len(prefix):]
            variants.add(prefix[:-1] + base)
            variants.add(prefix + prefix[-1] + base)

    variants.discard(target)
    variants = {
        candidate for candidate in variants
        if candidate
        and candidate not in valid_words
        and candidate != target
    }

    choices = list(variants)
    random.shuffle(choices)

    # Guaranteed fallback for unusual/custom words.
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    attempts = 0
    while len(choices) < 3 and attempts < 100:
        attempts += 1
        if not target:
            break
        index = random.randrange(len(target))
        replacement = random.choice(alphabet.replace(target[index], ""))
        candidate = target[:index] + replacement + target[index + 1:]
        if candidate != target and candidate not in valid_words and candidate not in choices:
            choices.append(candidate)

    # Final fallback for extremely short/custom input.
    while len(choices) < 3:
        candidate = target + random.choice("xyz")
        if candidate not in choices and candidate not in valid_words:
            choices.append(candidate)

    return choices[:3]


def choose_next_word():
    """Prioritize missed words while still cycling through the whole list."""
    words = st.session_state.words
    current = st.session_state.current_word

    if len(words) == 1:
        return words[0]

    candidates = [w for w in words if w != current]

    # Base weight of 1. Missed words get extra weight so they return more often.
    weights = [
        1 + min(st.session_state.review.get(w, 0), 4) * 2
        for w in candidates
    ]
    return random.choices(candidates, weights=weights, k=1)[0]


def clear_round_artifacts():
    for key in (
        "scramble_for",
        "scramble",
        "mask_for",
        "mask",
        "choices_for",
        "choices",
    ):
        st.session_state.pop(key, None)


def start_new_round():
    st.session_state.current_word = choose_next_word()
    st.session_state.round_id += 1
    st.session_state.feedback = ""
    st.session_state.checked = False
    clear_round_artifacts()


def reset_for_new_list(new_words):
    st.session_state.words = new_words
    st.session_state.current_word = random.choice(new_words)
    st.session_state.score = 0
    st.session_state.streak = 0
    st.session_state.best_streak = 0
    st.session_state.correct = 0
    st.session_state.missed = 0
    st.session_state.review = {}
    st.session_state.attempts_by_word = {}
    st.session_state.correct_by_word = {}
    st.session_state.round_id += 1
    st.session_state.feedback = ""
    st.session_state.checked = False
    clear_round_artifacts()


def record_correct():
    word = st.session_state.current_word
    st.session_state.score += 10
    st.session_state.streak += 1
    st.session_state.best_streak = max(
        st.session_state.best_streak,
        st.session_state.streak,
    )
    st.session_state.correct += 1
    st.session_state.attempts_by_word[word] = (
        st.session_state.attempts_by_word.get(word, 0) + 1
    )
    st.session_state.correct_by_word[word] = (
        st.session_state.correct_by_word.get(word, 0) + 1
    )
    st.session_state.feedback = "🎉 Correct! +10 points"
    st.session_state.checked = True


def record_wrong():
    word = st.session_state.current_word
    st.session_state.streak = 0
    st.session_state.missed += 1
    st.session_state.review[word] = st.session_state.review.get(word, 0) + 1
    st.session_state.attempts_by_word[word] = (
        st.session_state.attempts_by_word.get(word, 0) + 1
    )
    st.session_state.feedback = (
        f"💡 Almost! The correct spelling is **{word}**."
    )
    st.session_state.checked = True


def check_typed_answer(answer):
    if not answer.strip():
        st.warning("Type an answer first.")
        return
    if answer.strip().lower() == st.session_state.current_word:
        record_correct()
    else:
        record_wrong()


# -------------------- State --------------------
defaults = {
    "words": DEFAULT_WORDS.copy(),
    "score": 0,
    "streak": 0,
    "best_streak": 0,
    "correct": 0,
    "missed": 0,
    "review": {},
    "attempts_by_word": {},
    "correct_by_word": {},
    "round_id": 0,
    "current_word": None,
    "feedback": "",
    "checked": False,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

if st.session_state.current_word is None:
    st.session_state.current_word = random.choice(st.session_state.words)


# -------------------- Styling --------------------
st.markdown(
    """
    <style>
    /* Compact mobile-first page */
    .block-container {
        max-width: 760px;
        padding-top: 1rem;
        padding-bottom: 2rem;
    }

    h1 {
        margin-bottom: 0.15rem !important;
        line-height: 1.05 !important;
    }

    [data-testid="stCaptionContainer"] {
        margin-bottom: .25rem;
    }

    /* Keep the score bar horizontal even on narrow phones */
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: .45rem;
        margin: .8rem 0 1rem 0;
    }

    .stat-card {
        background: rgba(127, 127, 127, .10);
        border: 1px solid rgba(127, 127, 127, .18);
        border-radius: 14px;
        padding: .55rem .2rem;
        text-align: center;
        min-width: 0;
    }

    .stat-label {
        font-size: .72rem;
        line-height: 1.05;
        opacity: .78;
        white-space: nowrap;
    }

    .stat-value {
        font-size: 1.35rem;
        font-weight: 800;
        line-height: 1.15;
        margin-top: .15rem;
    }

    .big-word {
        font-size: clamp(1.6rem, 7vw, 2.35rem);
        font-weight: 800;
        letter-spacing: .05rem;
        text-align: center;
        overflow-wrap: anywhere;
        padding: .35rem 0 .7rem 0;
    }

    /* Make game controls a little tighter on phones */
    div[data-testid="stVerticalBlock"] > div {
        gap: .45rem;
    }

    .stButton > button {
        min-height: 2.8rem;
        border-radius: 12px;
    }

    div[data-baseweb="select"] > div {
        border-radius: 12px;
    }

    /* The radio answer choices should be easy to tap */
    div[role="radiogroup"] label {
        padding: .22rem 0;
    }

    /* Avoid giant headings further down the page */
    h2, h3 {
        line-height: 1.15 !important;
    }

    @media (max-width: 480px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: .75rem;
        }

        h1 {
            font-size: 2.25rem !important;
        }

        .stat-label {
            font-size: .64rem;
        }

        .stat-value {
            font-size: 1.18rem;
        }

        .stats-grid {
            gap: .32rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -------------------- Header --------------------
st.title("🪄 Spelling Adventure")
st.caption("Practice, earn points, build a streak, and master every word.")

stats_html = f"""
<div class="stats-grid">
    <div class="stat-card">
        <div class="stat-label">⭐ Score</div>
        <div class="stat-value">{st.session_state.score}</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">🔥 Streak</div>
        <div class="stat-value">{st.session_state.streak}</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">✅ Correct</div>
        <div class="stat-value">{st.session_state.correct}</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">🏆 Best</div>
        <div class="stat-value">{st.session_state.best_streak}</div>
    </div>
</div>
"""
st.markdown(stats_html, unsafe_allow_html=True)


# -------------------- Parent setup --------------------
with st.sidebar:
    st.header("👩‍🏫 Parent Setup")
    st.caption("Change the spelling list here anytime.")

    raw_words = st.text_area(
        "Spelling words",
        value="\n".join(st.session_state.words),
        height=230,
        help="Enter one word per line, or separate words with commas.",
    )

    if st.button("Use This Word List", use_container_width=True):
        new_words = normalize_words(raw_words)
        if new_words:
            reset_for_new_list(new_words)
            st.success("New spelling list loaded.")
            st.rerun()
        else:
            st.error("Please enter at least one word.")

    if st.button("Reset Scores", use_container_width=True):
        st.session_state.score = 0
        st.session_state.streak = 0
        st.session_state.best_streak = 0
        st.session_state.correct = 0
        st.session_state.missed = 0
        st.session_state.review = {}
        st.session_state.attempts_by_word = {}
        st.session_state.correct_by_word = {}
        st.session_state.feedback = ""
        st.session_state.checked = False
        st.session_state.round_id += 1
        clear_round_artifacts()
        st.success("Scores reset.")
        st.rerun()

    st.divider()
    st.write(f"**Words loaded:** {len(st.session_state.words)}")

    if st.session_state.review:
        st.write("**Needs more practice:**")
        for word, count in sorted(
            st.session_state.review.items(),
            key=lambda item: (-item[1], item[0]),
        ):
            st.write(f"• {word} ({count} missed)")


# -------------------- Game --------------------
mode = st.selectbox("Choose a game", GAME_MODES)
word = st.session_state.current_word

with st.container(border=True):
    # Hear It & Spell It
    if mode == "🔊 Hear It & Spell It":
        st.subheader("Listen, then spell the word.")

        if st.button(
            "🔊 Hear the Word",
            use_container_width=True,
            disabled=st.session_state.checked,
        ):
            speak(word)

        answer = st.text_input(
            "Your spelling",
            key=f"hear_{st.session_state.round_id}",
            placeholder="Type the word here...",
            disabled=st.session_state.checked,
        )

        if st.button(
            "Check Answer",
            type="primary",
            use_container_width=True,
            key=f"check_hear_{st.session_state.round_id}",
            disabled=st.session_state.checked,
        ):
            check_typed_answer(answer)

    # Unscramble
    elif mode == "🧩 Unscramble":
        if (
            "scramble_for" not in st.session_state
            or st.session_state.scramble_for != word
        ):
            st.session_state.scramble_for = word
            st.session_state.scramble = scrambled_word(word)

        st.subheader("Unscramble the letters.")
        st.markdown(
            f'<div class="big-word">{html.escape(st.session_state.scramble)}</div>',
            unsafe_allow_html=True,
        )

        answer = st.text_input(
            "Your answer",
            key=f"scramble_{st.session_state.round_id}",
            placeholder="Type the correctly spelled word...",
            disabled=st.session_state.checked,
        )

        if st.button(
            "Check Answer",
            type="primary",
            use_container_width=True,
            key=f"check_scramble_{st.session_state.round_id}",
            disabled=st.session_state.checked,
        ):
            check_typed_answer(answer)

    # Missing Letters
    elif mode == "🔤 Missing Letters":
        if (
            "mask_for" not in st.session_state
            or st.session_state.mask_for != word
        ):
            st.session_state.mask_for = word
            st.session_state.mask = masked_word(word)

        st.subheader("Fill in the missing letters.")
        st.markdown(
            f'<div class="big-word">{html.escape(st.session_state.mask)}</div>',
            unsafe_allow_html=True,
        )

        answer = st.text_input(
            "Complete the word",
            key=f"mask_{st.session_state.round_id}",
            placeholder="Type the full word...",
            disabled=st.session_state.checked,
        )

        if st.button(
            "Check Answer",
            type="primary",
            use_container_width=True,
            key=f"check_mask_{st.session_state.round_id}",
            disabled=st.session_state.checked,
        ):
            check_typed_answer(answer)

    # Pick Correct Spelling
    else:
        st.subheader("Choose the correctly spelled word.")

        if (
            "choices_for" not in st.session_state
            or st.session_state.choices_for != word
        ):
            st.session_state.choices_for = word
            wrong_choices = make_misspellings(
                word,
                set(st.session_state.words),
            )
            choices = [word] + wrong_choices
            random.shuffle(choices)
            st.session_state.choices = choices

        selected = st.radio(
            "Pick one:",
            st.session_state.choices,
            index=None,
            key=f"choice_{st.session_state.round_id}",
            label_visibility="collapsed",
            disabled=st.session_state.checked,
        )

        if st.button(
            "Check Answer",
            type="primary",
            use_container_width=True,
            key=f"check_choice_{st.session_state.round_id}",
            disabled=st.session_state.checked,
        ):
            if selected is None:
                st.warning("Choose an answer first.")
            elif selected == word:
                record_correct()
            else:
                record_wrong()


# -------------------- Feedback / Next --------------------
if st.session_state.feedback:
    if st.session_state.feedback.startswith("🎉"):
        st.success(st.session_state.feedback)
        st.balloons()
    else:
        st.warning(st.session_state.feedback)

if st.session_state.checked:
    if st.button(
        "Next Word ➜",
        type="primary",
        use_container_width=True,
        key=f"next_{st.session_state.round_id}",
    ):
        start_new_round()
        st.rerun()


# -------------------- Progress --------------------
total_attempts = st.session_state.correct + st.session_state.missed
if total_attempts:
    accuracy = round(100 * st.session_state.correct / total_attempts)
    st.progress(
        accuracy / 100,
        text=f"Accuracy: {accuracy}% • {total_attempts} answered",
    )

with st.expander("📚 Show this week's words"):
    for spelling_word in st.session_state.words:
        attempts = st.session_state.attempts_by_word.get(spelling_word, 0)
        correct_count = st.session_state.correct_by_word.get(spelling_word, 0)
        misses = st.session_state.review.get(spelling_word, 0)

        if attempts == 0:
            icon = "⚪"
            label = "Not practiced yet"
        elif misses > 0:
            icon = "🔁"
            label = "Practice again"
        elif correct_count > 0:
            icon = "✅"
            label = "Correct"
        else:
            icon = "⚪"
            label = "Not practiced yet"

        st.write(f"{icon} **{spelling_word}** — {label}")
