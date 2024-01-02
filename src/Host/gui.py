import tkinter as tk
from tkinter import Misc, ttk, messagebox
from serial import Serial, SerialException
from serial.tools.list_ports import comports
from serial.tools.list_ports_common import ListPortInfo
import logging
from typing import Callable
import settings
from calibration import calibration


class main:
    def __init__(self) -> None:
        # Load settings from settings.json
        settings.load_saved_settings()

        # Set up the main window
        self.root = tk.Tk()
        self.root.wm_title("BMS Test Board Control")
        self.root.grid()
        
        # Create tab container
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=0, column=0)
        
        # Add tabs to the main view
        # Connect
        self.tab_connect = view_connect(self.notebook, self.update_tab_selectable_state)
        self.notebook.add(self.tab_connect.frm, text="Connect")
        # Calibration
        self.tab_calibration = view_calibration(self.notebook)
        self.notebook.add(self.tab_calibration.frm, text="Calibration")
        
        # Make tabs selectable only once the relevant conditions are met
        self.update_tab_selectable_state()
        
        # Register shutdown tasks
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown_tasks)
        
        # Start the GUI
        self.root.mainloop()
    
    
    def update_tab_selectable_state(self):
        # Check to see if a test board is connected
        connected = self.tab_connect.test_board_connected
        
        # Update notebook tab availability accordingly
        if connected:
            for tab_idx in range(1, len(self.notebook.tabs())):
                self.notebook.tab(tab_idx, state="normal")
        else:
            for tab_idx in range(1, len(self.notebook.tabs())):
                self.notebook.tab(tab_idx, state="disabled")
    
    
    def shutdown_tasks(self):
        self.tab_connect.disconnect_from_test_board
        self.root.destroy()


class view():
    def __init__(self, master: Misc | None) -> None:
        # Create a frame to place graphical elements within
        self.frm = ttk.Frame(master, padding=10)
        self.frm.grid()


class view_connect(view):
    """Tab to connect to a target BMS test board for testing
    """
    
    def __init__(self, master: Misc | None, callback_connect_disconnect: Callable[[], None]) -> None:
        super().__init__(master=master)
        self.callback_connect_disconnect = callback_connect_disconnect
        
        # Show the connection status in a label at the top of this screen (always start disconnected)
        self._connection_status_label = ttk.Label(self.frm)
        self._connection_status_label.grid(column=0, columnspan=3, row=0, pady=(0, 10))
        self.ser = None
        
        # Show a list of all potentially relevant devices to connect to
        ttk.Label(self.frm, text="Device:", justify="left").grid(column=0, row=1)
        self._device_drop_down_text = tk.StringVar()
        self._device_drop_down = ttk.Combobox(self.frm, textvariable=self._device_drop_down_text)
        self._device_drop_down.grid(column=1, row=1, padx=(0, 10))
        # Whenever the user selects a device, populate the corresponding device name
        self._device_drop_down.bind("<<ComboboxSelected>>", lambda event: self._device_drop_down_text.set(self._device_list_values[self._device_list_display_values.index(self._device_drop_down.get())]))
        self.update_device_list()
        # Add refresh button to rescan for devices
        ttk.Button(self.frm, text="Refresh Device List", command=self.update_device_list).grid(column=2, row=1)
        
        # Add a button to connect/disconnect from the target device
        self._connect_disconnect_button = ttk.Button(self.frm, command=self.connect_disconnect_test_board)
        self._connect_disconnect_button.grid(column=2, row=2, pady=(10, 0))
        self.update_connect_disconnect_text()
        # Also trigger this event if the user hits enter on the combobox
        self._device_drop_down.bind("<Return>", lambda event: self._connect_disconnect_button.invoke())
        
    
    @property
    def test_board_connected(self) -> bool:
        """Whether or not a BMS test board has been connected to the host PC. True if a BMS test board has been
        connected, otherwise False.
        """
        return not self.ser is None


    def scan_for_devices() -> list[ListPortInfo]:
        """Lists all Pi Pico devices running MicroPython which are connected to the host PC

        Returns:
            list[ListPortInfo]: A list of all Pi Pico USB devices which are running MicroPython and connected to the
            host PC. See https://pyserial.readthedocs.io/en/latest/tools.html#serial.tools.list_ports.ListPortInfo.
        """
        
        # Relevant devices have a vendor ID of 0x2E8A and a product ID of 0x0005; see this page for details:
        # https://github.com/raspberrypi/usb-pid
        return list(filter(lambda port: port.pid == 0x0005 and port.vid == 0x2E8A, comports()))
    
    
    def update_device_list(self):
        # Get all the relevant devices
        devices = view_connect.scan_for_devices()
        
        # List the values to populate (the COM ports) and the corresponding values to display (the COM ports, plus the
        # corresponding manufacturers, products, and descriptions)
        self._device_list_values = list(device.device for device in devices)
        self._device_list_display_values = list(f"{device.device} ({device.manufacturer} {device.product}: {device.description})" for device in devices)
        
        # Update the drop-down text to match the new values
        self._device_drop_down.configure(values=self._device_list_display_values)
        
        # Auto-populate the combobox field with the first device, if it exists
        if len(self._device_list_values) > 0:
            self._device_drop_down_text.set(self._device_list_values[0])
        

    def connect_to_test_board(self, device: str):
        # Check to see if a device was properly specified
        if device == "":
            messagebox.showerror("Error", "Please select a valid device!", parent=self.frm.master)
            return
        
        try:
            # Open a new serial connection to the target device
            self.ser = Serial(port=device,
                              baudrate=settings.current_settings[settings._key_serial_baudrate],
                              timeout=settings.current_settings[settings._key_serial_timeout])
            logging.info(f"Opened serial port at '{device}'")
        
        except SerialException as e:
            # Failed to open the requested serial port, show an error popup to the user and continue
            messagebox.showerror("Error", f"Failed to open serial port at '{device}'!", parent=self.frm.master)
            logging.info(f"Failed to open serial port at '{device}'; full traceback:\n{e}")
            
        # TODO check to ensure the connected device is really the desired one
        
        # TODO Prompt the user for the number of cells used on the test board
        settings.current_settings[settings._key_cells_series] = 18
        settings.current_settings[settings._key_cells_parallel] = 4
            
    
    def disconnect_from_test_board(self):
        logging.info(f"Closing serial port at '{self.ser.port}'")
        self.ser.close()
        self.ser = None
        
    
    def update_connect_disconnect_text(self):
        # Check to see whether a test board is connected or not
        connected = self.test_board_connected
        
        # Update status label
        self._connection_status_label.configure(text = f"Connected to test board at {self.ser.port}." if connected else "Not connected to test board.")
        
        # Update connect/disconnect button text
        self._connect_disconnect_button.configure(text = "Disconnect" if connected else "Connect")
    
        
    def connect_disconnect_test_board(self):
        # The connect/disconnect button's function depends on whether a device is already connected; check state
        connected = self.test_board_connected
        if connected:
            self.disconnect_from_test_board
        else:
            # Get the target device from the combobox and attempt to connect to it
            target_device = self._device_drop_down_text.get()
            self.connect_to_test_board(target_device)
        
        # Update status text
        self.update_connect_disconnect_text()
        
        # Update main window tab state
        self.callback_connect_disconnect()
        

class view_calibration(view):
    def __init__(self, master: Misc | None) -> None:
        super().__init__(master)
        
        # Create a new calibration instance
        self.calibration = calibration()
        
        # Automatic calibration button
        def auto_calibrate():
            do_calibration = messagebox.askyesno("Auto-Calibrate",
                "The auto-calibration procedure will generate test voltages for each cell and temperature connection " +
                "and use the BMS sense board to read the corresponding voltages which are output by the test board. " +
                "This information will then be used to calibrate the test board so that its output voltages are " +
                "generated accurately. The results of this calibration depend entirely on the functionality and " +
                "accuracy of the BMS sense board which is connected, so please ensure that all connections to the BMS " +
                "are secure and that the BMS sense board which is connected is functioning properly.\n\n" +
                "Would you like to perform auto-calibration now?",
                parent=self.frm.master)
            if do_calibration:
                self.calibration.auto_calibrate()
                self.update_calibration_status(unsaved_changes=True)
            
        ttk.Button(self.frm, text="Auto-Calibrate", command=auto_calibrate).grid(column=0, row=1, pady=(0, 10))
        
        # Default calibration button
        def default_calibration():
            do_calibration = messagebox.askyesno("Reset Calibration",
                                                 "Would you like to restore the test board's calibration settings to " +
                                                 "their default values?",
                                                 parent=self.frm.master)
            if do_calibration:
                self.calibration.use_default_calibration()
                self.update_calibration_status(unsaved_changes=True)
            
        ttk.Button(self.frm, text="Reset Calibration", command=default_calibration).grid(column=1, row=1, pady=(0, 10))
        
        # Save calibration button
        def save_calibration():
            do_save = messagebox.askyesno("Save Calibration",
                                          "Saving the current calibration will overwrite any previous calibration " +
                                          "data. Would you like to continue?",
                                          parent=self.frm.master)
            if do_save:
                self.calibration.save_calibration()
                self.update_calibration_status(unsaved_changes=False)
                settings.save_current_settings()
        
        self._save_calibration_button = ttk.Button(self.frm, command=save_calibration)
        self._save_calibration_button.grid(column=0, row=2, pady=(0, 10))
        
        # Load calibration button
        def load_calibration():
            # Check to see if there is an available calibration file
            time_since_last_calibration = self.calibration.time_since_last_calibration()
            if time_since_last_calibration is None:
                messagebox.showerror("Load Calibration", "No calibration file was found!", parent=self.frm.master)
                return
            
            # If there appears to be an available calibration, ask the user if they want to load it
            do_load = messagebox.askyesno("Load Calibration",
                                          "Loading a calibration profile from the disk will cause any changes to the " +
                                          "current calibration profile to be discarded. Would you like to load a " +
                                          "calibration profile?",
                                          parent=self.frm.master)
            if do_load:
                self.calibration.load_calibration()
                self.update_calibration_status(unsaved_changes=False)

                # Check to make sure the calibration was actually loaded correctly
                calibration_loaded = self.calibration.calibration_loaded
                if not calibration_loaded:
                    messagebox.showerror("Error",
                                         "Failed to load calibration profile from the disk! This is likely due to a " +
                                         "corrupted settings file. It is recommended that you reset the calibration " +
                                         "profile or run the auto-calibration procedure and save the new calibration " +
                                         "to the disk.",
                                         parent=self.frm.master)
        
        ttk.Button(self.frm, text="Load Calibration", command=load_calibration).grid(column=1, row=2, pady=(0, 10))
        
        # Show the calibration status in a label at the top of the screen
        self._calibration_status_label = ttk.Label(self.frm)
        self._calibration_status_label.grid(column=0, columnspan=2, row=0, pady=(0, 10))
        self.update_calibration_status(unsaved_changes=False)
            
        
    
    def update_calibration_status(self, unsaved_changes: bool = False):
        # See how long it has been since the last calibration (note that this may be None if the timestamp is missing or
        # corrupted, or if the calibration has not yet been saved to the disk)
        time_since_last_calibration = self.calibration.time_since_last_calibration()
        
        # Update status text
        if self.calibration.calibration_loaded:
            status_text = "Calibration loaded."
        else:
            status_text = "No calibration loaded."
        if time_since_last_calibration is None:
            status_text += " No available calibration on disk."
        else:
            status_text += f" Calibration last saved: {time_since_last_calibration} ago."
        
        # Also update based on whether or not there are any unsaved canges
        if unsaved_changes:
            status_text += " There are unsaved changes to the calibration profile."
            self._save_calibration_button.configure(text="Save Calibration*")
        else:
            self._save_calibration_button.configure(text="Save Calibration")
        
        # Update status text
        self._calibration_status_label.configure(text=status_text)


if __name__ == '__main__':
    main()