import streamlit as st
# Must be the first Streamlit command
st.set_page_config(page_title="STM32L475 Monitor", page_icon="📊", layout="wide")

import serial
import serial.tools.list_ports
import time
import threading
import os
import platform
import json
from datetime import datetime

# Force page refresh using HTML meta tag
st.markdown(
    """
    <meta http-equiv="refresh" content="3">
    """,
    unsafe_allow_html=True
)

# Store data in a file so it persists between Streamlit refreshes
DATA_FILE = "serial_data.json"

# Initialize or load state from disk
if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            buffer = data.get('buffer', [])
            is_connected = data.get('is_connected', False)
            error_message = data.get('error_message', None)
            tremor_count = data.get('tremor_count', 0)
            dyskinesia_count = data.get('dyskinesia_count', 0)
            normal_count = data.get('normal_count', 0)
            last_updated = data.get('last_updated', str(datetime.now()))
    except Exception as e:
        # If the file is corrupted, start fresh
        print(f"Error loading data: {e}")
        buffer = []
        is_connected = False
        error_message = None
        tremor_count = 0
        dyskinesia_count = 0
        normal_count = 0
        last_updated = str(datetime.now())
else:
    # Initial state
    buffer = []
    is_connected = False
    error_message = None
    tremor_count = 0
    dyskinesia_count = 0
    normal_count = 0
    last_updated = str(datetime.now())

# Global flag for stopping the thread
stop_thread = False

# Function to save state to disk
def save_state():
    data = {
        'buffer': buffer,
        'is_connected': is_connected,
        'error_message': error_message,
        'tremor_count': tremor_count,
        'dyskinesia_count': dyskinesia_count,
        'normal_count': normal_count,
        'last_updated': str(datetime.now())
    }
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

# --- Styling ---
st.markdown("""
<style>
.main-header {
 font-size: 2.5rem;
 font-weight: 600;
 margin-bottom: 1rem;
 color: #4CAF50;
}
.status-ok {
 padding: 0.5rem;
 border-radius: 4px;
 background-color: rgba(76, 175, 80, 0.2);
 border: 1px solid #4CAF50;
}
.status-warning {
 padding: 0.5rem;
 border-radius: 4px;
 background-color: rgba(255, 152, 0, 0.2);
 border: 1px solid #FF9800;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">📊 STM32L475 Movement Disorder Monitor</h1>', unsafe_allow_html=True)

# The monitor thread that runs in the background independently from Streamlit
def serial_monitor_process(port, baud_rate):
    global buffer, is_connected, error_message, tremor_count, dyskinesia_count, normal_count, stop_thread
    
    try:
        print(f"Opening serial port {port} at {baud_rate} baud")
        with serial.Serial(port, baud_rate, timeout=1) as ser:
            is_connected = True
            buffer.append(f"✅ Connected to {port} at {baud_rate} baud")
            save_state()
            
            print("Connection successful, starting reading loop")
            
            while not stop_thread:
                if ser.in_waiting > 0:
                    raw_data = ser.readline()
                    if raw_data:
                        line = raw_data.decode("utf-8", "ignore").strip()
                        if line:
                            print(f"Data received: {line}")
                            buffer.append(line)
                            
                            # Update counts based on the line content
                            if "Tremor detected" in line:
                                tremor_count += 1
                            elif "Dyskinesia detected" in line:
                                dyskinesia_count += 1
                            elif "No movement disorder detected" in line:
                                normal_count += 1
                            
                            # Keep buffer at a reasonable size
                            if len(buffer) > 100:
                                buffer = buffer[-100:]
                            
                            # Save state after each new data
                            save_state()
                            
                time.sleep(0.1)
    
    except Exception as e:
        error_message = f"Serial Error: {e}"
        print(f"Error in serial thread: {e}")
        save_state()
    
    finally:
        is_connected = False
        buffer.append("Disconnected from serial port")
        save_state()
        print("Serial thread exited")

# --- Get Serial Ports ---
def get_available_ports():
    return list(serial.tools.list_ports.comports())

def is_stm32_device(port):
    return 'STM' in port.description or 'STLink' in port.description or 'ST-LINK' in port.description

# --- Sidebar UI ---
st.sidebar.header("Connection Settings")

ports = get_available_ports()
stm32_ports = [p for p in ports if is_stm32_device(p)]

if stm32_ports:
    st.sidebar.markdown(
        f'<div class="status-ok">STM32 device detected:<br/><strong>{stm32_ports[0].device}</strong></div>', 
        unsafe_allow_html=True
    )
else:
    st.sidebar.markdown(
        '<div class="status-warning">No STM32 device detected.</div>', 
        unsafe_allow_html=True
    )

# Port selection
port_options = [p.device for p in ports]
if port_options:
    port_labels = [f"{p.device} ({p.description})" for p in ports]
    default_index = 0
    if stm32_ports:
        try:
            default_index = port_options.index(stm32_ports[0].device)
        except ValueError:
            pass
    
    selected_port = st.sidebar.selectbox(
        "Select Port", 
        options=port_options,
        index=default_index,
        format_func=lambda x: next((l for p, l in zip(port_options, port_labels) if p == x), x)
    )
else:
    st.sidebar.error("No serial ports available")
    selected_port = None

baud_rate = st.sidebar.selectbox("Baud Rate", [115200, 9600, 57600, 38400, 19200, 4800], index=0)

if st.sidebar.button("Clear Console"):
    buffer.clear()
    tremor_count = 0
    dyskinesia_count = 0
    normal_count = 0
    save_state()
    st.rerun()

# --- Main Layout ---
col1, col2 = st.columns([7, 3])

with col1:
    if is_connected:
        st.success(f"Connected and receiving data")
    else:
        st.info("Not connected to any device")
    
    if error_message:
        st.error(error_message)
    
    st.subheader("Serial Monitor")
    
    # Display buffer content
    if buffer:
        st.text_area("Raw Output", "\n".join(buffer), height=400, disabled=True)
    else:
        st.info("No data received yet. Start monitoring to view data.")

with col2:
    st.subheader("Detection Statistics")
    
    # Statistics cards
    st.metric("Tremor Events", tremor_count)
    st.metric("Dyskinesia Events", dyskinesia_count)
    st.metric("Normal Readings", normal_count)
    
    # Simple bar chart
    if tremor_count > 0 or dyskinesia_count > 0 or normal_count > 0:
        chart_data = {
            "Tremor": tremor_count,
            "Dyskinesia": dyskinesia_count, 
            "Normal": normal_count
        }
        st.bar_chart(chart_data)

# --- Monitoring Controls ---
if not is_connected:
    if st.button("Start Monitoring", type="primary", use_container_width=True):
        if selected_port:
            # Reset global variables
            error_message = None
            stop_thread = False
            
            # Start monitoring thread
            buffer.append(f"Starting connection to {selected_port}...")
            save_state()
            
            # Create and start thread
            thread = threading.Thread(
                target=serial_monitor_process,
                args=(selected_port, baud_rate)
            )
            thread.daemon = True
            thread.start()
            
            # Wait a moment for the thread to start
            time.sleep(1)
            st.rerun()
        else:
            st.error("Please select a serial port")
else:
    if st.button("Stop Monitoring", type="secondary", use_container_width=True):
        stop_thread = True
        buffer.append("Stopping monitoring...")
        save_state()
        st.rerun()

# --- About Section ---
st.markdown("---")
st.subheader("About STM32L475 Movement Disorder Monitor")
st.markdown("""
This application connects to an STM32L475 Discovery IoT device programmed to detect movement disorders
using accelerometer data. The device samples motion at 104Hz and uses FFT analysis to identify:

- **Tremors**: Rhythmic oscillations between 3-5 Hz
- **Dyskinesia**: Involuntary movements between 5-7 Hz

The STM32 processes data in real-time and sends detection results through the serial port.
""")

# --- Debugging Tools ---
with st.expander("Debug Info", expanded=True):
    st.write("Connected:", is_connected)
    st.write("Error:", error_message)
    st.write("Selected Port:", selected_port)
    st.write("Baud Rate:", baud_rate)
    st.write("Data Count:", len(buffer))
    st.write("Last Updated:", last_updated)
    st.write("Stop Flag:", stop_thread)
    
    if st.button("Force Refresh"):
        st.rerun()
    
    if st.button("Inject Test Data"):
        buffer.extend([
            "TEST: Collecting samples...",
            "TEST: Analyzing data...",
            "TEST: No movement disorder detected (T: 123, D: 456)"
        ])
        normal_count += 1
        save_state()
        st.rerun()