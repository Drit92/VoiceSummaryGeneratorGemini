import streamlit as st
import speech_recognition as sr
from pydub import AudioSegment
import tempfile
import datetime
import os
from google import genai
import streamlit.components.v1 as components


notes_css = """
<style>
.notes-container {
    background: #fff9c4;
    border: 1px solid #fbc02d;
    border-radius: 5px;
    padding: 20px;
    font-family: 'Courier New', monospace;
    box-shadow: 2px 2px 10px #fbc02d88;
    white-space: pre-wrap;
    margin-bottom: 30px;
}
body {
    background-color: #e3f2fd;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    color: #0d47a1;
}
</style>
"""
st.markdown(notes_css, unsafe_allow_html=True)

client = genai.Client()

st.set_page_config(page_title="Lecture Voice-to-Notes Generator with Gemini", layout="wide")

# Session state for button clicks
if 'generate_quiz' not in st.session_state:
    st.session_state.generate_quiz = False
if 'generate_flashcards' not in st.session_state:
    st.session_state.generate_flashcards = False

st.sidebar.title("Actions")
if st.sidebar.button("Generate Quiz"):
    st.session_state.generate_quiz = True
if st.sidebar.button("Generate Flashcards"):
    st.session_state.generate_flashcards = True

st.title("Lecture Voice-to-Notes Generator")
st.write("""
Upload your lecture audio file (wav, mp3, m4a, ogg), transcribe it, summarize notes, and generate quizzes and flashcards using Gemini API!
""")

def convert_to_wav(uploaded_file):
    temp_input = tempfile.NamedTemporaryFile(delete=False)
    temp_input.write(uploaded_file.read())
    temp_input.flush()
    temp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    audio = AudioSegment.from_file(temp_input.name)
    audio.export(temp_output.name, format="wav")
    os.unlink(temp_input.name)
    return temp_output.name

def transcribe_audio(file_path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(file_path) as source:
        audio_data = recognizer.record(source)
        try:
            return recognizer.recognize_google(audio_data)
        except sr.UnknownValueError:
            return "Sorry, could not understand the audio."
        except sr.RequestError:
            return "Speech recognition service unavailable."

def gemini_generate(prompt: str) -> str:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt]
    )
    return response.text

def generate_study_notes(text):
    prompt = f"Summarize the following lecture notes:\n{text}"
    return gemini_generate(prompt)

def generate_quiz(notes):
    prompt = f"Generate a quiz with questions and answers based on these notes:\n{notes}"
    return gemini_generate(prompt)

def generate_flashcards(notes):
    prompt = (
        "Create interactive flashcards with a 'Front:' and 'Back:' section for each card, based on these notes. "
        "Format the output strictly as multiple blocks like:\n"
        "Front: [question here]\n"
        "Back: [answer here]\n\n"
        "Provide clear and concise questions and answers suitable for study.\n\n"
        f"Notes:\n{notes}"
    )
    return gemini_generate(prompt)

for key in ("transcript", "notes", "quiz", "flashcards"):
    if key not in st.session_state:
        st.session_state[key] = None

with st.form("upload_form"):
    audio_file = st.file_uploader("Upload audio (wav, mp3, m4a, ogg)", type=["wav", "mp3", "m4a", "ogg"])
    submit = st.form_submit_button("Process Audio")

if submit and audio_file:
    with st.spinner("Processing audio..."):
        try:
            wav_path = convert_to_wav(audio_file)
            transcript = transcribe_audio(wav_path)
            os.remove(wav_path)
            st.session_state.transcript = transcript
            st.session_state.notes = None
            st.session_state.quiz = None
            st.session_state.flashcards = None
            st.session_state.generate_quiz = False
            st.session_state.generate_flashcards = False
        except Exception as e:
            st.error(f"Error during processing: {e}")
            st.session_state.transcript = None
            st.session_state.notes = None
            st.session_state.quiz = None
            st.session_state.flashcards = None

if st.session_state.transcript:
    st.subheader("Lecture Transcript")
    st.write(st.session_state.transcript)
    if len(st.session_state.transcript) > 50:
        if st.session_state.notes is None:
            with st.spinner("Generating summarized notes..."):
                st.session_state.notes = generate_study_notes(st.session_state.transcript)

        st.markdown(f'<div class="notes-container">{st.session_state.notes}</div>', unsafe_allow_html=True)

        if st.session_state.generate_quiz:
            with st.spinner("Generating quiz questions..."):
                st.session_state.quiz = generate_quiz(st.session_state.notes)
            st.session_state.generate_quiz = False

        if st.session_state.generate_flashcards:
            with st.spinner("Generating flashcards..."):
                st.session_state.flashcards = generate_flashcards(st.session_state.notes)
            st.session_state.generate_flashcards = False

        if st.session_state.quiz:
            st.markdown('<a id="quiz-section"></a>', unsafe_allow_html=True)
            st.subheader("Quiz Questions")
            st.write(st.session_state.quiz)

        if st.session_state.flashcards:
            st.markdown('<a id="flashcards-section"></a>', unsafe_allow_html=True)
            st.subheader("Flashcards")

            flashcards_text = st.session_state.flashcards.strip()
            lines = flashcards_text.splitlines()

            cards = []
            current_front = None
            current_back = None

            for line in lines:
                line = line.strip()
                if line.startswith("Front:"):
                    if current_front and current_back:
                        cards.append((current_front, current_back))
                    current_front = line[len("Front:"):].strip()
                    current_back = None
                elif line.startswith("Back:") and current_front:
                    current_back = line[len("Back:"):].strip()
                else:
                    continue

            if current_front and current_back:
                cards.append((current_front, current_back))

            # Build full HTML document string with cards and embedded CSS/JS
            cards_html = ""
            for i, (front, back) in enumerate(cards, start=1):
                cards_html += f"""
                <div class="flashcard">
                  <div class="flashcard-inner">
                    <div class="flashcard-front">Flashcard {i}<br>{front}</div>
                    <div class="flashcard-back">{back}</div>
                  </div>
                </div>
                """

            full_html = f"""
            <html>
            <head>
            <style>
            .flashcard {{
              background: #fefefe;
              width: 320px;
              height: 200px;
              perspective: 1000px;
              margin: 10px;
              display: inline-block;
              cursor: pointer;
              border-radius: 10px;
              box-shadow: 3px 4px 10px rgba(0,0,0,0.2);
              user-select: none;
              transition: transform 0.3s ease;
            }}
            .flashcard-inner {{
              position: relative;
              width: 100%;
              height: 100%;
              transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
              transform-style: preserve-3d;
              border-radius: 10px;
            }}
            .flashcard.is-flipped .flashcard-inner {{
              transform: rotateY(180deg);
            }}
            .flashcard-front, .flashcard-back {{
              position: absolute;
              width: 100%;
              height: 100%;
              backface-visibility: hidden;
              border-radius: 10px;
              box-sizing: border-box;
              padding: 20px;
              display: flex;
              justify-content: center;
              align-items: center;
              font-size: 16px;
              font-weight: 600;
              text-align: left;
              user-select: none;
              flex-direction: column;
              overflow-y: auto;
              white-space: pre-wrap;
            }}
            .flashcard-front {{
              background: #bbdefb;
              color: #0d47a1;
              box-shadow: inset 0 0 10px rgba(13, 71, 161, 0.3);
            }}
            .flashcard-back {{
              background: #0d47a1;
              color: white;
              transform: rotateY(180deg);
              box-shadow: inset 0 0 10px rgba(255, 255, 255, 0.2);
            }}
            </style>
            </head>
            <body>
            <div id="flashcards-container">
            {cards_html}
            </div>
            <script>
            function addFlipListeners() {{
              const cards = document.querySelectorAll('.flashcard');
              cards.forEach(card => {{
                card.onclick = () => card.classList.toggle('is-flipped');
              }});
            }}
            document.addEventListener("DOMContentLoaded", addFlipListeners);
            </script>
            </body>
            </html>
            """

            components.html(full_html, height=320 + 220 * len(cards))

    else:
        st.info("Transcript is too short to summarize.")

st.write("### Feedback and Suggestions")
feedback = st.text_area("Provide any feedback here:")
if st.button("Submit Feedback"):
    if feedback.strip():
        try:
            with open("feedback_log.txt", "a") as f:
                f.write(f"{datetime.datetime.now()}: {feedback}\n")
            st.success("Thank you for your feedback!")
        except Exception as e:
            st.error(f"Failed to save feedback: {e}")
    else:
        st.warning("Please enter feedback before submitting.")
