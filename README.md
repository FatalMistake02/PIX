# PIX
---
Pixels. A Lossless image file format designed to be as small as possible.

>This project is licensed under the MIT License.

---
This is just a side project so I won't be working in this much. If you have any suggestions please let me know.

Not supported by any image editor directly.
To edit see [Editing](https://github.com/FatalMistake02/PIX/tree/master?tab=readme-ov-file#4-editing) in Intructions.

---
## Instructions

- [Install](https://github.com/FatalMistake02/PIX?tab=readme-ov-file#1-installation)
- [Convert](https://github.com/FatalMistake02/PIX?tab=readme-ov-file#2-conversion)
- [View](https://github.com/FatalMistake02/PIX?tab=readme-ov-file#3-viewing)
- [Edit](https://github.com/FatalMistake02/PIX?tab=readme-ov-file#4-editing)
- [Advanced Convert](https://github.com/FatalMistake02/PIX?tab=readme-ov-file#5-advanced-conversion-version-2)

### 1. Installation
Download the [latest release](https://github.com/FatalMistake02/PIX/releases/latest) and run the installer.

---
### 2. Conversion
**To convert a image to a PIX file, open the image with the Convert to PIX "app".**

1. Right click on an image file and go to open with.

![1-1](https://github.com/FatalMistake02/PIX/blob/master/screenshots/1-1.png?raw=true)
 
2. Click "Chose another app"

![1-2](https://github.com/FatalMistake02/PIX/blob/master/screenshots/1-2.png?raw=true)

3. Select "Convert to PIX"

![1-3](https://github.com/FatalMistake02/PIX/blob/master/screenshots/1-3.png?raw=true)

**To convert a pix file back to a png, open the pix file with the Convert to PNG "app"**

1. Right click on an pix file and go to open with.

![1-1](https://github.com/FatalMistake02/PIX/blob/master/screenshots/1-1.png?raw=true)
 
 2. Click "Convert to PNG"

![1-4](https://github.com/FatalMistake02/PIX/blob/master/screenshots/1-4.png?raw=true)

---
### 3. Viewing

**To view a PIX file, open the image with the PIX Viewer "app".**

1. Right click on an pix file and go to open with.

![1-1](https://github.com/FatalMistake02/PIX/blob/master/screenshots/1-1.png?raw=true)
 
2. Click "PIX Viewer"

![2-1](https://github.com/FatalMistake02/PIX/blob/master/screenshots/2-1.png?raw=true)

---
### 4. Editing

**To edit a PIX file, open the image with the PIX Editor "app".**

1. Right click on an pix file and go to open with.

![1-1](https://github.com/FatalMistake02/PIX/blob/master/screenshots/1-1.png?raw=true)
 
2. Click "PIX Editor"

![3-1](https://github.com/FatalMistake02/PIX/blob/master/screenshots/3-1.png?raw=true)

3. (version 1) This will open a terminal window and the photos app. Edit you image and when done go to the terminal and press enter.

![3-2](https://github.com/FatalMistake02/PIX/blob/master/screenshots/3-2.png?raw=true)


---

### 5. Advanced Conversion (Version 2)

1. Open the folder containing the PIX files and type:
`python to_pix test.png test.pix --scm METHOD`
- Replace test.png with your image file.
- Replace test.pix with the output name you want.
- Replace METHOD with one of the available methods.
- Run.

2. To get a list of available methods, run: `python to_pix test.png test.pix --list`
---