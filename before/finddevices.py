import serial
import time

# --- Configuration ---
# Replace 'COM3' with the port number you find in the device manager
SERIAL_PORT = 'COM17' 
# Make sure the baud rate matches the one set in your HC-06 module
BAUD_RATE = 115200
# -----------------------------
def find_devices():
    try:
        print(f"Connecting to {SERIAL_PORT} at {BAUD_RATE} baud...")
        # Create a serial connection object
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

        # Wait a moment to ensure the connection is established
        time.sleep(2)

        if ser.is_open:
            print("Connection successful!")

            # Prepare the message to send (must be a bytes object)

            # Send the message  to the serial device
            message_to_send = b'Hello from Python!\n'  # Example message

            # Send the message
            ser.write(message_to_send)
            
            print(f" {message_to_send.decode().strip()} has been sent.")

            # Close the connection
            ser.close()
            print("Connection closed.")
        else:
            print("Unable to open serial port.")

    except serial.SerialException as e:
        print(f"Error: {e}")
        print("Please check the COM port number and make sure the device is turned on.")
        print("请检查 COM 端口号是否正确，以及设备是否已开机。")