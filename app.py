
import random
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Spelling Adventure", page_icon="🪄", layout="centered")

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

# ---------- Helpers ----------
def normalize_words(raw):
    words = []
    for line in raw.replace(",", "\n").splitlines():
        w = line.strip().lower()
        if w:
            words.append(w)
    # preserve order, remove duplicates
    return list(dict.fromkeys(words))

def speak(text):
    safe = text.replace("\\", "\\\\").replace("'", "\\'")
    components.html(
        f"""
        <script>
        const msg = new SpeechSynthesisUtterance('{safe}');
        msg.rate = 0.82;
        msg.pitch = 1.0;
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(msg);
        </script>
        """,
        height=0,
    )

def masked_word(word):
    if len(word) <= 4:
        keep = {0, len(word)-1}
    else:
        keep = {0, len(word)-1}
        while len(keep) < max(2, len(word)//3):
            keep.add(random.randrange(1, len(word)-1))
    return " ".join(ch if i in keep else "_" for i, ch in enumerate(word))

def scrambled_word(word):
    letters = list(word)
    for _ in range(20):
        random.shuffle(letters)
        s = "".join(letters)
        if s != word:
            return s
    return "".join(reversed(word))

def new_round():
    st.session_state.current_word = random.choice(st.session_state.words)
    st.session_state.round_id += 1
    st.session_state.feedback = ""
    st.session_state.checked = False

def correct_answer():
    st.session_state.score += 10
    st.session_state.streak += 1
    st.session_state.best_streak = max(st.session_state.best_streak, st.session_state.streak)
    st.session_state.correct += 1
    st.session_state.feedback = "🎉 Correct! +10 points"
    st.session_state.checked = True

def wrong_answer():
    st.session_state.streak = 0
    st.session_state.missed += 1
    word = st.session_state.current_word
    st.session_state.review[word] = st.session_state.review.get(word, 0) + 1
    st.session_state.feedback = f"💡 Almost! The correct spelling is **{word}**."
    st.session_state.checked = True

# ---------- Session state ----------
defaults = {
    "words": DEFAULT_WORDS.copy(),
    "score": 0,
    "streak": 0,
    "best_streak": 0,
    "correct": 0,
    "missed": 0,
    "review": {},
    "round_id": 0,
    "current_word": None,
    "feedback": "",
    "checked": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

if st.session_state.current_word is None:
    st.session_state.current_word = random.choice(st.session_state.words)

# ---------- Styling ----------
st.markdown(
    """
    <style>
    .block-container {max-width: 760px; padding-top: 1.5rem;}
    .game-card {
        padding: 1.4rem;
        border: 2px solid rgba(120,120,120,.25);
        border-radius: 18px;
        margin: .8rem 0 1.2rem 0;
        text-align: center;
    }
    .big-word {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: .08rem;
    }
    .stat {
        text-align:center;
        padding:.5rem;
        border-radius:12px;
        background:rgba(120,120,120,.10);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🪄 Spelling Adventure")
st.caption("Practice, earn points, build a streak, and master every word.")

# ---------- Sidebar parent setup ----------
with st.sidebar:
    st.header("👩‍🏫 Parent Setup")
    raw_words = st.text_area(
        "Spelling words",
        value="\n".join(st.session_state.words),
        height=230,
        help="Enter one word per line, or separate words with commas.",
    )
    if st.button("Use This Word List", use_container_width=True):
        new_words = normalize_words(raw_words)
        if new_words:
            st.session_state.words = new_words
            st.session_state.current_word = random.choice(new_words)
            st.session_state.review = {}
            st.session_state.score = 0
            st.session_state.streak = 0
            st.session_state.best_streak = 0
            st.session_state.correct = 0
            st.session_state.missed = 0
            st.success("New spelling list loaded.")
        else:
            st.error("Please enter at least one word.")

    if st.button("Reset Scores", use_container_width=True):
        st.session_state.score = 0
        st.session_state.streak = 0
        st.session_state.best_streak = 0
        st.session_state.correct = 0
        st.session_state.missed = 0
        st.session_state.review = {}
        st.session_state.feedback = ""
        st.success("Scores reset.")

    st.divider()
    st.write(f"**Words loaded:** {len(st.session_state.words)}")
    if st.session_state.review:
        st.write("**Words to review:**")
        for w, n in sorted(st.session_state.review.items(), key=lambda x: (-x[1], x[0])):
            st.write(f"• {w} ({n})")

# ---------- Stats ----------
c1, c2, c3, c4 = st.columns(4)
c1.metric("⭐ Score", st.session_state.score)
c2.metric("🔥 Streak", st.session_state.streak)
c3.metric("✅ Correct", st.session_state.correct)
c4.metric("🏆 Best", st.session_state.best_streak)

mode = st.selectbox(
    "Choose a game",
    ["🔊 Hear It & Spell It", "🧩 Unscramble", "🔤 Missing Letters", "🎯 Pick the Correct Spelling"],
)

word = st.session_state.current_word
st.markdown('<div class="game-card">', unsafe_allow_html=True)

# ---------- Mode: Hear It ----------
if mode == "🔊 Hear It & Spell It":
    st.subheader("Listen carefully, then type the word.")
    col_a, col_b = st.columns([1,1])
    with col_a:
        if st.button("🔊 Hear the Word", use_container_width=True):
            speak(word)
    with col_b:
        if st.button("🔁 Hear It Again", use_container_width=True):
            speak(word)

    answer = st.text_input(
        "Your spelling",
        key=f"hear_{st.session_state.round_id}",
        placeholder="Type the word here...",
    )
    if st.button("Check Answer", type="primary", use_container_width=True, disabled=st.session_state.checked):
        if answer.strip().lower() == word:
            correct_answer()
        else:
            wrong_answer()

# ---------- Mode: Unscramble ----------
elif mode == "🧩 Unscramble":
    if "scramble_for" not in st.session_state or st.session_state.scramble_for != word:
        st.session_state.scramble_for = word
        st.session_state.scramble = scrambled_word(word)
    st.subheader("Unscramble the letters.")
    st.markdown(f'<div class="big-word">{st.session_state.scramble}</div>', unsafe_allow_html=True)
    answer = st.text_input(
        "Your answer",
        key=f"scramble_{st.session_state.round_id}",
        placeholder="Type the correctly spelled word...",
    )
    if st.button("Check Answer", type="primary", use_container_width=True, disabled=st.session_state.checked):
        if answer.strip().lower() == word:
            correct_answer()
        else:
            wrong_answer()

# ---------- Mode: Missing Letters ----------
elif mode == "🔤 Missing Letters":
    if "mask_for" not in st.session_state or st.session_state.mask_for != word:
        st.session_state.mask_for = word
        st.session_state.mask = masked_word(word)
    st.subheader("Fill in the missing letters.")
    st.markdown(f'<div class="big-word">{st.session_state.mask}</div>', unsafe_allow_html=True)
    answer = st.text_input(
        "Complete the word",
        key=f"mask_{st.session_state.round_id}",
        placeholder="Type the full word...",
    )
    if st.button("Check Answer", type="primary", use_container_width=True, disabled=st.session_state.checked):
        if answer.strip().lower() == word:
            correct_answer()
        else:
            wrong_answer()

# ---------- Mode: Multiple Choice ----------
else:
    st.subheader("Choose the correctly spelled word.")
    if "choices_for" not in st.session_state or st.session_state.choices_for != word:
        st.session_state.choices_for = word
        choices = {word}
        while len(choices) < min(4, max(2, len(st.session_state.words))):
            if len(word) > 3:
                i = random.randrange(1, len(word)-1)
                j = random.randrange(1, len(word)-1)
                if i != j:
                    letters = list(word)
                    letters[i], letters[j] = letters[j], letters[i]
                    choices.add("".join(letters))
            if len(choices) < 4:
                choices.add(random.choice(st.session_state.words))
        st.session_state.choices = random.sample(list(choices), len(choices))

    selected = st.radio(
        "Pick one:",
        st.session_state.choices,
        key=f"choice_{st.session_state.round_id}",
        label_visibility="collapsed",
    )
    if st.button("Check Answer", type="primary", use_container_width=True, disabled=st.session_state.checked):
        if selected == word:
            correct_answer()
        else:
            wrong_answer()

st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.feedback:
    if st.session_state.feedback.startswith("🎉"):
        st.success(st.session_state.feedback)
        st.balloons()
    else:
        st.warning(st.session_state.feedback)

if st.session_state.checked:
    if st.button("Next Word ➜", type="primary", use_container_width=True):
        new_round()
        st.rerun()

st.divider()

# ---------- Mastery section ----------
st.subheader("📚 This Week's Words")
cols = st.columns(2)
for i, w in enumerate(st.session_state.words):
    misses = st.session_state.review.get(w, 0)
    status = "✅" if misses == 0 else "🔁"
    cols[i % 2].write(f"{status} {w}")

if st.session_state.correct + st.session_state.missed >= 5:
    total = st.session_state.correct + st.session_state.missed
    accuracy = round(100 * st.session_state.correct / total)
    st.progress(accuracy / 100, text=f"Accuracy: {accuracy}%")
