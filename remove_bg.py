import cv2
import numpy as np

img = cv2.imread('assets/images/trophy.png', cv2.IMREAD_UNCHANGED)
if img is not None:
    if img.shape[2] == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    
    mask = np.zeros((img.shape[0] + 2, img.shape[1] + 2), np.uint8)
    # Flood fill from (0,0)
    # We use a difference of 65 to catch both white and grey squares in the checkerboard
    cv2.floodFill(img, mask, (0, 0), (0, 0, 0, 0), (65, 65, 65, 65), (65, 65, 65, 65), 4)
    
    cv2.imwrite('assets/images/trophy.png', img)
    print("Done")
else:
    print("Image not found")
