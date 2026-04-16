# Smart Classroom AI – Final Project Report

**Date:** April 2026
**Subject:** Smart Classroom Automated Monitoring & Energy Optimization System

---

## 1. Executive Summary

The **Smart Classroom AI** project was developed to provide an end-to-end, real-time monitoring and analytics solution for modern educational environments. By leveraging state-of-the-art Computer Vision (YOLOv8), the system autonomously scans live camera feeds, video files, and images to detect human occupancy. 

Based on this occupancy, the system achieves two primary goals:
1. **Historical Data Analytics**: Logging every detection phase to a local SQLite database, allowing administrators to review peak classroom hours and average attendance via dynamic graphs and CSV exports.
2. **Intelligent Energy Management**: Automatically calculating and controlling the required number of fans and lights for the room based on live student density—significantly reducing wasted energy in empty or partially-filled classrooms.

---

## 2. System Architecture & Tech Stack

The architecture is split into a highly efficient Python-based data processing backend and a responsive, dynamic web frontend.

* **Inference Engine (AI)**: Powered by `Ultralytics YOLOv8`, delivering high-fps edge inference without the need for external cloud APIs. 
* **Backend Server**: Built using **Flask** and **Flask-SocketIO**. It handles the REST APIs, connects the continuous camera MJPEG byte-stream, and uses web-sockets to push sub-second JSON updates to the frontend dashboard.
* **Persistent Storage**: **SQLite** utilizing Write-Ahead Logging (WAL) is implemented to handle hundreds of fast concurrent inserts per second without locking the main detection loop.
* **Frontend Dashboard**: Constructed with HTML5, Vanilla CSS tokens, Inter/JetBrains formatting, and **Chart.js** for immediate reactive data visualizations.

---

## 3. Core Features & Capabilities

### Real-Time Quadrant Analysis
Every frame processed by the camera is mathematically divided into four specific quadrants (Q1: Top-Left, Q2: Top-Right, Q3: Bottom-Left, Q4: Bottom-Right). The system tracks specifically where students are clustering within the classroom, rendering a live total combined with regional breakdowns.

![Smart Classroom Live Dashboard](https://github.com/Mohd-Shujath-Ali/smart-classroom/blob/main/smart-classroom/assets/placeholder.png)

> [!TIP]
> The dashboard operates at near-zero latency because we split the video imagery away from the statistical text data. The statistics are sent instantly via Socket.io over a persistent web socket, keeping network traffic exceptionally low.

---

### Automated Appliance Control (Smart Energy)

To prevent power waste, we introduced an **Automated Appliances** matrix. A background listener continually reviews the person count. If a threshold is crossed, the system updates its targeted energy parameters for the physical room hardware:

* **0 Students**: 0 Fans, 0 Lights *(Maximum Energy Saving Mode)*
* **1 – 10 Students**: 2 Fans, 4 Lights *(Low-Power Mode)*
* **11 – 19 Students**: 4 Fans, 6 Lights *(Medium-Power Mode)*
* **20+ Students**: 6 Fans, 8 Lights *(Maximum Cooling/Lighting Mode)*

<!-- ![Automated Appliance Dashboard](/Users/sheikharsalan/.gemini/antigravity/brain/6c5aa36e-460a-4c62-b434-d4dc7450cb93/automated_appliances_panel_1776259492263.png)

Whenever the server algorithm shifts, the UI actively glows and updates in real time. For standalone image analysis, the dashboard fires a dedicated system toast informing the user of the exact power-routing choices it made based on the snapshot. -->

---

### Database Tracking & Historical Visualizations

Every time a user initiates a feed (webcam, file, or image), a distinct **Session** record is created in `classroom.db`. 

Rather than overloading the local disk by saving data 30 times a second, our DB layer implements a **Thread-Safe Memory Buffer**. It quietly holds statistical data (FPS, individual quadrant counts, timestamp) in RAM and bulk-flushes it dynamically, guaranteeing the live video feed never drops frames while logging data.

![Historical Database Statistics](https://github.com/Mohd-Shujath-Ali/smart-classroom/blob/main/smart-classroom/assets/analysis.png?raw=true)

> [!IMPORTANT]
> To comply with strict reporting and analytics standards, the dashboard features one-click robust data delivery mechanisms.
> * **Download CSV:** Triggers a backend pipeline returning an Excel-formatted `.csv` spreadsheet summarizing timestamps, peak person counts, and average persons for deep-diving into the numbers.
> * **Download Graph:** Actively screenshots the transparent graphical element on the dashboard so administrators can embed the dynamic tracking chart directly into their presentations.

---

## 4. Conclusion and ROI

The Smart Classroom AI presents a fully scalable blueprint for institutional modernization. By removing the human element from tedious tasks (head counts, physically flipping switches on and off based on room density), administrators are empowered visually through the Dashboard.

**Immediate Return on Investment:**
1. **Cost Reduction:** Automated tracking prevents fans and lights from running in empty or low-density environments.
2. **Security & Auditing:** The SQLite Database retains unquestionable chronological proof of classroom usage over the last 24 hours.
3. **Data-Driven Scheduling:** Long-term insights gathered from the `CSV` exports can allow the university/school to optimize when they schedule classes for specific rooms based on historical peak volumes.
