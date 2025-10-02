import streamlit as st
import serial
import serial.tools.list_ports
import time

# Function to get available ports
def get_available_ports():
    ports = list(serial.tools.list_ports.comports())
    port_dict = {}
    
    for port in ports:
        # Create nice display name with description
        if port.description and port.description != "n/a":
            display_name = f"{port.device}: {port.description}"
        else:
            display_name = port.device
            
        port_dict[display_name] = port.device
    
    return port_dict

# Initialize session state
if "serial_data" not in st.session_state:
    st.session_state.serial_data = []

if "connected" not in st.session_state:
    st.session_state.connected = False

if "port" not in st.session_state:
    st.session_state.port = ""

# Function to clear the console
def clear_console():
    st.session_state.serial_data = []

# Page setup
st.set_page_config(page_title="STM32 Monitor", layout="wide")
st.title("📟 STM32L475 Serial Monitor")

# Sidebar for connection settings
with st.sidebar:
    st.header("Connection Settings")
    
    # Port selection
    port_dict = get_available_ports()
    
    if not port_dict:
        st.warning("No serial ports found")
        selected_port = ""
    else:
        # Look for STM32 device in ports
        stm32_port = None
        for display_name, port in port_dict.items():
            if "STM32" in display_name or "usbmodem" in display_name:
                stm32_port = display_name
                break
        
        # Select port from dropdown
        selected_display = st.selectbox(
            "Select Port", 
            options=list(port_dict.keys()),
            index=list(port_dict.keys()).index(stm32_port) if stm32_port else 0
        )
        
        selected_port = port_dict[selected_display]
        st.session_state.port = selected_port
    
    # Baud rate selection
    baud_rate = st.selectbox("Baud Rate", options=[9600, 115200, 57600, 38400, 19200, 4800])
    
    # Connect/Disconnect button
    if not st.session_state.connected:
        if st.button("Connect", type="primary", use_container_width=True):
            try:
                # Try to establish connection
                st.session_state.ser = serial.Serial(selected_port, baud_rate, timeout=0.5)
                st.session_state.connected = True
                st.session_state.serial_data.append(f"Connected to {selected_port} at {baud_rate} baud")
            except Exception as e:
                st.error(f"Cannot connect: {e}")
    else:
        if st.button("Disconnect", type="primary", use_container_width=True):
            if hasattr(st.session_state, 'ser'):
                st.session_state.ser.close()
            st.session_state.connected = False
            st.session_state.serial_data.append("Disconnected")
    
    # Clear and refresh buttons
    col1, col2 = st.columns(2)
    with col1:
        st.button("Clear Console", on_click=clear_console, use_container_width=True)
    with col2:
        if st.button("Refresh Ports", use_container_width=True):
            st.rerun()
    
    # Connection status
    if st.session_state.connected:
        st.success(f"Connected to {st.session_state.port}")
    else:
        st.warning("Not connected")

# Main area for console output
st.subheader("Console Output")
console = st.empty()

# Auto scroll toggle
auto_scroll = st.checkbox("Auto-scroll", value=True)

# Display console output
if st.session_state.serial_data:
    console.code("\n".join(st.session_state.serial_data), language="")
else:
    console.info("No data yet. Please connect to start monitoring.")

# Read data when connected
if st.session_state.connected and hasattr(st.session_state, 'ser'):
    try:
        ser = st.session_state.ser
        if ser.in_waiting > 0:
            raw = ser.readline()
            if raw:
                line = raw.decode("utf-8", "ignore").rstrip()
                if line:
                    st.session_state.serial_data.append(line)
                    # Keep only last 500 lines
                    if len(st.session_state.serial_data) > 500:
                        st.session_state.serial_data = st.session_state.serial_data[-500:]
                    
                    # Update display
                    console.code("\n".join(st.session_state.serial_data), language="")
    except Exception as e:
        st.error(f"Error reading serial data: {e}")
        st.session_state.connected = False
        if hasattr(st.session_state, 'ser'):
            try:
                st.session_state.ser.close()
            except:
                pass

# Auto-rerun for updates
if st.session_state.connected:
    time.sleep(0.1)
    st.rerun()

# Add a small delay to reduce CPU usage even when not connected
time.sleep(0.1)