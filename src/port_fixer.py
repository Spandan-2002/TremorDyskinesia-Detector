#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import signal
import serial
import serial.tools.list_ports

def get_user_sudo():
    """Ask for sudo password if not already running with sudo"""
    if os.geteuid() != 0:
        print("This script needs sudo privileges to fix port issues.")
        try:
            subprocess.check_call(['sudo', 'echo', 'Sudo access granted'])
            return True
        except:
            print("Failed to get sudo access.")
            return False
    return True

def list_ports():
    """List all available serial ports"""
    ports = list(serial.tools.list_ports.comports())
    print(f"Found {len(ports)} serial ports:")
    for i, port in enumerate(ports):
        print(f"{i+1}. {port.device}: {port.description}")
    return [p.device for p in ports]

def find_processes_using_port(port_name):
    """Find processes that might be using the given port"""
    processes = []
    
    try:
        if sys.platform.startswith('darwin'):  # macOS
            cmd = ['lsof', '-t', port_name]
            output = subprocess.check_output(cmd, universal_newlines=True).strip()
            if output:
                pids = output.split('\n')
                for pid in pids:
                    try:
                        proc_cmd = ['ps', '-p', pid, '-o', 'comm=']
                        proc_name = subprocess.check_output(proc_cmd, universal_newlines=True).strip()
                        processes.append((pid, proc_name))
                    except:
                        processes.append((pid, "Unknown"))
        
        elif sys.platform.startswith('linux'):  # Linux
            cmd = ['fuser', port_name]
            try:
                output = subprocess.check_output(cmd, universal_newlines=True).strip()
                if output:
                    pids = output.split()
                    for pid in pids:
                        try:
                            proc_cmd = ['ps', '-p', pid, '-o', 'comm=']
                            proc_name = subprocess.check_output(proc_cmd, universal_newlines=True).strip()
                            processes.append((pid, proc_name))
                        except:
                            processes.append((pid, "Unknown"))
            except:
                pass  # fuser might not be installed
        
        elif sys.platform.startswith('win'):  # Windows
            # Windows requires more complex handling, just a simplified version here
            print("On Windows, please use Task Manager to find and end processes using the port.")
    except Exception as e:
        print(f"Error finding processes: {e}")
    
    return processes

def fix_port_permissions(port_name):
    """Fix permissions for the port"""
    if sys.platform.startswith('win'):
        print("On Windows, port permissions are usually handled by device drivers.")
        return False
    
    try:
        if os.path.exists(port_name):
            # Change permissions to allow read/write for everyone
            os.system(f'sudo chmod 666 {port_name}')
            print(f"Changed permissions for {port_name} to allow read/write access")
            return True
        else:
            print(f"Port {port_name} does not exist as a file")
            return False
    except Exception as e:
        print(f"Error fixing permissions: {e}")
        return False

def kill_process(pid):
    """Kill a process by its PID"""
    try:
        os.kill(int(pid), signal.SIGTERM)
        print(f"Successfully terminated process {pid}")
        return True
    except Exception as e:
        print(f"Error killing process {pid}: {e}")
        print("Trying with sudo...")
        try:
            os.system(f'sudo kill {pid}')
            print(f"Sent kill signal to {pid} with sudo")
            return True
        except:
            return False

def test_port_connection(port_name, baud_rate=9600):
    """Test if we can open and close the port"""
    try:
        print(f"Testing connection to {port_name}...")
        ser = serial.Serial(port_name, baud_rate, timeout=1)
        print("Successfully opened port")
        ser.close()
        print("Successfully closed port")
        return True
    except Exception as e:
        print(f"Error testing port: {e}")
        return False

def monitor_port(port_name, baud_rate=9600, duration=10):
    """Monitor the port for a short duration to verify it's working"""
    try:
        print(f"\nMonitoring {port_name} for {duration} seconds...")
        with serial.Serial(port_name, baud_rate, timeout=0.1) as ser:
            end_time = time.time() + duration
            received_data = False
            
            while time.time() < end_time:
                try:
                    data = ser.readline()
                    if data:
                        received_data = True
                        print(f"Data: {data.decode('utf-8', errors='replace').strip()}")
                    time.sleep(0.05)
                except serial.SerialException as e:
                    print(f"Error during monitoring: {e}")
                    return False
            
            if not received_data:
                print("No data received during monitoring period.")
            return received_data
    except Exception as e:
        print(f"Error setting up monitoring: {e}")
        return False

def main():
    """Main function to fix port issues"""
    print("\n=== Serial Port Fixer ===\n")
    
    # List available ports
    available_ports = list_ports()
    
    if not available_ports:
        print("No serial ports detected. Please check your device connection.")
        return 1
    
    # Get port selection from user
    port_index = 0
    if len(available_ports) > 1:
        try:
            port_index = int(input(f"Select port number (1-{len(available_ports)}): ")) - 1
            if port_index < 0 or port_index >= len(available_ports):
                print("Invalid selection, using first port.")
                port_index = 0
        except:
            print("Invalid input, using first port.")
            port_index = 0
    
    port_name = available_ports[port_index]
    print(f"\nSelected port: {port_name}")
    
    # Check for processes using the port
    print("\nChecking for processes using the port...")
    processes = find_processes_using_port(port_name)
    
    if processes:
        print(f"Found {len(processes)} processes using {port_name}:")
        for pid, name in processes:
            print(f"PID: {pid}, Name: {name}")
        
        kill_them = input("\nWould you like to terminate these processes? (y/n): ").lower()
        if kill_them == 'y':
            for pid, _ in processes:
                kill_process(pid)
            print("Waiting for processes to terminate...")
            time.sleep(2)
    else:
        print("No processes found to be using the port.")
    
    # Fix port permissions
    print("\nAttempting to fix port permissions...")
    if sys.platform.startswith('darwin') or sys.platform.startswith('linux'):
        sudo_access = get_user_sudo()
        if sudo_access:
            fixed = fix_port_permissions(port_name)
            if fixed:
                print("Port permissions updated successfully.")
            else:
                print("Could not update port permissions.")
        else:
            print("Skipping permission fix due to lack of sudo access.")
    
    # Test port connection
    print("\nTesting port connection...")
    baud_rate = input("Enter baud rate [9600]: ").strip()
    if not baud_rate:
        baud_rate = 9600
    else:
        baud_rate = int(baud_rate)
    
    if test_port_connection(port_name, baud_rate):
        print("\nPort connection test successful!")
        
        # Ask if user wants to monitor
        monitor = input("\nWould you like to monitor the port for 10 seconds? (y/n): ").lower()
        if monitor == 'y':
            success = monitor_port(port_name, baud_rate)
            if success:
                print("\nMonitoring successful! Your port is working correctly.")
            else:
                print("\nMonitoring completed, but no data was received.")
        
        print("\nTry using this port in your Streamlit app now.")
    else:
        print("\nPort connection test failed.")
        print("Please try:");
        print("1. Unplugging and reconnecting your device")
        print("2. Restarting your computer")
        print("3. Checking device drivers")
        print("4. Using a different USB port")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())