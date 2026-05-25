import flask
import GPUtil
import psutil
import datetime
import os
import platform
import logging
import subprocess

# Set up logging to avoid flooding the console
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = flask.Flask(__name__, static_folder='static')

try:
    import GPUtil
except ImportError:
    GPUtil = None

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    import pythoncom
except ImportError:
    AudioUtilities = None

cached_weather = "SCANNING WEATHER..."
last_weather_fetch = 0
current_system_state = "IDLE"
current_input_mode = "voice"
current_music = {"song_name": "NO MEDIA PLAYING", "status": "STOPPED"}
interaction_log = [{"type": "system", "text": "SYSTEM INITIALIZED: HUD ONLINE", "time": datetime.datetime.now().strftime("%H:%M:%S")}]


@app.route('/')
def index():
    return flask.send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return flask.send_from_directory('static', path)

@app.route('/api/system')
def system_vitals():
    # Time and Date
    now = datetime.datetime.now()
    current_time = now.strftime("%H:%M:%S")
    current_date = now.strftime("%Y-%m-%d")

    # CPU and RAM
    cpu_usage = psutil.cpu_percent(interval=0)
    ram = psutil.virtual_memory()
    ram_usage = ram.percent
    
    # GPU
    gpu_data = []
    if GPUtil:
        try:
            for gpu in GPUtil.getGPUs():
                gpu_data.append({
                    "id": gpu.id,
                    "name": gpu.name,
                    "load": round(gpu.load * 100),
                    "temp": gpu.temperature
                })
        except Exception as e:
            pass
    if not gpu_data:
        gpu_data = [{"id": 0, "name": "N/A", "load": 0, "temp": 0}]

    # Network Connections
    connections = []
    try:
        conns = psutil.net_connections(kind='inet')
        for c in conns:
            if c.status == 'ESTABLISHED' and c.raddr:
                connections.append(f"{c.raddr.ip}:{c.raddr.port}")
        # Make unique and get up to 5
        connections = list(set(connections))[:5]
    except (psutil.AccessDenied, Exception):
        connections = ["Access Denied / Insufficient Privs"]

    if not connections:
        connections = ["No active external connections"]

    # Volume
    volume_percent = "N/A"
    if AudioUtilities:
        try:
            pythoncom.CoInitialize()
            devices = AudioUtilities.GetSpeakers()
            volume = devices.EndpointVolume
            vol = volume.GetMasterVolumeLevelScalar()
            volume_percent = round(vol * 100)
        except Exception:
            pass
            
    # Disk Usage
    disks_info = []
    try:
        for part in psutil.disk_partitions(all=False):
            if os.name == 'nt' and ('cdrom' in part.opts or part.fstype == ''):
                continue
            usage = psutil.disk_usage(part.mountpoint)
            disks_info.append({
                "device": part.device.replace('\\', ''),
                "percent": usage.percent
            })
    except Exception:
        pass
    
    if not disks_info:
        try:
            disk = psutil.disk_usage('/')
            disks_info = [{"device": "MAIN", "percent": disk.percent}]
        except:
            disks_info = [{"device": "MAIN", "percent": 0}]

    # Battery
    battery = psutil.sensors_battery()
    battery_data = {"percent": 0, "plugged": False}
    if battery:
        battery_data = {"percent": battery.percent, "plugged": battery.power_plugged}

    # Network Name
    network_name = "Disconnected"
    try:
        output = subprocess.check_output(
            'powershell -Command "Get-NetConnectionProfile | Select-Object -ExpandProperty Name"',
            creationflags=0x08000000 # CREATE_NO_WINDOW
        ).decode().strip()
        if output:
            network_name = output.split("\n")[0].strip()
        else:
            # Fallback for older systems or different network setup
            network_name = "Active Network"
    except Exception:
        network_name = "Connected"

    return flask.jsonify({
        "time": current_time,
        "date": current_date,
        "cpu": cpu_usage,
        "ram": ram_usage,
        "gpu": gpu_data,
        "network": connections,
        "volume": volume_percent,
        "os": platform.system() + " " + platform.release(),
        "disks": disks_info,
        "battery": battery_data,
        "network_name": network_name,
        "state": current_system_state,
        "input_mode": current_input_mode,
        "music": current_music,
        "logs": interaction_log
    })

import queue
command_queue = queue.Queue()

def command_worker():
    import pythoncom
    pythoncom.CoInitialize()
    import sys
    import os
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
        
    try:
        import jarvish_
        # Disable background voice listening when commands come from the dashboard
        # to prevent microphone resource conflicts.
        jarvish_.VOICE_INTERRUPTION_ENABLED = False
    except Exception as e:
        print("Backend load error:", e)
        return

    while True:
        cmd = command_queue.get()
        if cmd is None: break
        
        try:
            # Simple heuristic to determine if it's a chat prompt or a discrete command
            is_chat = not any(kw in cmd for kw in [
                "open ", "play ", "weather", "time", "date", 
                "status", "shut down", "message", "news", "screenshot", "close ",
                "cpu", "gpu", "ram", "battery", "sound", "volume", "internet", "network", "wifi"
            ])
            
            # Log the user's text command
            new_entry = {"type": "user", "text": cmd, "time": datetime.datetime.now().strftime("%H:%M:%S")}
            interaction_log.append(new_entry)
            if len(interaction_log) > 10: interaction_log.pop(0)

            if cmd in ["exit", "quit", "shutdown", "close jarvis"]:
                j_entry = {"type": "jarvis", "text": "Goodbye Sir, have a great day", "time": datetime.datetime.now().strftime("%H:%M:%S")}
                interaction_log.append(j_entry)
                jarvish_.speak("Goodbye Sir, have a great day")
                try:
                    import psutil
                    parent = psutil.Process(os.getppid())
                    parent.terminate()
                except Exception:
                    pass
                os._exit(0)

            if is_chat:
                res = jarvish_.ask_ai(cmd)
                
                # Log Jarvis's response
                j_entry = {"type": "jarvis", "text": res, "time": datetime.datetime.now().strftime("%H:%M:%S")}
                interaction_log.append(j_entry)
                if len(interaction_log) > 10: interaction_log.pop(0)

                jarvish_.speak(res)
            else:
                jarvish_.execute_command(cmd)
        except Exception as e:
            print("Command execution error:", e)
        command_queue.task_done()

import threading
threading.Thread(target=command_worker, daemon=True).start()

@app.route('/api/command', methods=['POST'])
def handle_command():
    from flask import request
    data = request.get_json()
    command = data.get('command', '').lower().strip()
    
    if command:
        command_queue.put(command)
        reply = f"Delivered: {command}"
    else:
        reply = "Empty transmission ignored."
    
    return flask.jsonify({"response": reply})

@app.route('/api/status', methods=['POST'])
def set_status():
    global current_system_state
    from flask import request
    data = request.get_json()
    current_system_state = data.get('state', 'IDLE')
    return flask.jsonify({"status": "updated"})

@app.route('/api/mode', methods=['POST'])
def update_mode():
    global current_input_mode
    from flask import request
    data = request.get_json()
    current_input_mode = data.get('mode', 'voice')
    return flask.jsonify({"status": "updated"})

@app.route('/api/tts_engine', methods=['POST'])
def update_tts_engine():
    from flask import request
    data = request.get_json()
    engine = data.get('engine', 'sapi')
    try:
        import sys
        import os
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.append(parent_dir)
        import jarvish_
        jarvish_.TTS_ENGINE = engine
    except Exception as e:
        print("Error updating TTS engine:", e)
    return flask.jsonify({"status": "updated"})

@app.route('/api/music', methods=['POST'])
def update_music():
    global current_music
    from flask import request
    data = request.get_json()
    current_music["song_name"] = data.get("song_name", "NO MEDIA PLAYING")
    current_music["status"] = data.get("status", "STOPPED")
    return flask.jsonify({"status": "updated"})

@app.route('/api/toggle_f2', methods=['POST'])
def toggle_f2():
    import keyboard
    keyboard.send("f2")
    return flask.jsonify({"status": "f2_sent"})

@app.route('/api/log', methods=['POST'])
def add_log():
    global interaction_log
    from flask import request
    try:
        data = request.get_json()
        if not data:
            return flask.jsonify({"error": "No data received"}), 400
            
        new_entry = {
            "type": data.get("type", "user"),
            "text": data.get("text", ""),
            "time": datetime.datetime.now().strftime("%H:%M:%S")
        }
        print(f"[HUD-LOG] {new_entry['type'].upper()}: {new_entry['text']}")
        interaction_log.append(new_entry)
        if len(interaction_log) > 15: # Increased history slightly
            interaction_log.pop(0)
        return flask.jsonify({"status": "logged"})
    except Exception as e:
        print(f"[ERR] Logging failure: {e}")
        return flask.jsonify({"error": str(e)}), 500

def run_flask():
    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)

if __name__ == '__main__':
    print("Starting J.A.R.V.I.S. Core Systems Server...")
    
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        print(f"\n=======================================================")
        print(f" WEB UI ACCESS (LOCAL PC):   http://127.0.0.1:5000")
        print(f" PHONE ACCESS (LOCAL WI-FI): http://{local_ip}:5000")
        try:
            from pyngrok import ngrok
            public_url = ngrok.connect(5000, bind_tls=True).public_url
            print(f" PHONE ACCESS (ANYWHERE):    {public_url}")
        except Exception as e:
            print(f" (Anywhere access error: {e})")
        print(f"=======================================================\n")
    except Exception:
        pass

    import threading
    import time
    
    # Run the Flask app in a separate background thread
    server_thread = threading.Thread(target=run_flask)
    server_thread.daemon = True
    server_thread.start()
    
    # Wait a moment for the server to start
    time.sleep(1)
    
    try:
        import webview
        print("Opening Dashboard in Python UI Window...")
        
        # Make Jarvis Speak when UI opens
        def speak_greeting():
            import time
            time.sleep(1.5) # Wait for the UI window to render first
            try:
                import win32com.client
                speaker = win32com.client.Dispatch("SAPI.SpVoice")
                # Voice customization (if available) SAPI usually has multiple voices, but default works
                speaker.Speak("J.A.R.V.I.S. visual interface is online. All core systems operating at nominal capacity.")
            except Exception as e:
                print("Speech error:", e)
                
        # Start voice greeting in parallel so it doesn't block UI load
        threading.Thread(target=speak_greeting, daemon=True).start()

        # Create a native Python window displaying the web dashboard
        webview.create_window(
            'J.A.R.V.I.S. Systems Dashboard', 
            'http://127.0.0.1:5000/', 
            width=1280, 
            height=800, 
            background_color='#03050a'
        )
        webview.start()
    except ImportError:
        print("pywebview not installed. Opening in default web browser instead...")
        import webbrowser
        webbrowser.open('http://127.0.0.1:5000/')
        while True:
            time.sleep(1)
