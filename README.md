
# IoT Wearable Fitness Belt

## The Project Concept

This repository contains the documentation and code for a custom-built, wearable fitness tracker driven by a Raspberry Pi. Instead of using a standard, off-the-shelf digital heart monitor, this project focuses on capturing and processing raw electrical signals directly from the human body. By reading live electrocardiogram data and electromyography data, the system digitizes biological activity and uses custom software filters to calculate real-time physiological metrics.

## Engineering and Mechanics

The primary challenge of this build was creating a safe, functional bridge between high-voltage analog biology and low-voltage digital computing.

1. **Heart Rate Monitor (AD8232):** The sensor picks up millivolt-level electrical pulses across the chest. Because the module runs natively at 3.3V, its output signal can safely connect directly to the analog-to-digital converter.
2. **Muscle Activation Sensor (EMG):** This sensor monitors electrical impulses during muscle flexion. Since this specific module operates on a dual positive/negative 9V battery array, its raw signal can spike high enough to destroy low-voltage computing components. To protect the system, the signal passes through a custom-built 2k Ohm and 1k Ohm voltage divider circuit, which safely steps down potential 9V spikes to a maximum of 3.0V before it reaches the converter.
3. **Digitization:** An ADS1115 16-bit converter translates the safe analog signals into digital values, sending the data to the Raspberry Pi using the I2C communication protocol at address 0x48.
4. **Signal Processing:** A Python application samples the incoming data at 860 samples per second. The software uses a moving average algorithm to track the natural shift in electrical baseline caused by breathing and physical movement. By establishing this dynamic baseline, the code applies a responsive threshold to calculate accurate beats per minute while ignoring environmental static.

## Hardware Components

* **Microcomputer:** Raspberry Pi 4 Model B (2GB)
* **Converter:** ADS1115 16-bit Analog-to-Digital Converter
* **Motion Tracking:** MPU6050 6-axis Accelerometer and Gyroscope
* **Biometric Capture:** AD8232 Heart Rate Monitor and Analog EMG Muscle Sensor
* **Power Delivery:** Isolated 9V Battery Array with a Resistor-Based Voltage Divider

## Practical Skills and Concepts Developed

### Hardware Integration

* **Mixed-Voltage Safety:** Designing circuits that safely combine high-voltage analog battery supplies with sensitive 3.3V digital microcomputers.
* **Voltage Regulation:** Calculating and building resistor networks to lower input voltage safely and predictably.
* **Bus Networking:** Configuring, addressing, and troubleshooting multiple microchips sharing a single I2C communication bus.
* **Biological Signal Challenges:** Understanding how physical factors like skin contact, wire movement, and respiration affect micro-volt readings.

### Software Engineering and Signal Processing

* **Dynamic Filtering:** Writing software capable of adapting to a shifting baseline rather than relying on fixed numeric triggers.
* **Noise Isolation:** Implementing algorithmic smoothing techniques to separate meaningful biometric events from electrical static.
* **Environmental Management:** Using Python virtual environments to keep project-specific hardware libraries organized and isolated.

### Systems Administration

* **Remote Development:** Operating and programming the Raspberry Pi completely without a dedicated monitor or keyboard by establishing a secure WebRTC tunnel via Raspberry Pi Connect.
* **Linux Environment Management:** Handling package installations, troubleshooting hardware detection tools, and configuring core system interfaces.
