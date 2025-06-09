# Spezi — Apple Music Companion for macOS

**Spezi** is a lightweight companion app for **Apple Music** on macOS that enhances your listening experience with:

- 🎚️ **Automatic sample rate matching**  
  Seamlessly switches your audio device’s sample rate to match the currently playing song.
  
- 🎨 **Now Playing screen**  
  Displays high-resolution cover art and animated album art (if available).
  
- 🕹️ **Remote control features**  
  Play, pause, skip, directly from spezi.

- 🌈 **Visualizers**  
  Choose from built-in background visualizers—or add your own!

---

## Screenshots

<img width="1470" alt="Screenshot 1" src="https://github.com/user-attachments/assets/8fc69c1c-d666-4399-b764-64657ff7cccb" />

<img width="1470" alt="Screenshot 2" src="https://github.com/user-attachments/assets/ce9f2d61-77a3-44a9-8f8f-b72811dc17b1" />

---

## Prerequisites

- **macOS 15.x** or newer  
  > (older versions *might* work, but are untested)

- **Python 3.11**  
  > other versions may also work, but this one is recommended

## Setup
- **Installing**  
  Install with:
  ```bash
  xcode-select --install
  git clone https://github.com/rubbelgeorge/spezi
  cd spezi
  pip install -r requirements.txt

- **Running the app**  
  run with:
  ```bash
  python main.py
-
  Then open the interface in Safari (currently the only supported browser):

  http://localhost:22441



## Notes
- **Bit-Depth**
  This tool is only switching the sample rate, not the Bit-Depth. So make sure, that your audio device is set to 24 Bit or more.  
- **Visualizers**  
  There are several visualizers included, but you can easily add more. Just duplicate one of the existing in the visualizer folder and change the value. every js file in this folder     that is compatible with the app are in the visualizer app automatically.

- **Performance**
  There could be some performance issues on older macs. If your mac doesnt support native hevc encoding it could get a bit spicy when viewing animated artwork. An option to force avc    animated artwork is planned.
  The visualizers are utilizing the gpu more than i thought they would. Optimization is planned as well as an option to turn them off.
  

  
## Roadmap

  - AVC force mode
  - Turning off visualizers
  - Lyric support (i cant promise a satisfying result at the moment)
  - Perfomance improvements (faster cover art loading) 


  
