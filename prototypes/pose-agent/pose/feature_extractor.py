import numpy as np
from collections import deque
import math

class FeatureExtractor:
    def __init__(self, sequence_length=30, stride=15):
        self.prev_landmarks = deque(maxlen=2)  # 현재 + 이전 프레임만 유지
        self.sequence_buffer = deque(maxlen=sequence_length)  # 30개 feature 벡터 유지
        self.stride = stride
        self.frame_counter = 0  # 프레임 카운터: stride마다 시퀀스 버퍼에 추가

    def _distance(self, a, b):
        # 두 landmark 사이의 2D 유클리드 거리 계산
        return ((a.x - b.x)**2 + (a.y - b.y)**2) ** 0.5
    
    def _angle(self, a, b, c):
        # 세 landmark가 이루는 각도 계산 (b가 꼭짓점, b에서 a와 c로 향하는 벡터의 각도)

        ab = np.array([a.x - b.x, a.y - b.y])
        cb = np.array([c.x - b.x, c.y - b.y])

        dot_product = np.dot(ab, cb)
        norm_ab = np.linalg.norm(ab)
        norm_cb = np.linalg.norm(cb)

        if norm_ab == 0 or norm_cb == 0:
            return None  # 벡터 길이가 0이면 각도 계산 불가

        cos_angle = dot_product / (norm_ab * norm_cb)  
        cos_angle = np.clip(cos_angle, -1.0, 1.0)  # 수치 안정성 위해 클리핑

        angle_rad = math.acos(cos_angle)
        angle_deg = math.degrees(angle_rad)

        return angle_deg
  
    def get_wrist_to_shoulder_left(self, landmarks):
        # 왼손목(15)-왼어깨(11) 거리
        # 반환: float 또는 None
        if 15 in landmarks and 11 in landmarks:
            return self._distance(landmarks[15], landmarks[11])
        return None

    def get_shoulder_height_diff(self, landmarks):
        # 양쪽 어깨의 높이 차이 계산
        # 왼어깨(11)-오른어깨(12)
        # 반환: float 또는 None
        if 11 in landmarks and 12 in landmarks:
            return abs(landmarks[11].y - landmarks[12].y)
        return None

    def get_wrist_velocity_left(self, landmarks):
        # 손목의 프레임 간 이동 거리 계산 (속도 유사)
        # 왼손목(15) 프레임간 이동거리 (속도)
        # 반환: float 또는 None
        self.prev_landmarks.append(landmarks)

        if len(self.prev_landmarks) < 2:
            return None  # 이전 프레임이 없으면 계산 불가
        
        prev = self.prev_landmarks[0]
        curr = self.prev_landmarks[1]

        if 15 in prev and 15 in curr:
            return self._distance(curr[15], prev[15])  
        return None

    def get_elbow_angle(self, landmarks):
        # 팔 각도 계산
        # 왼팔: 왼어깨(11)-왼팔꿈치(13)-왼손목(15)
        # 오른팔: 오른어깨(12)-오른팔꿈치(14)-오른손목(16)
        # 반환: {'left': float, 'right': float}
        result = {}

        if 11 in landmarks and 13 in landmarks and 15 in landmarks:
            result['left'] = self._angle(landmarks[11], landmarks[13], landmarks[15])

        if 12 in landmarks and 14 in landmarks and 16 in landmarks:
            result['right'] = self._angle(landmarks[12], landmarks[14], landmarks[16])

        return result
    
    def get_wrist_angle_right(self, landmarks):
        # 오른손목 각도: 오른팔꿈치(14)-오른손목(16)-오른엄지(18)
        # 반환: float 또는 None
        if 14 in landmarks and 16 in landmarks and 18 in landmarks:
            return self._angle(landmarks[14], landmarks[16], landmarks[18]) 
        return None


    def compute(self, landmarks):
        # 모든 거리 feature를 한번에 계산해서 dictionary로 반환

        if landmarks is None:
            return None

        return {
            'wrist_to_shoulder_left': self.get_wrist_to_shoulder_left(landmarks),
            'shoulder_height_diff':   self.get_shoulder_height_diff(landmarks),
            'wrist_velocity_left':    self.get_wrist_velocity_left(landmarks),
            'elbow_angle':            self.get_elbow_angle(landmarks),
            'wrist_angle_right':      self.get_wrist_angle_right(landmarks),
        }
    
    def to_vector(self, features):
        # features dictionary를 벡터 형태로 변환 (모델 입력용)
        # (#features,) 형태의 1D numpy array 반환
        # keypoint가 존재하지 않으면 0.0으로 채움

        if features is None:
            return np.zeros(6)  # feature 개수에 맞게 0 벡터 반환
        
        ea = features['elbow_angle'] or {}

        vector = [
            features['wrist_to_shoulder_left'] or 0.0,  # 0 왼손목 - 왼어깨 거리
            features['shoulder_height_diff']   or 0.0,  # 1 양쪽 어깨 높이 차이
            features['wrist_velocity_left']    or 0.0,  # 2 왼손목 속도
            ea.get('left',  0.0),                       # 3 왼팔 각도
            ea.get('right', 0.0),                       # 4 오른팔 각도
            features['wrist_angle_right']      or 0.0,  # 5 오른손목 각도
        ]

        return np.array(vector, dtype=np.float32)    
    
    def update_buffer(self, features):
        self.frame_counter += 1

        if self.frame_counter % self.stride != 0:
            return None

        if self.frame_counter % self.stride == 0:
            # sequence buffer에 feature 벡터 추가
            # 버퍼가 sequence_length개 채워지면 (sequence_length, feature_dim) 형태의 numpy array 반환, 그렇지 않으면 None 반환
            vector = self.to_vector(features)
            self.sequence_buffer.append(vector)

        if len(self.sequence_buffer) < self.sequence_buffer.maxlen:
            return None  # 버퍼가 아직 채워지지 않음
        
        # (sequence_length, feature_dim) = (30, 6) 형태의 배열 반환 
        return np.array(self.sequence_buffer, dtype=np.float32)  
