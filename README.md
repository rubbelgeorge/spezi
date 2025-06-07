spezi is a companion app for apple music on MacOs that does that matche the sample rate of your audio device to the sample rate of the currently playing song
and showing a Now playing screen with High res cover art and animated cover art (if available for the song). 
Additionally spezi serves as a simple remote for apple music and has several background visualizer with the option to add your own. 



Screenshots:

<img width="1470" alt="Bildschirmfoto 2025-06-07 um 19 26 44" src="https://github.com/user-attachments/assets/8fc69c1c-d666-4399-b764-64657ff7cccb" />


<img width="1470" alt="Bildschirmfoto 2025-06-07 um 19 27 35" src="https://github.com/user-attachments/assets/ce9f2d61-77a3-44a9-8f8f-b72811dc17b1" />


Prerequisites 

MacOs 15.x or newer (older versions should work, its the only one i was able to test) 
Python 3.11 (other versions could work as well) 


Installing

pip install -r requirements.txt 
xcode-select --install

Running the app 

python main.py 
now open [localhost:22441/](http://localhost:22441) in safari (only safari seems to be working properly at the moment)
