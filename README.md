# J.A.R.V.I.S. Core Systems & UI Dashboard

An advanced, multi-threaded AI voice assistant with a real-time web-based visual dashboard. 

## 🚀 Features
* **Interactive UI Dashboard**: A Flask-based web interface showing real-time system telemetry (CPU, RAM, GPU, Battery, Network, Volume, and comprehensive Drive Storage usage).
* **Multi-Engine Speech Processing**: Seamlessly toggle between SAPI (Native Windows), Pyttsx3, and gTTS for voice output. Includes robust interruption capabilities (say "Stop Jarvis").
* **Intelligent NLP**: Integrated with DeepSeek AI (via OpenRouter) for dynamic, conversational responses.
* **Advanced OS Control**: 
  * Smart process termination via PowerShell (say "Close [App Name]").
  * Global system controls (say "Lock PC", "Minimize All", "Empty Recycle Bin", "Volume Up/Down/Mute").
* **Universal File Opener**: Native indexing of personal folders (Desktop, Downloads, Documents, etc.) to instantly open any file or folder natively. Automatically falls back to Windows Search for unrecognized apps.
* **Offline Fallbacks**: Uses Google Speech Recognition primarily, with automatic fallbacks to Vosk to ensure continuous operation.
* **Automated Services**: Capable of sending emails, WhatsApp messages (`pywhatkit`), SMS/Calls (`twilio`), controlling media playback (`vlc`, `yt-dlp`), and fetching weather/news.

## 🛠️ Installation

1. **Install Python**: Ensure you have Python 3.8+ installed on your system.
2. **Install Dependencies**: Run the following command in your terminal:
   ```bash
   pip install -r requirements.txt
   ```
3. **Environment Variables**: Create a `.env` file in the root directory and add your API keys:
   ```env
   OPENROUTER_API_KEY=your_openrouter_api_key
   OPENWEATHER_API_KEY=your_weather_api_key
   NEWS_API_KEY=your_news_api_key
   MY_EMAIL=your_email@gmail.com
   MY_EMAIL_APP_PASSWORD=your_app_password
   TWILIO_SID=your_twilio_sid
   TWILIO_AUTH_TOKEN=your_twilio_token
   TWILIO_PHONE_NUMBER=your_twilio_number
   MY_PHONE_NUMBER=your_actual_number
   ```

## ▶️ How to Run

To start the J.A.R.V.I.S. system, simply execute the main python script from your terminal:

```bash
python jarvish_.py
```

* The visual dashboard will automatically launch.
* You can access the UI remotely via your phone using the Local IP link printed in the terminal.
* Press `F2` at any time to seamlessly toggle between Voice Input and Text Input modes.