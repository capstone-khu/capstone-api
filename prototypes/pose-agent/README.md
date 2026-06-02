# Pose Agent

영상 또는 웹캠 입력에서 사람의 포즈 랜드마크를 추출하고, 자세 분석 결과를 `pose_output.json`으로 저장하는 자세 에이전트입니다.

## 클론 후 실행 준비

### 1. 저장소 클론

```bash
git clone <repository-url>
cd Pose-Agent
```

이미 상위 폴더에서 클론했다면 실제 프로젝트 폴더인 `Pose-Agent`로 이동한 뒤 아래 명령을 실행하세요.

### 2. Git LFS 파일 받기

이 프로젝트는 MediaPipe 모델 파일인 `pose_landmarker_lite.task`를 Git LFS로 관리합니다.

```bash
git lfs install
git lfs pull
```

`git lfs` 명령이 없다고 나오면 Git LFS를 먼저 설치한 뒤 다시 실행해야 합니다.

### 3. 가상환경 생성 및 활성화

Windows PowerShell:

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 4. 의존성 설치

```bash
pip install -r requirements.txt
```

### 5. 실행

기본 실행은 `asset/input_{good | bad}.mp4` 영상을 사용합니다.

```bash
python main.py
```

실행 중 화면 창이 뜨면 `q` 키로 종료할 수 있습니다. 분석 결과는 실행한 위치의 `pose_output.json`에 저장됩니다.

## 입력 영상 변경

[main.py](main.py)에서 아래 부분을 원하는 영상 파일로 바꾸면 됩니다.

```python
source = cv2.VideoCapture(filename=str(project_root / "asset" / "input_bad.mp4"))
```

웹캠을 사용하려면 위 줄 대신 아래 줄을 사용하세요.

```python
source = cv2.VideoCapture(0)
```

## 저장소 구조

```text
Pose-Agent/
├── main.py
│   # 입력 영상 또는 웹캠을 열고 PoseAgent를 실행
│
├── requirements.txt
│   # 프로젝트 실행에 필요한 Python 패키지 목록
│
├── pose_landmarker_lite.task
│   # MediaPipe Pose Landmarker 모델 파일
│   # 포즈 랜드마크를 추출할 때 사용하며 Git LFS로 관리
│
├── asset/
│   ├── input_bad.mp4
│   │   # 테스트용 나쁜 자세 예시 영상
│   └── input_good.mp4
│       # 테스트용 좋은 자세 예시 영상
│
├── model/
│   └── pose_model.pkl
│       # 추출된 특징값을 바탕으로 자세 상태를 분석하는 학습 모델
│
└── pose/
    ├── __init__.py
    │
    ├── pose_agent.py
    │   # 전체 실행 흐름을 관리하는 핵심 클래스
    │   # 포즈 추출, 특징 추출, 자세 분석, 보상 업데이트를 연결
    │
    ├── pose_extractor.py
    │   # MediaPipe를 사용해 프레임에서 포즈 랜드마크를 추출
    │   # 화면에 관절점과 연결선을 그리는 기능 포함
    │
    ├── feature_extractor.py
    │   # 랜드마크 좌표를 자세 분석에 사용할 특징값으로 변환
    │   # 일정 길이의 프레임 시퀀스를 버퍼로 관리
    │
    ├── pose_analyzer.py
    │   # pose_model.pkl을 로드해 자세 위험도와 피드백을 계산
    │
    └── q_pose_reward_updater.py
        # 분석 결과를 바탕으로 상태, 행동, 보상 값을 관리
        # 강화학습 방식의 피드백 선택 로직을 담당
```

## 필요한 모델 파일

실행 전에 아래 파일들이 있어야 합니다.

- `pose_landmarker_lite.task`
- `model/pose_model.pkl`

`pose_landmarker_lite.task`가 없거나 용량이 너무 작으면 Git LFS 파일을 제대로 받지 못한 상태일 수 있습니다.

```bash
git lfs pull
```

## 자주 발생하는 문제

`pose_landmarker_lite.task` 또는 `model/pose_model.pkl`을 찾을 수 없다는 오류가 나면:

```bash
cd Pose-Agent
git lfs pull
python main.py
```

의존성 관련 오류가 나면 가상환경이 활성화되어 있는지 확인한 뒤 다시 설치하세요.

```bash
pip install -r requirements.txt
```
