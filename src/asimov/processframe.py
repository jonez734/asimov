def processframe(img):
    global detector

    # Rectangle detection
    imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    imgBlur = cv2.GaussianBlur(imgGray, (5, 5), 1)
    imgCanny = cv2.Canny(imgBlur, 50, 150)
    contours, _ = cv2.findContours(imgCanny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    rectangles = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area >= 1000:
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

            if len(approx) == 4:
                pts = approx.reshape((4, 2))
                polygon = np.array(pts, np.int32).reshape((-1, 1, 2))

                # Check if fingertip is inside or near the rectangle (with margin)
                touching = False
                if left_index_tip is not None:
                    dist = cv2.pointPolygonTest(polygon, left_index_tip, False)

                    # Debugging print statements
                    print(f"Fingertip: {left_index_tip}, Polygon: {pts}, Dist: {dist}")

                    # Use margin to check proximity to the polygon
                    if dist >= -MARGIN:
                        touching = True

                rectangles.append((polygon, touching))

    # Draw rectangles first
    for polygon, touching in rectangles:
        # Set color based on whether fingertip is touching
        color = (0, 255, 0) if not touching else (0, 0, 255)  # Green if not touching, Red if touching
        cv2.polylines(img, [polygon], True, color, 2)

    # Hand detection
    hands, img = detector.findHands(img, draw=False)

    left_index_tip = None
    if hands:
        for hand in hands:
            if hand['type'] == "Left":
                lmList = hand['lmList']
                left_index_tip = (lmList[8][0], lmList[8][1])  # Index fingertip (landmark 8)

    # Draw fingertip marker on top!
    if left_index_tip is not None:
        cv2.circle(img, left_index_tip, 8, (0, 255, 255), cv2.FILLED)
        cv2.circle(img, left_index_tip, 12, (0, 255, 255), 2)
    
    return img
