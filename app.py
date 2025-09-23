# advanced_demo.py
import streamlit as st
import random, time, os
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import pandas as pd

st.set_page_config(page_title="Psychology Counselling Demo (Advanced)", layout="wide")

# -------------------- Session init --------------------
def init_state():
    defaults = {
        "reaction_time": None,
        "rt_ready": False,
        "rt_start_time": None,
        "memory_seq": None,
        "memory_phase": None,   # None / "show" / "input" / "done"
        "memory_input": "",
        "memory_result": None,
        "conc_letters": None,
        "conc_revealed": None,
        "conc_start_time": None,
        "conc_clicks": 0,
        "conc_found": False,
        "conc_time": None,
        "sentiment_label": None,
        "sentiment_score": None,
        "mood": None,
        "student_log_path": "student_results.csv"
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# -------------------- Helpers: Scoring --------------------
def score_reaction(rt):
    if rt is None:
        return None
    # lower = better
    if rt < 0.35:
        return 100
    elif rt < 0.55:
        return 85
    elif rt < 0.8:
        return 60
    else:
        return 30

def score_memory(seq, user_input):
    if not seq or not user_input:
        return None
    seq_list = seq
    user_list = user_input.strip().split()
    # compare position-wise (partial credit)
    matches = sum(1 for a,b in zip(seq_list, user_list) if a == b)
    return int(matches / len(seq_list) * 100)

def score_concentration(found, clicks, time_s, total_cells=36):
    if not found:
        return 15
    # fewer clicks and less time -> better
    penalty = max(0, (clicks - 1) * 8 + int(time_s * 8))
    return max(0, 100 - penalty)

def score_mood_sentiment(mood, sentiment_label):
    mood_map = {"😊 Happy":100,"😐 Neutral":85,"😔 Sad":40,"😟 Anxious":30,"😴 Tired":45}
    mood_score = mood_map.get(mood, 80)
    sentiment_map = {"Positive":100, "Neutral":70, "Negative":25}
    sent_score = sentiment_map.get(sentiment_label, 70)
    # combine (weighted)
    return int(0.6 * mood_score + 0.4 * sent_score)

def compute_final_score(r_score, m_score, c_score, ms_score):
    # weights (can be tuned)
    weights = {'reaction':0.20, 'memory':0.25, 'concentration':0.25, 'mood':0.30}
    total_weight = 0
    weighted_sum = 0
    if r_score is not None:
        weighted_sum += r_score * weights['reaction']; total_weight += weights['reaction']
    if m_score is not None:
        weighted_sum += m_score * weights['memory']; total_weight += weights['memory']
    if c_score is not None:
        weighted_sum += c_score * weights['concentration']; total_weight += weights['concentration']
    if ms_score is not None:
        weighted_sum += ms_score * weights['mood']; total_weight += weights['mood']
    if total_weight == 0:
        return None
    final = weighted_sum / total_weight
    return round(final, 1)

def risk_category(final_score):
    if final_score is None:
        return "Insufficient data"
    if final_score >= 75:
        return "Normal"
    if final_score >= 50:
        return "At-Risk"
    return "High-Risk"

# -------------------- Sidebar: Student info --------------------
st.sidebar.header("Student Info & Controls")
student_id = st.sidebar.text_input("Student ID", value="student_001")
student_name = st.sidebar.text_input("Name", value="Test Student")
st.sidebar.markdown("**Use the tabs to run games, fill survey, then compute result.**")

# -------------------- Main UI --------------------
st.title("🧠 Psychology-Aware Counselling — Advanced Demo")
tabs = st.tabs(["🎮 Games", "📝 Survey & Text", "📊 Result & Export"])

# -------------------- Games Tab --------------------
with tabs[0]:
    st.header("Games — measure attention, memory & concentration")

    # ------- Reaction Time -------
    st.subheader("1) Reaction Time Test")
    st.write("Press **Start**, wait until the app shows `CLICK!`, then click it as fast as you can.")
    col1, col2 = st.columns([1,2])
    with col1:
        if st.button("Start Reaction Test", key="start_rt"):
            wait = random.uniform(1.8, 3.0)
            st.info("Get ready... (do not press anything until CLICK appears)")
            time.sleep(wait)  # brief blocking wait so student can't cheat by pre-clicking
            st.session_state.rt_start_time = time.time()
            st.session_state.rt_ready = True
            st.rerun()

    with col2:
        if st.session_state.rt_ready:
            if st.button("CLICK! Now!", key="rt_click"):
                rt = time.time() - st.session_state.rt_start_time
                st.session_state.reaction_time = round(rt, 3)
                st.success(f"Reaction time recorded: {st.session_state.reaction_time} seconds")
                st.session_state.rt_ready = False

    st.markdown("---")

    # ------- Memory Test -------
    st.subheader("2) Memory Test (sequence shown briefly)")
    st.write("Press **Start Memory** — you'll see a short sequence for 3 seconds, it will disappear, then type what you remember.")
    if st.button("Start Memory Test", key="start_mem"):
        seq = [str(random.randint(0,9)) for _ in range(5)]
        st.session_state.memory_seq = seq
        st.session_state.memory_phase = "show"
        placeholder = st.empty()
        placeholder.info("Memorize this sequence (3 seconds):  " + "  ".join(seq))
        time.sleep(3)
        placeholder.empty()
        st.session_state.memory_phase = "input"
        st.rerun()


    if st.session_state.memory_phase == "input":
        st.write("Enter the sequence you just saw (space separated):")
        mem_input = st.text_input("Your answer:", key="mem_input")
        if st.button("Submit Memory", key="submit_mem"):
            st.session_state.memory_input = mem_input
            seq = st.session_state.memory_seq or []
            result_score = score_memory(seq, mem_input)
            st.session_state.memory_result = result_score
            if result_score == 100:
                st.success("Great — perfect recall!")
            else:
                st.warning(f"Partial/Incorrect — memory score: {result_score}%")
            st.session_state.memory_phase = "done"

    if st.session_state.memory_phase == "done" and st.session_state.memory_result is not None:
        st.write(f"Memory score: **{st.session_state.memory_result}%** (sequence was: {' '.join(st.session_state.memory_seq)})")

    st.markdown("---")

    # ------- Concentration Test -------
    st.subheader("3) Concentration Grid")
    st.write("Press Start to generate a grid of `?`. Click cells to reveal letters. Find the single `O` (others are `Q`).")
    if st.button("Start Concentration Test", key="start_conc"):
        rows, cols = 6, 6
        total = rows * cols
        pos = random.randint(0, total - 1)
        letters = ["Q"] * total
        letters[pos] = "O"
        st.session_state.conc_letters = letters
        st.session_state.conc_revealed = [False] * total
        st.session_state.conc_start_time = time.time()
        st.session_state.conc_clicks = 0
        st.session_state.conc_found = False
        st.session_state.conc_time = None
        st.rerun()


    if st.session_state.conc_letters:
        rows, cols = 6, 6
        letters = st.session_state.conc_letters
        revealed = st.session_state.conc_revealed
        # display grid
        for r in range(rows):
            cols_ui = st.columns(cols)
            for c in range(cols):
                idx = r * cols + c
                label = "?" if not revealed[idx] else letters[idx]
                clicked = cols_ui[c].button(label, key=f"conc_{idx}")
                if clicked:
                    # reveal cell
                    if not st.session_state.conc_revealed[idx]:
                        st.session_state.conc_revealed[idx] = True
                        st.session_state.conc_clicks += 1
                        if letters[idx] == "O" and not st.session_state.conc_found:
                            st.session_state.conc_found = True
                            st.session_state.conc_time = round(time.time() - st.session_state.conc_start_time, 3)
                            st.success(f"Found 'O' in {st.session_state.conc_clicks} clicks, {st.session_state.conc_time}s")
                            # reveal all
                            st.session_state.conc_revealed = [True] * len(letters)
                            st.rerun()

        # If already found, show stats
        if st.session_state.conc_found:
            st.info(f"Concentration result — clicks: {st.session_state.conc_clicks}, time: {st.session_state.conc_time}s")

# -------------------- Survey & Text Tab --------------------
with tabs[1]:
    st.header("Survey & Short Text (sentiment)")
    st.write("Quick mood survey (1 question) + short text input for sentiment analysis.")
    mood = st.radio("How do you feel today?", ["😊 Happy", "😐 Neutral", "😔 Sad", "😟 Anxious", "😴 Tired"], index=1, key="mood_radio")
    st.session_state.mood = mood

    st.write("Write a short sentence about how you feel (one or two lines).")
    user_text = st.text_area("Your text:", height=120, key="user_text")
    if st.button("Analyze Sentiment", key="analyze_sent"):
        if user_text.strip() == "":
            st.warning("Please type something (or use the mood option).")
        else:
            analyzer = SentimentIntensityAnalyzer()
            score = analyzer.polarity_scores(user_text)
            comp = score["compound"]
            if comp >= 0.05:
                label = "Positive"
            elif comp <= -0.05:
                label = "Negative"
            else:
                label = "Neutral"
            st.session_state.sentiment_label = label
            st.session_state.sentiment_score = round(comp, 3)
            st.write(f"🔍 Sentiment: **{label}**  |  compound score: {st.session_state.sentiment_score}")
    # if previously analyzed, show
    if st.session_state.sentiment_label:
        st.write(f"Last sentiment: **{st.session_state.sentiment_label}** (score {st.session_state.sentiment_score})")

# -------------------- Result & Export Tab --------------------
with tabs[2]:
    st.header("Result, Recommendations & Export")
    st.write("When you're ready, compute the combined psychological score and suggested action.")

    if st.button("Compute Psychological Risk", key="compute_risk"):
        # gather individual scores
        r_score = score_reaction(st.session_state.reaction_time)
        m_score = st.session_state.memory_result if st.session_state.memory_result is not None else score_memory(st.session_state.memory_seq, st.session_state.memory_input)
        c_score = score_concentration(st.session_state.conc_found, st.session_state.conc_clicks, st.session_state.conc_time)
        ms_score = score_mood_sentiment(st.session_state.mood, st.session_state.sentiment_label or "Neutral")

        final = compute_final_score(r_score, m_score, c_score, ms_score)
        category = risk_category(final)

        st.session_state._last_eval = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "student_id": student_id,
            "student_name": student_name,
            "reaction_time": st.session_state.reaction_time,
            "reaction_score": r_score,
            "memory_seq": " ".join(st.session_state.memory_seq) if st.session_state.memory_seq else "",
            "memory_input": st.session_state.memory_input,
            "memory_score": m_score,
            "conc_clicks": st.session_state.conc_clicks,
            "conc_time": st.session_state.conc_time,
            "conc_found": st.session_state.conc_found,
            "concentration_score": c_score,
            "mood": st.session_state.mood,
            "sentiment_label": st.session_state.sentiment_label,
            "sentiment_score": st.session_state.sentiment_score,
            "mood_sent_score": ms_score,
            "final_score": final,
            "risk_category": category
        }

        # show results
        st.markdown("### 🔎 Evaluation Summary")
        st.write(f"**Final score:** {final} / 100")
        if category == "Normal":
            st.success("✅ Category: **Normal** — no immediate action required.")
        elif category == "At-Risk":
            st.warning("⚠️ Category: **At-Risk** — suggest light counselling, peer mentoring and follow-up.")
        else:
            st.error("🚨 Category: **High-Risk** — immediate counsellor human intervention recommended.")

        # tailored suggestions
        st.markdown("### Suggested Actions")
        suggestions = []
        if r_score is not None and r_score < 60:
            suggestions.append("Improve sleep & alertness routines; schedule attention-building activities.")
        if m_score is not None and m_score < 60:
            suggestions.append("Memory & study-skills coaching session recommended.")
        if c_score is not None and c_score < 60:
            suggestions.append("Short concentration exercises (pomodoro, focus drills).")
        if (st.session_state.sentiment_label == "Negative") or (ms_score is not None and ms_score < 50):
            suggestions.append("Schedule 1:1 counselling and mental health check-in.")
        if not suggestions:
            suggestions.append("Continue regular monitoring; encourage positive habits.")

        for s in suggestions:
            st.write("- " + s)

        # log to CSV
        df_row = pd.DataFrame([st.session_state._last_eval])
        file_path = st.session_state.student_log_path
        if os.path.exists(file_path):
            df_row.to_csv(file_path, mode='a', header=False, index=False)
        else:
            df_row.to_csv(file_path, index=False)

        st.success(f"Result logged to `{file_path}`")

    # show last evaluation if present
    if "_last_eval" in st.session_state:
        st.write("Most recent evaluation:")
        st.json(st.session_state._last_eval)

    # download logged csv
    if os.path.exists(st.session_state.student_log_path):
        df_all = pd.read_csv(st.session_state.student_log_path)
        st.markdown("### Export / Download logged results")
        st.dataframe(df_all.tail(10))
        csv_bytes = df_all.to_csv(index=False).encode('utf-8')
        st.download_button("Download all results (CSV)", data=csv_bytes, file_name="student_results.csv", mime="text/csv")

    st.markdown("---")
    st.info("Tip: run multiple students / repeated sessions to collect data and later train a classifier for higher accuracy.")

