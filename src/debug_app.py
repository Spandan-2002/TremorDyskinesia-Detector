import streamlit as st
import serial
import serial.tools.list_ports
import time
import os

# Function to get available ports with detailed info
def get_available_ports():
    ports = list(serial.tools.list_ports.comports())
    return ports

# Initialize session state
if "serial_data" not in st.session_state:
    st.session_state.serial_data = []

# Function to clear the console
def clear_console():
    st.session_state.serial_data = []

# Page setup
st.set_page_config(page_title="STM32 Debug Console", layout="wide")
st.title("📟 STM32L475 Serial Console Debugger")

# Sidebar for connection settings
with st.sidebar:
    st.header("Connection Settings")
    
    # Port detection and selection
    ports = get_available_ports()
    
    if not ports:
        st.warning("No serial ports found")
        st.session_state.port = ""
    else:
        # Display detailed port information
        st.subheader("Available Ports")
        for i, port in enumerate(ports):
            with st.expander(f"{port.device}"):
                st.write(f"Name: {port.name}")
                st.write(f"Description: {port.description}")
                st.write(f"Hardware ID: {port.hwid}")
                if hasattr(port, 'manufacturer'):
                    st.write(f"Manufacturer: {port.manufacturer}")
        
        # Manual port entry option
        st.divider()
        manual_port = st.text_input("Manual Port Entry", 
                                   value="/dev/tty.debug-console", 
                                   help="Enter port exactly as shown in terminal")
        
        # Port selection from dropdown
        port_names = [p.device for p in ports]
        selected_port = st.selectbox("Select Port", 
                                    options=port_names,
                                    index=0 if port_names else None)
        
        # Use manual entry or dropdown selection
        use_manual = st.checkbox("Use manual entry", value=True)
        st.session_state.port = manual_port if use_manual else selected_port
    
    # Baud rate selection
    st.session_state.baud_rate = st.selectbox("Baud Rate", 
                                             options=[9600, 115200, 57600, 38400, 19200, 4800])
    
    # Clear console button
    st.button("Clear Console", on_click=clear_console)
    
    # Refresh ports button
    if st.button("Refresh Ports"):
        st.rerun()

# Main area for console output
st.subheader("Console Output")

# Direct connection attempt button
if st.button("Connect and Monitor", use_container_width=True):
    if not st.session_state.port:
        st.error("Please select a serial port")
    else:
        try:
            with serial.Serial(st.session_state.port, st.session_state.baud_rate, timeout=0.5) as ser:
                st.success(f"Connected to {st.session_state.port} at {st.session_state.baud_rate} baud")
                placeholder = st.empty()
                
                # Continuously read and update
                stop_button = st.button("Stop Monitoring")
                while not stop_button:
                    try:
                        raw = ser.readline()
                        if raw:
                            line = raw.decode("utf-8", "ignore").rstrip()
                            if line:
                                st.session_state.serial_data.append(line)
                                # Limit the buffer size
                                if len(st.session_state.serial_data) > 500:
                                    st.session_state.serial_data = st.session_state.serial_data[-500:]
                        
                        # Update the display
                        placeholder.code("\n".join(st.session_state.serial_data), language="")
                        time.sleep(0.1)
                        
                        # Check if stop was pressed
                        stop_button = st.button("Stop Monitoring")
                        
                    except serial.SerialException:
                        st.error("Serial connection lost")
                        break
        
        except Exception as e:
            st.error(f"Cannot connect to {st.session_state.port}: {e}")
            
            # Provide debugging help
            with st.expander("Debugging Help"):
                st.write("Try these steps:")
                st.write("1. Check if the port is already open in another program")
                st.write("2. Verify you have permission to access the port")
                st.write("3. Try using the exact port name from your terminal")
                st.write("4. On macOS, ports often start with '/dev/tty.'")
                st.write("5. On Windows, ports use 'COM' format (e.g., COM3)")
                st.write("6. On Linux, ports are typically '/dev/ttyACM0' or similar")
                
                # Show environment info
                st.subheader("System Information")
                st.write(f"Operating System: {os.name}")
                try:
                    st.write(f"Platform: {os.uname().sysname}")
                except:
                    st.write("Platform info not available")

# Show existing data even when not monitoring
if st.session_state.serial_data:
    st.code("\n".join(st.session_state.serial_data), language="")
else:
    st.info("No data yet. Click 'Connect and Monitor' to begin")

# Test section for direct port access
st.divider()
st.subheader("Direct Port Test")
test_text = """
This section allows you to test if your port is accessible.
Enter the exact port name and it will try a quick open/close test.
"""
st.write(test_text)

col1, col2 = st.columns([3, 1])
with col1:
    test_port = st.text_input("Test Port", value=st.session_state.port)
with col2:
    if st.button("Test Port"):
        try:
            # Just try to open and close
            ser = serial.Serial(test_port, 9600)
            ser.close()
            st.success(f"Successfully opened and closed {test_port}")
        except Exception as e:
            st.error(f"Cannot access {test_port}: {e}")