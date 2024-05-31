from threading import Thread
import time

import numpy as np
import cv2

from bbsengine6 import io

import cvzone
from cvzone.FPS import FPS as cvzoneFPS
from cvzone.HandTrackingModule import HandDetector

#import mediapipe as mp
#import imutils

RESOLUTION = (640, 480)
#RESOLUTION = (1280, 720)
SRC = 1
FONT = cv2.FONT_HERSHEY_SIMPLEX
FPS = 30

LABELCOLOR = (187, 187, 187) # lightgray
VALUECOLOR = (0, 204, 85) # green
DARKGRAY = (51, 51, 51)
BGCOLOR = DARKGRAY
GREEN = (0, 204, 85)
CONTOURCOLOR = GREEN

def order_points(pts):
	# initialzie a list of coordinates that will be ordered
	# such that the first entry in the list is the top-left,
	# the second entry is the top-right, the third is the
	# bottom-right, and the fourth is the bottom-left
	rect = np.zeros((4, 2), dtype = "float32")
	# the top-left point will have the smallest sum, whereas
	# the bottom-right point will have the largest sum
	s = pts.sum(axis = 1)
	rect[0] = pts[np.argmin(s)]
	rect[2] = pts[np.argmax(s)]
	# now, compute the difference between the points, the
	# top-right point will have the smallest difference,
	# whereas the bottom-left will have the largest difference
	diff = np.diff(pts, axis = 1)
	rect[1] = pts[np.argmin(diff)]
	rect[3] = pts[np.argmax(diff)]
	# return the ordered coordinates
	return rect

def four_point_transform(image, pts):
	# obtain a consistent order of the points and unpack them
	# individually
	rect = order_points(pts)
	(tl, tr, br, bl) = rect
	# compute the width of the new image, which will be the
	# maximum distance between bottom-right and bottom-left
	# x-coordiates or the top-right and top-left x-coordinates
	widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
	widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
	maxWidth = max(int(widthA), int(widthB))
	# compute the height of the new image, which will be the
	# maximum distance between the top-right and bottom-right
	# y-coordinates or the top-left and bottom-left y-coordinates
	heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
	heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
	maxHeight = max(int(heightA), int(heightB))
	# now that we have the dimensions of the new image, construct
	# the set of destination points to obtain a "birds eye view",
	# (i.e. top-down view) of the image, again specifying points
	# in the top-left, top-right, bottom-right, and bottom-left
	# order
	dst = np.array([
		[0, 0],
		[maxWidth - 1, 0],
		[maxWidth - 1, maxHeight - 1],
		[0, maxHeight - 1]], dtype = "float32")
	# compute the perspective transform matrix and then apply it
	M = cv2.getPerspectiveTransform(rect, dst)
	warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
	# return the warped image
	return warped

def handle_hands(image):
	hands, image = detector.findHands(image, draw=True, flipType=True)
	return image

def handle_cards_orig(img):
	print(f"{img=}")
	# Convert the image to grayscale
	gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
	blurred = cv2.GaussianBlur(gray, (5, 5), 0)
#	cv2.imshow("gray", gray)
#	cv2.imshow("blurred", blurred)
	edges = cv2.Canny(blurred, 50, 150)
#	cv2.imshow("edges", edges)
#	text_color = (255, 255, 255)
	label = "rect"
	contours, hierarchy = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	#print(f"{hierarchy=}")
	for contour in contours:
		# Approximate the contour to a polygon
		polygon = cv2.approxPolyDP(contour, 0.1 * cv2.arcLength(contour, True), True)
		# Check if the polygon has 4 sides
		if len(polygon) == 4:
			# Draw the rectangle on the image
			x, y, w, h = cv2.boundingRect(polygon)
			print(f"{x=} {y=} {w=} {h=}")
			if w < 80 or h < 80:
				continue
			# cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
			cvzone.cornerRect(img, (x, y, w, h), l=30, t=5, rt=1, colorR=(255, 0, 255), colorC=(0, 255, 0))
			(w, h), _ = cv2.getTextSize(label, FONT, 0.6, 1)
			img = cv2.putText(img, label, (x, y - 5), FONT, 0.6, VALUECOLOR, 1)
	return img

def handle_cards(image):
	canny = cv2.Canny(image, 50, 150)
	dilated = cv2.dilate(canny, np.ones((5,5), np.uint8), image)
	imgContours, conFoundFiltered = cvzone.findContours(image, dilated, minArea=100, sort=True, filter=[4,], drawCon=True, c=CONTOURCOLOR, ct=(255, 0, 255), retrType=cv2.RETR_EXTERNAL, approxType=cv2.CHAIN_APPROX_NONE)
	return imgContours
#	print(count)
# Load an image
#img = cv2.imread("2024-05-21-134326.jpg")
#img = cv2.imread("2024-05-21-154747.jpg")
#handle_frame(img)
#cv2.imshow("prod", img)
#cv2.waitKey(0)
#cv2.destroyAllWindows()

class Video:
	def __init__(self, resolution=(640, 480), fps=FPS, src=SRC):
		self.stream = cv2.VideoCapture(src)
		if self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0]) is True:
			io.echo(f"FRAME_WIDTH set to {resolution[0]}", level="debug")
		if self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1]) is True:
			io.echo(f"FRAME_HEIGHT set to {resolution[1]}", level="debug")
		if self.stream.set(cv2.CAP_PROP_FPS, fps) is True:
			io.echo(f"FPS set to {fps}", level="debug")

		self.stopped = False
		self.frame = None

	def update(self):
		while True:
			if self.stopped is True:
				self.stream.release()
				return

			ret = self.stream.read()
			if ret is False:
				io.echo(f"no frame grabbed", level="warning")
			else:
				(self.grabbed, self.frame) = ret

	def read(self):
		return self.frame

	def start(self):
		Thread(target=self.update, args=()).start()

	def stop(self):
		self.stopped = True

fpsReader = cvzoneFPS(avgCount=30)

v = Video(src=SRC, resolution=RESOLUTION, fps=FPS)
v.start()
detector = HandDetector(staticMode=False, maxHands=2, modelComplexity=1, detectionCon=0.5, minTrackCon=0.5)

try:
	done = False
	while not done:
		image = v.read()
		fps, image = fpsReader.update(image, pos=(30,40), bgColor=BGCOLOR, textColor=VALUECOLOR, scale=3, thickness=3)
#		image = cv2.flip(image, 1)
		ch = cv2.waitKey(1)
		if ch == ord("q") or ch == 27:
			done = True
		if image is not None:
#			image = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
			image = handle_cards(image)
			image = handle_hands(image)
#			cv2.flip(image, 1)
			cv2.imshow("project asimov", image)
#		fps, image = fpsReader.update(image, pos=(30,40), bgColor=BGCOLOR, textColor=VALUECOLOR, scale=3, thickness=3)

except:
	v.stop()
	raise

cv2.destroyAllWindows()
v.stop()
