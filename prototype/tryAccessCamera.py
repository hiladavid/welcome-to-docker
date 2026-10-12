import cv2

#try open camera(Index 0)
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) 

if not cap.isOpened():
    print("can't open camera - Container succeeded.")
else:
    print("camera opened - contaier failed.")
    

    #get frame of stream from driver.
    ret, frame = cap.read()
    if ret:
        print("picture was successfuly captured.")
        #saves picture to folder.
        cv2.imwrite("photo.jpg", frame)
        #show picture on screen.
        cv2.imshow("Camera Capture", frame)

        #waits 2s before closing the picture.
        cv2.waitKey(2000)
        cv2.destroyAllWindows()

    #realese camera.
    cap.release()