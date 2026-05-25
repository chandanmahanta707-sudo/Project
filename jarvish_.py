from openai import OpenAI
import speech_recognition as sr
import os
import webbrowser
import datetime
import pyautogui
import requests
from langdetect import detect
import re
import keyboard
import multiprocessing
import time
import psutil
import subprocess
from dotenv import load_dotenv

load_dotenv()

# =========================
# 🔑 SET YOUR API KEY HERE
# =========================
client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1"
)

# =========================
# 📇 CONTACTS & MESSAGING SETUP
# =========================
# Add your contacts here. Ensure you include country codes for WhatsApp (e.g., +1, +91).
CONTACTS = {
    "me": {"phone": "+910000000000", "email": "your_email@gmail.com"},
    "boss": {"phone": "+1234567890", "email": "boss@example.com"},
    "mom": {"phone": "+1122334455", "email": "mom@example.com"},
}

# Email Credentials for Background Sending (Use 16-character SMTP App Password, NOT your regular password)
MY_EMAIL = os.getenv("MY_EMAIL")
MY_EMAIL_APP_PASSWORD = os.getenv("MY_EMAIL_APP_PASSWORD")

# =========================
# 🗣️ TEXT TO SPEECH
# =========================
import win32com.client
import tempfile
import os
import time

try:
    import pyttsx3
    pyttsx3_engine = pyttsx3.init()
    pyttsx3_engine.setProperty('rate', 180)
except ImportError:
    pyttsx3_engine = None

try:
    import gtts
except ImportError:
    gtts = None

# Set the TTS engine here (sapi, pyttsx3, gtts)
TTS_ENGINE = "sapi"

# Use pure Native Windows SAPI to absolutely eliminate any delays!
sapi = win32com.client.Dispatch("SAPI.SpVoice")
sapi.Rate = 1  # Moderate fast speed (similar to 180wpm natively)

# Global toggle to enable/disable background voice interruption listening
VOICE_INTERRUPTION_ENABLED = True


preload_command_from_interrupt = ""

def speak(text, listen_for_stop=None):
    if listen_for_stop is None:
        listen_for_stop = VOICE_INTERRUPTION_ENABLED
        
    print("Jarvis:", text)
    log_to_dashboard("jarvis", text)

    r = sr.Recognizer()
    r.energy_threshold = 400
    r.pause_threshold = 0.5
    r.non_speaking_duration = 0.3
    interrupted = False

    def bg_callback(recognizer, audio):
        nonlocal interrupted
        global preload_command_from_interrupt
        try:
            speech = recognizer.recognize_google(audio).lower()
            if "stop" in speech or "jarvis" in speech or "shut up" in speech:
                interrupted = True
                cleaned = speech.replace("jarvis", "").replace("stop", "").replace("shut up", "").replace("please", "").strip()
                if cleaned:
                    preload_command_from_interrupt = cleaned
        except Exception:
            pass

    # Start listening in background for voice interruption
    stop_listen = lambda wait_for_stop: None
    if listen_for_stop:
        try:
            m = sr.Microphone()
            with m as source:
                r.adjust_for_ambient_noise(source, duration=0.1)
            stop_listen = r.listen_in_background(m, bg_callback, phrase_time_limit=1.5)
        except Exception:
            # Fallback if mic is already in use
            pass

    try:
        if TTS_ENGINE == "sapi":
            sapi.Speak(text, 1) # 1 = SVSFlagsAsync
            time.sleep(0.1)
            while sapi.Status.RunningState == 2:
                try:
                    if keyboard.is_pressed("space"):
                        interrupted = True
                except Exception:
                    pass
                if interrupted:
                    print("\n[Jarvis stopped speaking]")
                    sapi.Speak("", 2) # 2 = SVSFPurgeBeforeSpeak
                    break
                time.sleep(0.05)
                
        elif TTS_ENGINE == "pyttsx3":
            if pyttsx3_engine:
                try:
                    pyttsx3_engine.say(text)
                    pyttsx3_engine.runAndWait()
                except Exception as e:
                    print("pyttsx3 Error:", e)
            else:
                print("pyttsx3 not installed. Defaulting to SAPI.")
                sapi.Speak(text, 0)
                
        elif TTS_ENGINE == "gtts":
            if gtts:
                try:
                    tts = gtts.gTTS(text=text, lang='en')
                    temp_filename = "temp_speech.mp3"
                    tts.save(temp_filename)
                    import vlc
                    player = vlc.MediaPlayer(temp_filename)
                    player.play()
                    time.sleep(0.5) # Give it a moment to start
                    while True:
                        state = player.get_state()
                        if state in [vlc.State.Ended, vlc.State.Error, vlc.State.Stopped]:
                            break
                        try:
                            if keyboard.is_pressed("space"):
                                interrupted = True
                        except Exception:
                            pass
                        if interrupted:
                            print("\n[Jarvis stopped speaking]")
                            break
                        time.sleep(0.05)
                    # Stop player and remove file automatically
                    player.stop()
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)
                except Exception as e:
                    print("gTTS Error:", e)
            else:
                print("gTTS not installed. Defaulting to SAPI.")
                sapi.Speak(text, 0)
    except Exception as e:
        print("TTS Error:", e)

    # Stop background listener when finished speaking
    stop_listen(wait_for_stop=False)


# =========================
# 🎤 SPEECH & TEXT INPUT
# =========================
input_mode = "voice"
last_f2_toggle = 0

import threading
import pythoncom


def toggle_input_mode(e):
    global input_mode, last_f2_toggle
    if time.time() - last_f2_toggle > 0.5:
        input_mode = "text" if input_mode == "voice" else "voice"
        print(
            f"\n\n[Switched to {input_mode.upper()} mode - Press F2 to toggle]\n",
            end="",
            flush=True,
        )
        
        try:
            import requests
            requests.post("http://127.0.0.1:5000/api/mode", json={"mode": input_mode}, timeout=0.1)
        except Exception:
            pass

        # Threaded COM initialization so it doesn't crash from keyboard background hook
        def speak_mode():
            pythoncom.CoInitialize()
            local_sapi = win32com.client.Dispatch("SAPI.SpVoice")
            local_sapi.Rate = 1
            # 0 = Synchronous flag, preventing the background thread from dying before the audio finishes!
            local_sapi.Speak(f"Switched to {input_mode} mode", 0)

        threading.Thread(target=speak_mode).start()
        last_f2_toggle = time.time()


# F2 hotkey binding moved to run_jarvis to avoid multiprocessing fork bomb duplicate triggers


def _hud_process(visible_flag, state_val):
    # Tk UI Logic
    import tkinter as tk
    import math

    root = tk.Tk()
    root.title("J.A.R.V.I.S.")
    root.geometry("150x150")
    root.attributes("-topmost", True)
    root.configure(bg="#000001")
    try:
        root.attributes("-transparentcolor", "#000001")
    except Exception:
        pass
    root.overrideredirect(True)
    try:
        # Move to top-right corner
        x = root.winfo_screenwidth() - 170
        y = 20
        root.geometry(f"+{x}+{y}")
    except Exception:
        pass

    canvas = tk.Canvas(root, width=150, height=150, bg="#000001", highlightthickness=0, bd=0)
    canvas.pack()
    angle = 0
    current_visibility = True

    # Drag window logic
    drag_data = {"x": 0, "y": 0}

    def start_drag(event):
        drag_data["x"] = event.x
        drag_data["y"] = event.y

    def stop_drag(event):
        drag_data["x"] = None
        drag_data["y"] = None

    def do_drag(event):
        if drag_data["x"] is not None and drag_data["y"] is not None:
            x = root.winfo_x() - drag_data["x"] + event.x
            y = root.winfo_y() - drag_data["y"] + event.y
            root.geometry(f"+{x}+{y}")

    canvas.bind("<ButtonPress-1>", start_drag)
    canvas.bind("<ButtonRelease-1>", stop_drag)
    canvas.bind("<B1-Motion>", do_drag)
    
    # Change cursor on hover to indicate it's draggable
    canvas.bind("<Enter>", lambda e: canvas.config(cursor="fleur"))
    canvas.bind("<Leave>", lambda e: canvas.config(cursor=""))

    def update_hud():
        nonlocal angle, current_visibility
        is_visible = visible_flag.value == 1

        if is_visible and not current_visibility:
            root.deiconify()
            current_visibility = True
        elif not is_visible and current_visibility:
            root.withdraw()
            current_visibility = False

        if current_visibility:
            canvas.delete("all")
            # Center coordinates for 150x150
            cx, cy = 75, 75
            # Scaled down radii
            r1, r2, r3 = 45, 55, 65
            angle = (angle + 3) % 360

            color1, color2, color3 = "#00e5ff", "#00a8ff", "#ccffff"
            canvas.create_oval(
                cx - r1, cy - r1, cx + r1, cy + r1, outline=color1, width=2
            )

            for i in range(0, 360, 45):
                start = math.radians(i + angle)
                canvas.create_arc(
                    cx - r2,
                    cy - r2,
                    cx + r2,
                    cy + r2,
                    start=math.degrees(start),
                    extent=20,
                    outline=color1,
                    width=3,
                    style=tk.ARC,
                )

            for i in range(0, 360, 30):
                start = math.radians(i - angle * 1.5)
                canvas.create_arc(
                    cx - r3,
                    cy - r3,
                    cx + r3,
                    cy + r3,
                    start=math.degrees(start),
                    extent=10,
                    outline=color2,
                    width=2,
                    style=tk.ARC,
                )

            canvas.create_text(
                cx,
                cy - 5,
                text="J.A.R.V.I.S.",
                fill=color1,
                font=("Segoe UI", "9", "bold"),
            )
            state_text = "LISTENING..." if state_val.value == 1 else "PROCESSING..."
            canvas.create_text(
                cx, cy + 12, text=state_text, fill=color3, font=("Segoe UI", "6")
            )

        root.after(30, update_hud)

    update_hud()
    root.mainloop()


class JarvisHUD:
    def __init__(self):
        self.visible_flag = multiprocessing.Value("i", 0)
        self.state_val = multiprocessing.Value("i", 1)
        self.proc = multiprocessing.Process(
            target=_hud_process, args=(self.visible_flag, self.state_val), daemon=True
        )
        self.proc.start()

    def start(self):
        self.visible_flag.value = 1

    def stop(self):
        self.visible_flag.value = 0

    def set_state(self, text):
        self.state_val.value = 1 if text == "LISTENING..." else 2


jarvis_hud = None


def init_hud():
    global jarvis_hud
    if jarvis_hud is None:
        jarvis_hud = JarvisHUD()


def update_dashboard_status(state):
    try:
        import requests
        requests.post("http://127.0.0.1:5000/api/status", json={"state": state}, timeout=0.1)
    except:
        pass

def update_dashboard_music(song_name, status):
    try:
        import requests
        requests.post("http://127.0.0.1:5000/api/music", json={"song_name": song_name, "status": status}, timeout=0.1)
    except:
        pass

def log_to_dashboard(log_type, text):
    try:
        import requests
        requests.post("http://127.0.0.1:5000/api/log", json={"type": log_type, "text": text}, timeout=0.1)
    except:
        pass

def listen():
    global input_mode, jarvis_hud, preload_command_from_interrupt
    if input_mode == "voice":
        if preload_command_from_interrupt:
            cmd = preload_command_from_interrupt
            preload_command_from_interrupt = ""
            print("You (Voice, via Interruption):", cmd)
            log_to_dashboard("user", cmd)
            return cmd

        if jarvis_hud:
            jarvis_hud.start()
        if jarvis_hud:
            jarvis_hud.set_state("LISTENING...")
        update_dashboard_status("LISTENING")
        r = sr.Recognizer()
        r.pause_threshold = (
            1.0  # Dramatically reduces wait time after you stop speaking!
        )
        try:
            with sr.Microphone() as source:
                print("Listening (Voice)... [Press F2 for Text Mode]")
                r.adjust_for_ambient_noise(source, duration=0.2)

                while input_mode == "voice":
                    try:
                        if jarvis_hud:
                            jarvis_hud.set_state("LISTENING...")
                        update_dashboard_status("LISTENING")
                        audio = r.listen(source, timeout=0.5, phrase_time_limit=15)
                        try:
                            if jarvis_hud:
                                jarvis_hud.set_state("PROCESSING...")
                            update_dashboard_status("PROCESSING")
                            text = r.recognize_google(audio)
                            print("You (Voice):", text)
                            log_to_dashboard("user", text)
                            if jarvis_hud:
                                jarvis_hud.stop()
                            update_dashboard_status("IDLE")
                            return text.lower()
                        except Exception:
                            pass
                    except sr.WaitTimeoutError:
                        pass
        except Exception:
            pass

        if jarvis_hud:
            jarvis_hud.stop()
        update_dashboard_status("IDLE")
        return ""
    else:
        # In text mode, the user relies on the Web HUD (server.py) to input text via the /api/command endpoint.
        # We simply sleep and return empty so the main loop doesn't spin wildly.
        time.sleep(0.5)
        return ""


# =========================
# 🌍 MULTI-LANGUAGE SUPPORT
# =========================
def detect_language(text):
    try:
        return detect(text)
    except Exception:
        return "en"


# =========================
# 🧠 DEEPSEEK AI RESPONSE
# =========================
chat_history = []


def ask_ai(prompt):
    global chat_history
    try:
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are Jarvis, a smart and concise AI voice assistant. The current date and time is {datetime.datetime.now().strftime('%A, %B %d, %Y %I:%M %p')}. "
                    "If the user asks for real-time information, current events, weather, sports scores, "
                    "or anything you do not currently know, you MUST reply ONLY with EXACTLY the word "
                    "SEARCH_WEB: followed by your search query. "
                    "For example: SEARCH_WEB: IPL match tomorrow schedule. "
                    "Otherwise, answer normally, concisely, and conversationally in plain text. "
                    "CRITICAL MAXIMUM LENGTH: ALWAYS ANSWER IN 1 TO 3 SHORT SENTENCES. BE EXTREMELY FAST AND CONCISE. "
                    "NEVER use markdown formatting like asterisks (*), hashtags (#), or backticks (`). "
                    "NEVER output JSON blocks or 'thoughts'."
                ),
            }
        ]

        # Append history for context
        messages.extend(chat_history)
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model="deepseek/deepseek-chat", messages=messages, max_tokens=100
        )

        # Get the raw text from AI
        raw_text = response.choices[0].message.content.strip()
        print(f"[DEBUG] AI Raw Output: {raw_text}")

        # Use regex to find SEARCH_WEB or SEARCHWEB anywhere in the response
        # This captures everything after the colon until a period, newline, or end of string.
        match = re.search(r"SEARCH_?WEB:\s*(.*?)(?=\.|\n|$)", raw_text, re.IGNORECASE)

        if match:
            query = match.group(1).strip(" \"'")
            print(f"Internet Source Required. Jarvis is searching the web for: {query}")

            try:
                try:
                    from ddgs import DDGS
                except ImportError:
                    from duckduckgo_search import DDGS

                # Convert to list to ensure compatibility with generator-based versions of DDGS
                results = list(DDGS().text(query, max_results=3))
                search_context = "\n".join(
                    [f"Source: {r['title']}\nInfo: {r['body']}" for r in results]
                )

                messages.append({"role": "assistant", "content": f"SEARCH_WEB: {query}"})
                messages.append(
                    {
                        "role": "user",
                        "content": f"Here are the web search results for your query:\n{search_context}\n\nNow, provide a short conversational answer to my original question based ONLY on these results.",
                    }
                )

                # Overwrite the system prompt so it stops trying to search again!
                messages[0]["content"] = (
                    f"You are Jarvis, a smart and concise AI voice assistant. The current date and time is {datetime.datetime.now().strftime('%A, %B %d, %Y %I:%M %p')}. "
                    "Answer normally, concisely, and conversationally in plain text using the provided search results. "
                    "CRITICAL MAXIMUM LENGTH: ALWAYS ANSWER IN 1 TO 3 SHORT SENTENCES. BE EXTREMELY FAST AND CONCISE. "
                    "NEVER output SEARCH_WEB. NEVER use markdown formatting."
                )

                response2 = client.chat.completions.create(
                    model="deepseek/deepseek-chat", messages=messages, max_tokens=100
                )
                raw_text = response2.choices[0].message.content.strip()
            except Exception as e:
                print("Web search failed:", e)
                return "I tried to search the web for that, but I couldn't get the results right now."

        # Clean out any remaining symbols just in case the AI messes up
        clean_text = re.sub(r"[*#_`\[\]{}]", "", raw_text)

        # Store in history
        chat_history.append({"role": "user", "content": prompt})
        chat_history.append({"role": "assistant", "content": clean_text})
        # Keep memory limited to last 10 interactions to prevent token overflow
        if len(chat_history) > 20:
            chat_history = chat_history[-20:]

        return clean_text

    except Exception as e:
        print(f"Error details: {e}")

        # Check if it was an internet disconnection error
        import socket

        try:
            socket.create_connection(("8.8.8.8", 53), timeout=1)
        except OSError:
            return "Sir, there is an error connecting to the Internet."

        return "Sir, there is an error connecting to the AI."


# =========================
# 🌐 REAL-TIME INFO (Weather & News)
# =========================
def get_weather(city="Bhubaneswar"):
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key or api_key == "your_openweather_api_key_here":
        # Fallback to wttr.in if API key is not set
        try:
            url = f"https://wttr.in/{city}?format=3"
            res = requests.get(url, timeout=5)
            weather_data = res.text
            clean_weather = re.sub(r"[^\x00-\x7F]+", "", weather_data).strip()
            if ":" in clean_weather:
                clean_weather = clean_weather.split(":")[-1].strip()
            return clean_weather.replace("C", " degrees Celsius").replace("+", "")
        except Exception:
            return "Couldn't fetch weather."

    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        res = requests.get(url, timeout=10).json()
        if res.get("cod") != 200:
            return "City not found."
        temp = res["main"]["temp"]
        desc = res["weather"][0]["description"]
        return f"{temp} degrees Celsius with {desc}"
    except Exception:
        return "Couldn't fetch weather."


def get_news(topic="world"):
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key or api_key == "your_news_api_key_here":
        return "Sir, your News API key is not configured in the dot env file. Please update it first."
    try:
        import urllib.parse
        safe_topic = urllib.parse.quote(topic)
        url = f"https://newsapi.org/v2/everything?q={safe_topic}&language=en&sortBy=publishedAt&pageSize=5&apiKey={api_key}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10).json()
        if res.get("status") != "ok":
            return "Failed to fetch news."
        articles = res.get("articles", [])
        if not articles:
            return "No news found at the moment."
        news_list = [article["title"].split(" - ")[0] for article in articles]
        return news_list
    except Exception:
        return "An error occurred while fetching the news."


# =========================
# 💻 PC CONTROL COMMANDS
# =========================
music_player = None
last_played_media = ""


def execute_command(command):
    global music_player
    global last_played_media
    # 1. Smart Google Search
    if "search" in command and "google" in command:
        query = (
            command.replace("search", "")
            .replace("on google", "")
            .replace("for", "")
            .strip()
        )
        if query:
            webbrowser.open(f"https://www.google.com/search?q={query}")
            speak(f"Searching Google for {query}")
        else:
            webbrowser.open("https://google.com")
            speak("Opening Google")

    # 2. Smart YouTube Player & Controls
    elif (
        "pause" in command
        or "resume" in command
        or ("play" in command and "video" in command)
    ):

        target_vlc = "music" in command or "background" in command
        target_browser = "video" in command or "youtube" in command

        # If generic command without specific target, apply to both
        if not target_vlc and not target_browser:
            target_vlc = True
            target_browser = True

        if "pause" in command or "stop" in command:
            if target_vlc and music_player is not None:
                try:
                    music_player.set_pause(1)  # force pause
                except Exception:
                    pass
            if target_browser:
                keyboard.send("play/pause media")
            speak("Playback paused.")
            update_dashboard_music(last_played_media if last_played_media else "MEDIA PAUSED", "PAUSED")

        elif "resume" in command or "play" in command:
            if target_vlc and music_player is not None:
                try:
                    # VLC state 4 is Paused. Only resume if it's paused.
                    if music_player.get_state() == 4:
                        music_player.play()
                except Exception:
                    pass
            if target_browser:
                keyboard.send("play/pause media")
            speak("Playback resumed.")
            update_dashboard_music(last_played_media if last_played_media else "MEDIA PLAYING", "PLAYING")

    elif command.startswith("play "):

        # Branch detection: Browser (YouTube) vs. Background (VLC)
        target_background = "background" in command or "music" in command

        if not target_background:
            query = (
                command.replace("play ", "")
                .replace("on youtube", "")
                .replace("in youtube", "")
                .strip()
            )

            # Context Memory
            if query in ["that song", "that video", "it", "this", "that"]:
                if last_played_media:
                    query = last_played_media
                else:
                    speak("I don't remember what you played last.")
                    return
            else:
                last_played_media = query

            original_query = query
            # Prioritize Original songs (ignore if user asked for remix/cover/latest)
            if not any(
                kw in query.lower()
                for kw in [
                    "remix",
                    "cover",
                    "mashup",
                    "lofi",
                    "slowed",
                    "reverb",
                    "live",
                    "latest video",
                ]
            ):
                query += " official song original"

            # "Latest Video" Logic
            if "latest video" in original_query:
                song_name_str = f"Latest from {original_query.replace('latest video', '').strip()}"
                speak(
                    f"Searching for the latest video from {original_query.replace('latest video', '').strip()}"
                )
            else:
                song_name_str = original_query
                speak(f"Playing {original_query} on YouTube")
            update_dashboard_music(song_name_str.upper(), "PLAYING")

            try:
                import urllib.request
                import urllib.parse

                query_string = urllib.parse.urlencode({"search_query": query})
                html_content = urllib.request.urlopen(
                    "https://www.youtube.com/results?" + query_string
                )
                search_results = re.findall(
                    r"watch\?v=(\S{11})", html_content.read().decode()
                )
                if search_results:
                    webbrowser.open(
                        "https://www.youtube.com/watch?v=" + search_results[0]
                    )
                else:
                    speak("I couldn't find the video.")
            except Exception:
                speak("There was an error playing the video.")
        else:
            query = (
                command.replace("play ", "")
                .replace("in background", "")
                .replace("in the background", "")
                .replace("music", "")
                .strip()
            )

            if query in ["that song", "that video", "it", "this", "that"]:
                if last_played_media:
                    query = last_played_media
                else:
                    speak("I don't remember what you played last.")
                    return
            else:
                last_played_media = query

            original_query = query
            # Prioritize Original songs (ignore if user asked for remix/cover/latest)
            if not any(
                kw in query.lower()
                for kw in [
                    "remix",
                    "cover",
                    "mashup",
                    "lofi",
                    "slowed",
                    "reverb",
                    "live",
                    "latest video",
                ]
            ):
                query += " official audio original"

            if "latest video" in original_query:
                speak(
                    f"Playing the latest release from {original_query.replace('latest video', '').strip()} in the background."
                )
            else:
                speak(f"Playing {original_query} in the background.")

            def bg_worker():
                try:
                    import yt_dlp
                    import vlc

                    global music_player
                    if music_player is None:
                        music_player = vlc.MediaPlayer()

                    ydl_opts = {
                        "format": "bestaudio/best",
                        "noplaylist": True,
                        "quiet": True,
                        "default_search": "scsearch1",
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(f"scsearch1:{query}", download=False)
                        if "entries" in info and len(info["entries"]) > 0:
                            entry = info["entries"][0]
                            audio_url = entry["url"]
                            song_title = entry.get("title", original_query)
                            media = vlc.Media(audio_url)
                            music_player.set_media(media)
                            music_player.play()
                            update_dashboard_music(song_title.upper(), "PLAYING")
                except Exception as e:
                    print("Background play error:", e)

            import threading

            threading.Thread(target=bg_worker, daemon=True).start()

    # 3. System App Control (Open/Close Any App or Folder)
    elif any(kw in command for kw in ["open", "close", "launch", "exit", "terminate"]):
        # Known web apps
        WEB_APPS = {
            "google": "https://google.com",
            "youtube": "https://youtube.com",
            "gmail": "https://mail.google.com",
            "whatsapp": "https://web.whatsapp.com",
        }
        
        # Check for web apps first
        found_web = False
        for app_name, url in WEB_APPS.items():
            if app_name in command:
                found_web = True
                if "open" in command or "launch" in command:
                    speak(f"Opening {app_name}")
                    webbrowser.open(url)
                elif any(kw in command for kw in ["close", "exit", "terminate"]):
                    speak("Closing browser tabs.")
                    pyautogui.hotkey("ctrl", "w")
                break
                
        if found_web:
            return

        # Special Case: Close current tab/window
        if "tab" in command and any(kw in command for kw in ["close", "exit", "terminate"]):
            speak("Closing the current tab.")
            pyautogui.hotkey("ctrl", "w")
            return
        if "window" in command and any(kw in command for kw in ["close", "exit", "terminate"]):
            speak("Closing the current window.")
            pyautogui.hotkey("alt", "f4")
            return

        # Smart Open / Close any app or folder
        is_open = "open" in command or "launch" in command
        
        # Extract the target name dynamically
        target = command.replace("open", "").replace("launch", "").replace("close", "").replace("exit", "").replace("terminate", "").replace("folder", "").replace("app", "").replace("the", "").replace("application", "").strip()

        if is_open and target:
            speak(f"Opening {target}")
            
            # Helper to find folders that might be inside OneDrive on modern Windows
            def get_user_folder(folder_name):
                base = os.path.expanduser('~')
                standard_path = os.path.join(base, folder_name)
                onedrive_path = os.path.join(base, 'OneDrive', folder_name)
                if os.path.exists(onedrive_path) and not os.path.exists(standard_path):
                    return onedrive_path
                return standard_path

            # Explicit Folder & File Manager Routing
            common_folders = {
                "downloads": get_user_folder('Downloads'),
                "documents": get_user_folder('Documents'),
                "desktop": get_user_folder('Desktop'),
                "music": get_user_folder('Music'),
                "pictures": get_user_folder('Pictures'),
                "videos": get_user_folder('Videos'),
                "c drive": "C:\\",
                "d drive": "D:\\",
                "e drive": "E:\\",
                "f drive": "F:\\",
                "file manager": "explorer",
                "file explorer": "explorer",
                "this pc": "explorer ::{20D04FE0-3AEA-1069-A2D8-08002B30309D}",
                "my computer": "explorer ::{20D04FE0-3AEA-1069-A2D8-08002B30309D}"
            }
            
            if target in common_folders:
                try:
                    if common_folders[target].startswith("explorer"):
                        os.system(common_folders[target])
                    else:
                        os.startfile(common_folders[target])
                except FileNotFoundError:
                    speak(f"I couldn't find the exact path for your {target}. Falling back to windows search.")
                    pyautogui.press("win")
                    time.sleep(0.5)
                    pyautogui.write(target)
                    time.sleep(0.5)
                    pyautogui.press("enter")
                return

            # Check all common directories for matching shortcuts, files, or folders
            search_dirs = [
                get_user_folder('Desktop'),
                get_user_folder('Downloads'),
                get_user_folder('Documents'),
                get_user_folder('Pictures'),
                get_user_folder('Music'),
                get_user_folder('Videos')
            ]
            
            found_file = False
            try:
                # 1. Try exact match first (ignoring case)
                for s_dir in search_dirs:
                    if not os.path.exists(s_dir): continue
                    for item in os.listdir(s_dir):
                        item_name_no_ext = os.path.splitext(item)[0].lower()
                        if target == item_name_no_ext:
                            os.startfile(os.path.join(s_dir, item))
                            found_file = True
                            break
                    if found_file: break
                
                # 2. Try partial match if exact match not found
                if not found_file:
                    for s_dir in search_dirs:
                        if not os.path.exists(s_dir): continue
                        for item in os.listdir(s_dir):
                            item_name_no_ext = os.path.splitext(item)[0].lower()
                            if target in item_name_no_ext:
                                os.startfile(os.path.join(s_dir, item))
                                found_file = True
                                break
                        if found_file: break
            except Exception:
                pass

            if found_file:
                return

            # Fall   back for ANY other app: The ultimate trick (WinKey + Type + Enter)
            pyautogui.press("win")
            time.sleep(0.5)
            pyautogui.write(target)
            time.sleep(0.5)
            pyautogui.press("enter")
            return
            
        elif not is_open and target:
            speak(f"Attempting to close {target}")
            # Try killing by matching process name or main window title via PowerShell
            ps_command = f"Get-Process | Where-Object {{($_.Name -match '{target}') -or ($_.MainWindowTitle -match '{target}')}} | Stop-Process -Force"
            os.system(f'powershell -Command "{ps_command}" >nul 2>&1')
            # Also try basic taskkill fallback
            os.system(f'taskkill /f /im {target}.exe >nul 2>&1')
            return
            
        else:
            response = ask_ai(command)
            speak(response)
            return

    # 4. Time and Date
    elif "time" in command and "date" in command:
        now_time = datetime.datetime.now().strftime("%I:%M %p")
        now_date = datetime.datetime.now().strftime("%B %d, %Y")
        speak(f"The time is {now_time} and today's date is {now_date}")

    elif "time" in command:
        now = datetime.datetime.now().strftime("%I:%M %p")
        speak(f"The time is {now}")

    elif "date" in command:
        now_date = datetime.datetime.now().strftime("%B %d, %Y")
        speak(f"Today's date is {now_date}")

    # 5. Smart Dynamic Weather
    elif "weather" in command:
        city = "Bhubaneswar"  # Default city
        if "in " in command:
            # Extract the city name mentioned after the word "in"
            city = command.split("in ")[-1].strip()

        weather_data = get_weather(city)
        if weather_data.startswith("Couldn") or weather_data.startswith("City"):
            speak(f"Sorry, I couldn't fetch the weather for {city}.")
        else:
            speak(f"The weather in {city} is {weather_data}")

    # 5.1 Smart News
    elif "news" in command or "headlines" in command:
        topic = command.replace("tell me", "").replace("the", "").replace("latest", "").replace("news", "").replace("about", "").replace("headlines", "").strip()
        if not topic:
            topic = "world"
        speak(f"Fetching the latest news about {topic} for you.")
        news_data = get_news(topic)
        if isinstance(news_data, list):
            speak("Here are the top headlines:")
            for i, headline in enumerate(news_data):
                speak(f"Headline {i+1}: {headline}")
                time.sleep(0.5)
        else:
            speak(news_data)

    # 5.5. System Diagnostics (CPU, GPU, RAM, Battery, Sound, Network)
    elif any(
        kw in command
        for kw in [
            "system status",
            "cpu",
            "gpu",
            "ram",
            "battery",
            "system percentages",
            "sound",
            "volume",
            "internet",
            "network",
            "wifi",
            "storage",
            "disk",
            "space left",
            "drive",
        ]
    ):
        # Prevent false triggers if asking general questions like "what is a cpu"
        if "what is" not in command and "who is" not in command:
            speak("Checking system vitals...")
            status_parts = []

            # Battery
            if (
                "battery" in command
                or "system" in command
                or "status" in command
                or "all" in command
            ):
                battery = psutil.sensors_battery()
                if battery:
                    plugged = (
                        "plugged in" if battery.power_plugged else "on battery power"
                    )
                    status_parts.append(
                        f"Battery is at {battery.percent} percent and is {plugged}."
                    )
                else:
                    if "battery" in command:
                        status_parts.append(
                            "I couldn't detect a battery on this system."
                        )

            # CPU
            if (
                "cpu" in command
                or "processor" in command
                or "system" in command
                or "status" in command
                or "all" in command
            ):
                cpu_usage = psutil.cpu_percent(
                    interval=1
                )  # small block to measure actual utilization
                status_parts.append(f"CPU usage is at {cpu_usage} percent.")

            # RAM
            if (
                "ram" in command
                or "memory" in command
                or "system" in command
                or "status" in command
                or "all" in command
            ):
                ram = psutil.virtual_memory()
                status_parts.append(f"RAM usage is at {ram.percent} percent.")

            # GPU
            if (
                "gpu" in command
                or "system" in command
                or "status" in command
                or "all" in command
            ):
                try:
                    nvidia_smi = (
                        subprocess.check_output(
                            "nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits",
                            creationflags=subprocess.CREATE_NO_WINDOW,
                        )
                        .decode()
                        .strip()
                    )
                    gpu_usages = nvidia_smi.split("\n")
                    if len(gpu_usages) == 1:
                        status_parts.append(f"GPU usage is at {gpu_usages[0]} percent.")
                    else:
                        for i, usage in enumerate(gpu_usages):
                            status_parts.append(
                                f"GPU {i+1} usage is at {usage} percent."
                            )
                except Exception:
                    if "gpu" in command:
                        status_parts.append("I couldn't fetch discrete GPU details.")

            # Volume
            if (
                "sound" in command
                or "volume" in command
                or "system" in command
                or "status" in command
                or "all" in command
            ):
                try:
                    from pycaw.pycaw import AudioUtilities

                    devices = AudioUtilities.GetSpeakers()
                    volume_interface = devices.EndpointVolume
                    current_vol = round(
                        volume_interface.GetMasterVolumeLevelScalar() * 100
                    )
                    muted = volume_interface.GetMute()
                    if muted:
                        status_parts.append(
                            f"System sound is currently muted (set at {current_vol}%)."
                        )
                    else:
                        status_parts.append(
                            f"System sound is at {current_vol} percent."
                        )
                except Exception:
                    if "sound" in command or "volume" in command:
                        status_parts.append("I couldn't retrieve the sound volume.")

            # Storage / Disk
            if (
                "storage" in command
                or "disk" in command
                or "drive" in command
                or "system" in command
                or "status" in command
                or "all" in command
            ):
                try:
                    for part in psutil.disk_partitions(all=False):
                        if os.name == 'nt' and ('cdrom' in part.opts or part.fstype == ''):
                            continue
                        usage = psutil.disk_usage(part.mountpoint)
                        device_name = part.device.replace('\\', '')
                        status_parts.append(f"Drive {device_name} is at {usage.percent} percent capacity.")
                except Exception:
                    if "storage" in command or "disk" in command:
                        status_parts.append("I couldn't retrieve the storage space details.")

            # Internet/Network
            if (
                "internet" in command
                or "network" in command
                or "wifi" in command
                or "system" in command
                or "status" in command
                or "all" in command
            ):
                try:
                    import socket

                    socket.create_connection(("8.8.8.8", 53), timeout=2)
                    connected = True
                except Exception:
                    connected = False

                if connected:
                    try:
                        output = (
                            subprocess.check_output(
                                'powershell -Command "Get-NetConnectionProfile | Select-Object -ExpandProperty Name"',
                                creationflags=subprocess.CREATE_NO_WINDOW,
                            )
                            .decode()
                            .strip()
                        )
                        if output:
                            # Might be multiple lines if there are multiple active networks, take the first one
                            ssid = output.split("\n")[0].strip()
                            status_parts.append(
                                f"Internet is connected to the network {ssid}."
                            )
                        else:
                            status_parts.append("Internet is connected.")
                    except Exception:
                        status_parts.append("Internet is connected.")
                else:
                    status_parts.append(
                        "The system is currently disconnected from the internet."
                    )

            if status_parts:
                speak(" ".join(status_parts))
            else:
                speak("I am unable to retrieve the system status right now.")
            return

    # 6. Device Control (Iron Man Style)
    elif "shut down" in command or "shutdown pc" in command:
        speak("Warning. Shutting down your PC in 5 seconds.")
        os.system("shutdown /s /t 5")

    elif "restart pc" in command or "restart computer" in command:
        speak("Restarting your system in 5 seconds.")
        os.system("shutdown /r /t 5")

    elif "take screenshot" in command or "take a screenshot" in command:
        filename = f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        pyautogui.screenshot(filename)
        speak("Screenshot captured and saved.")

    elif "lock pc" in command or "lock computer" in command or "lock the system" in command:
        speak("Locking the system.")
        os.system("rundll32.exe user32.dll,LockWorkStation")

    elif "empty recycle bin" in command or "clear recycle bin" in command:
        speak("Emptying the recycle bin.")
        os.system('powershell.exe -NoProfile -Command "Clear-RecycleBin -Confirm:$false"')

    elif "show desktop" in command or "minimize all" in command:
        speak("Minimizing all windows.")
        pyautogui.hotkey("win", "d")

    elif "volume up" in command or "increase volume" in command:
        speak("Increasing volume.")
        for _ in range(5):
            pyautogui.press("volumeup")

    elif "volume down" in command or "decrease volume" in command:
        speak("Decreasing volume.")
        for _ in range(5):
            pyautogui.press("volumedown")

    elif "mute volume" in command or "mute sound" in command or "unmute" in command:
        speak("Toggling mute.")
        pyautogui.press("volumemute")

    # 7. Messaging Services (WhatsApp, Email, SMS)

    elif any(
        kw in command for kw in ["message", "sms", "whatsapp", "email", "text message"]
    ):
        # A. EMAIL BRANCH
        if "email" in command:
            speak(
                "Who should I send the email to? You can say a contact name or an email address."
            )
            recipient_name = listen()

            email_addr = ""
            if recipient_name in CONTACTS and "email" in CONTACTS[recipient_name]:
                email_addr = CONTACTS[recipient_name]["email"]
            else:
                # Clean up spoken emails (e.g. "john at gmail dot com")
                cleaned = (
                    recipient_name.replace(" at ", "@")
                    .replace(" dot ", ".")
                    .replace(" ", "")
                )
                if "@" in cleaned and "." in cleaned:
                    email_addr = cleaned

            if email_addr:
                speak("What is the subject?")
                subject = listen()
                speak("What is the message?")
                body = listen()

                if body:
                    speak(f"Sending email to {email_addr}.")
                    try:
                        import smtplib
                        from email.message import EmailMessage

                        email = EmailMessage()
                        email["From"] = MY_EMAIL
                        email["To"] = email_addr
                        email["Subject"] = subject or "Message from Jarvis"
                        email.set_content(body)

                        server = smtplib.SMTP("smtp.gmail.com", 587)
                        server.starttls()
                        server.login(MY_EMAIL, MY_EMAIL_APP_PASSWORD)
                        server.send_message(email)
                        server.quit()
                        speak("Email sent successfully.")
                    except Exception as e:
                        print("Email Error:", e)
                        speak(
                            "Sir, I couldn't send the email. Please check your App Password or Internet."
                        )
                else:
                    speak("Canceling.")
            else:
                speak("I couldn't identify the email address.")
            return

        # B. SMS/WHATSAPP BRANCH
        if "sms" in command:
            service = "sms"
        else:
            service = "whatsapp"

        speak("Who is the recipient? You can say a contact name or phone number.")
        recipient_name = listen()

        phone = ""
        if recipient_name in CONTACTS and "phone" in CONTACTS[recipient_name]:
            phone = CONTACTS[recipient_name]["phone"]
        else:
            nums = re.sub(r"\D", "", recipient_name)
            if len(nums) >= 10:
                phone = (
                    "+" + nums
                    if not getattr(recipient_name, "startswith", lambda x: False)("+")
                    else recipient_name
                )
                if len(nums) == 10:  # Assume default country code if only 10 digits
                    phone = "+91" + nums

        if phone:
            speak("What is the text message?")
            msg = listen()
            if msg:
                if service == "whatsapp":
                    speak(f"Dispatching WhatsApp message to {phone}.")
                    try:
                        import pywhatkit

                        pywhatkit.sendwhatmsg_instantly(
                            phone, msg, wait_time=15, tab_close=True
                        )
                        speak("WhatsApp message dispatched successfully.")
                    except Exception as e:
                        speak("Failed to dispatch the WhatsApp message.")
                        print("WhatsApp Error:", e)
                else:
                    speak(f"Dispatching cellular SMS to {phone}.")
                    try:
                        # Using Twilio for actual cellular SMS
                        from twilio.rest import Client

                        # USER MUST FILL THESE IN (Free trial at twilio.com)
                        TWILIO_SID = os.getenv("TWILIO_SID")  # noqa
                        TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")  # noqa
                        TWILIO_PHONE = os.getenv(
                            "TWILIO_PHONE"
                        )  # Your provided Twilio Number

                        if not TWILIO_SID or TWILIO_SID == "your_twilio_account_sid":
                            speak(
                                "Sir, your Twilio SMS API keys are not configured in the script. Please update them first."
                            )
                        else:
                            twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)
                            message = twilio_client.messages.create(
                                body=msg, from_=TWILIO_PHONE, to=phone
                            )
                            speak(
                                "SMS dispatched successfully over the cellular network."
                            )
                    except ImportError:
                        speak("Please install the twilio Python package first.")
                    except Exception as e:
                        speak("Failed to dispatch the cellular SMS.")
                        print("SMS Error:", e)
            else:
                speak("Message was empty. Canceling.")
        else:
            speak("I couldn't find that contact or understand the phone number.")

    # 8. Mode Switching
    elif "switch to text mode" in command or "enable text mode" in command or command == "text mode":
        if input_mode != "text":
            try:
                import requests
                requests.post("http://127.0.0.1:5000/api/toggle_f2", timeout=1)
            except Exception:
                pass
        else:
            speak("Sir, we are already in text mode.")
        return

    elif "switch to voice mode" in command or "enable voice mode" in command or command == "voice mode":
        if input_mode != "voice":
            try:
                import requests
                requests.post("http://127.0.0.1:5000/api/toggle_f2", timeout=1)
            except Exception:
                pass
        else:
            speak("Sir, we are already in voice mode.")
        return

    # 9. Fallback to AI
    elif any(command.strip() == kw for kw in ["stop", "shut up", "stop jarvis", "shut up jarvis"]):
        # If 'stop' bled over from speech interruption, just ignore it quietly.
        pass

    else:
        response = ask_ai(command)
        speak(response)


# =========================
# 🚀 MAIN LOOP
# =========================
def run_jarvis():
    import keyboard

    # Register F2 here so it ONLY applies to the main process, preventing duplicate SAPI speak!
    try:
        keyboard.on_release_key("f2", toggle_input_mode)
    except Exception:
        pass

    init_hud()

    hour = datetime.datetime.now().hour
    if 0 <= hour < 12:
        greeting = "Good morning Sir."
    elif 12 <= hour < 17:
        greeting = "Good afternoon Sir."
    elif 17 <= hour < 21:
        greeting = "Good evening Sir."
    else:
        greeting = "Good night Sir."

    speak(f"{greeting} Jarvis is activated. How can I help you?")

    try:
        while True:
            command = listen()

            if command == "":
                continue

            # Exit program
            if command in ["exit", "quit", "shutdown", "close jarvis"] or any(x in command for x in ["exit program", "exit jarvis", "close jarvis"]):
                speak("Goodbye Sir, have a great day", listen_for_stop=False)
                # Give SAPI enough time to actually finish speaking before the python process forcefully hits exit
                time.sleep(3)
                break

            execute_command(command)

    except KeyboardInterrupt:
        print("\n[Jarvis Terminated by User]")


# =========================
# ▶️ START
# =========================
if __name__ == "__main__":
    import sys
    import subprocess
    import os
    import atexit
    multiprocessing.freeze_support()
    
    dashboard_process = None
    
    try:
        # Launch the Graphical UI Dashboard in the background
        dashboard_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard", "server.py")
        if os.path.exists(dashboard_path):
            print("[INFO] Launching J.A.R.V.I.S. Graphical UI...")
            # Hide the backend server console, but the pywebview HUD window will still show up natively
            dashboard_process = subprocess.Popen([sys.executable, dashboard_path], creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000))
            
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
                print("\n=======================================================")
                print(" WEB UI ACCESS (LOCAL PC):   http://127.0.0.1:5000")
                print(f" PHONE ACCESS (LOCAL WI-FI): http://{local_ip}:5000")
                print("=======================================================\n")
            except Exception:
                print("\n=======================================================")
                print(" WEB UI ACCESS: http://127.0.0.1:5000")
                print("=======================================================\n")

            def cleanup_dashboard():
                if dashboard_process:
                    print("[INFO] Terminating HUD Dashboard...")
                    dashboard_process.terminate()
            
            atexit.register(cleanup_dashboard)
    except Exception as e:
        print("[ERROR] Failed to launch UI dashboard:", e)

    run_jarvis()