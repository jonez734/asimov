import time, random
import numpy as np
import cv2

class Distortion:
    def __init__(self):
        self.active = False
        self.start_time = 0
        self.duration = 0
        self.next_time = time.time() + random.uniform(5, 15)
        self.intensity = 0.0
        self.name = "NEEDINFO"
    def __call__(self, frame):
        return frame

def tear(image):
    rows, cols, _ = image.shape
    num_slices = random.randint(3, 8)  # number of tearing "slices"
    tear_image = image.copy()

    for _ in range(num_slices):
        y = random.randint(0, rows - 20)
        h = random.randint(5, 20)  # height of tear band
        shift = random.randint(-30, 30)  # how much to horizontally offset

        # Shift the band horizontally
        tear_image[y:y+h, :] = np.roll(tear_image[y:y+h, :], shift, axis=1)

        # Add a thin black line above or below to simulate a gap
        gap_position = y + h if (y + h) < rows else y - 1
        gap_thickness = random.randint(1, 3)
        gap_color = random.randint(0, 30)  # very dark gray instead of pure black
        if 0 <= gap_position < rows - gap_thickness:
            tear_image[gap_position:gap_position+gap_thickness, :] = gap_color

    return tear_image

class WhiteNoise(Distortion):
    def __init__(self):
        super().__init__()
        self.name = "whitenoise"

    def update(self):
        current_time = time.time()

        if not self.active and current_time >= self.next_time:
            # Start distortion
            self.active = True
            self.start_time = current_time
            self.duration = 0.25 + random.uniform(0.0, 1.0)
            self.intensity = random.uniform(0.3, 0.7)
            print(f"[{self.name}] Starting distortion for {self.duration:.2f}s with intensity {self.intensity:.2f}")

        elif self.active:
            elapsed = current_time - self.start_time
            if elapsed >= self.duration:
                # End distortion
                self.active = False
                self.next_time = current_time + random.uniform(1, 5)
                print(f"[{self.name}] Distortion ended. Next at {self.next_time:.2f}")

    def apply(self, frame):
        if not self.active:
            return frame

        elapsed = time.time() - self.start_time
        t = elapsed / self.duration
        fade = np.sin(np.pi * t)

        # Generate grayscale noise and broadcast to RGB
        noise = np.random.randint(0, 256, (frame.shape[0], frame.shape[1], 1), dtype=np.uint8)
        noise = np.repeat(noise, 3, axis=2).astype(np.float32)

        frame_f32 = frame.astype(np.float32)
        alpha = min(1.0, self.intensity * fade)

        distorted = cv2.addWeighted(frame_f32, 1.0, noise, alpha, 0)
        return np.clip(distorted, 0, 255).astype(np.uint8)

    def __call__(self, frame):
        self.update()
        return self.apply(frame)
