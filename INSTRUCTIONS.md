# CANSentinel: Instruction Manual

Welcome to **CANSentinel**, your Virtual Car Hacking Lab! This manual will guide you through setting up a safe, virtual environment to simulate car attacks and defending against them using a custom Intrusion Detection System (IDS).

---

## 1. System Preparation

Before we begin, we need to ensure your system has the necessary tools to simulate a Controller Area Network (CAN) bus.

### Required Software
This guide assumes you are running **Arch Linux** (as detected on your system).

1.  **Open a terminal** and install the standard CAN utilities:
    ```bash
    sudo pacman -S can-utils
    ```

2.  **Install the Instrument Cluster Simulator (ICSim)**:
    Since you are on Arch, you can use an AUR helper like `yay`:
    ```bash
    yay -S icsim
    ```
    *(Note: If you have already installed `icsim`, you can skip this step. Verify by compiling `which icsim`)*.

3.  **Compiler**:
    Ensure you have `g++` installed to build the CANSentinel tool:
    ```bash
    sudo pacman -S gcc
    ```

---

## 2. Compiling CANSentinel

The core of this project is the `ids_guard` program, which monitors the network for suspicious activity.

1.  Navigate to the project directory:
    ```bash
    cd "CANSentinel"
    ```
2.  Compile the source code:
    ```bash
    g++ ids_guard.cpp -o ids_guard
    ```
3.  Verify the file exists:
    ```bash
    ls -l ids_guard
    ```
    You should see an executable file named `ids_guard`.

---

## 3. Running the Dashboard (New Standalone App)
We have consolidated the Simulator, Instrument Cluster, and IDS into a single Python application.

### Step 1: Initialize Virtual CAN
We still need the Linux kernel to create the virtual wire.
```bash
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
```

### Step 2: Launch the Dashboard
```bash
sudo python dashboard_gui.py
```
*(Sudo is required to access the raw SocketCAN interface).*

### Step 3: Controls
*   **Start Engine**: The car will start "driving" automatically (Needle moves). ID `0x244` packets are broadcast at 20Hz.
*   **Hack Speedometer**: This simulates an external attack injection.
    *   **Effect**: 50 frames are injected at 1ms intervals.
    *   **Visual**: The dashboard turns **RED** and displays "IDS ALERT".

This demonstrates how a modern Defensive Dashboard can detect and visualize anomalies on the CAN Bus in real-time.
