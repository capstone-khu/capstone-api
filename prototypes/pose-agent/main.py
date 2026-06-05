import cv2
from pathlib import Path

from pose.pose_agent import PoseAgent


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent
    source = cv2.VideoCapture(filename=str(project_root / "asset" / "input_good.mp4"))
    # source = cv2.VideoCapture(0)  # 웹캠 사용 시
    source.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    agent = PoseAgent(source)
    agent.run()

