# moto-lpr-recorder
Can connect to Motorola License Plate Readers and save scanned plates to a csv along with an image of the plate

There are many unsecured publicly accessible license plate readers by Motorola available on the open Internet. You can find IPs for these devices by using `search.censys.io` and searching for `services.http.response.body:"Not found your stream. PLease contact administrator to get correct stream name"`.

You will get many hosts matching this pattern. 

If you open VLC and connect to a network stream of one of the IPs with the scheme of `http://XX.XX.XX.XX:8080/cam1color` you can view the first camera on the system. The systems can support multiple cameras. You can access them by changing the number after the `cam` designation. You can also choose either `color` or `ir` views. 

To receive data of the plates, the script connects to ports in the 5000 range. 5001 would be the data from cam1, 5002 is from cam2, etc. Sometimes for some reason certain camera data ports stop responding to connections. It may take you some trial and error to find a good system with a camera with activity, that has a responding data port. 

To test the data port, you can use `nc -v XX.XX.XX.XX 5001` on a linux system. If it is responding, you should see a connection successful message, followed by a bunch of binary data as cars pass by the camera. 

## Using the script
Edit the IP and port at the bottom of the script to match the system you wish to connect to. Then run the script from your terminal. 

Data from the plates will be appended to `output.csv`, and images of the plates will be placed in `images/YYYY-MM-DD/*.jpg`.

## Known Limitations
If more than one car is processed within 1 second, both cars will have the same timestamp and the image will be overwritten. A better system for co-relating output lines and images is needed.
