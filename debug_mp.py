import mediapipe as mp
print(mp.__version__)
print('has pose:', hasattr(mp.solutions, 'pose'))
print('solutions keys:', list(mp.solutions.__dict__.keys())[:50])
