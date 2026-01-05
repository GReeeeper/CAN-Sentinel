/**
 * ids_guard.cpp
 * 
 * Simple Intrusion Detection System for CAN Bus (vcan0).
 * Detects high-frequency injection attacks on ID 0x244.
 * 
 * Compile with: g++ ids_guard.cpp -o ids_guard
 */

#include <iostream>
#include <string>
#include <cstring>
#include <unistd.h>
#include <net/if.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <linux/can.h>
#include <linux/can/raw.h>
#include <sys/time.h>

// Threshold in milliseconds
const long THRESHOLD_MS = 5;

int main() {
    int s;
    struct sockaddr_can addr;
    struct ifreq ifr;
    struct can_frame frame;

    // 1. Create socket
    if ((s = socket(PF_CAN, SOCK_RAW, CAN_RAW)) < 0) {
        perror("Socket");
        return 1;
    }

    // 2. Specify interface (vcan0)
    strcpy(ifr.ifr_name, "vcan0");
    ioctl(s, SIOCGIFINDEX, &ifr);

    // 3. Bind socket to interface
    memset(&addr, 0, sizeof(addr));
    addr.can_family = AF_CAN;
    addr.can_ifindex = ifr.ifr_ifindex;

    if (bind(s, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("Bind");
        return 1;
    }

    std::cout << "IDS Guard Listening on vcan0..." << std::endl;
    std::cout << "Monitoring CAN ID 0x244 for packet flooding (< " << THRESHOLD_MS << "ms intervals)." << std::endl;

    struct timeval last_time = {0, 0};
    bool first_packet = true;

    // 4. Main Loop
    while (true) {
        int nbytes = read(s, &frame, sizeof(struct can_frame));

        if (nbytes < 0) {
            perror("Read");
            return 1;
        }

        // Only check standard frames with ID 0x244
        if (frame.can_id == 0x244) {
            struct timeval current_time;
            gettimeofday(&current_time, NULL);

            if (!first_packet) {
                // Calculate time difference in milliseconds
                long seconds = current_time.tv_sec - last_time.tv_sec;
                long useconds = current_time.tv_usec - last_time.tv_usec;
                long mtime = ((seconds) * 1000 + useconds / 1000.0) + 0.5;

                if (mtime < THRESHOLD_MS) {
                    std::cout << "\033[1;31m[ALERT] Injection Detected! ID: 0x244 | Delta: " 
                              << mtime << "ms\033[0m" << std::endl;
                }
            }

            last_time = current_time;
            first_packet = false;
        }
    }

    close(s);
    return 0;
}
