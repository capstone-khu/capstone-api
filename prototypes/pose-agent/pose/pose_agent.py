import json

import cv2

from pose.feature_extractor import FeatureExtractor
from pose.pose_extractor import PoseExtractor
from pose.pose_analyzer import PoseFeedbackAnalyzer
from pose.q_pose_reward_updater import Q_PoseRewardUpdater


class PoseAgent:
    def __init__(
        self,
        source,
        pose_extractor=None,
        feature_extractor=None,
        analyzer=None,
        output_path="pose_output.json",
        supervisor=None,
        feedback_interval_seconds=5.0,
    ):
        self.source = source
        self.fps = self._get_capture_fps()
        self.feedback_interval_seconds = feedback_interval_seconds
        self.next_feedback_timestamp = feedback_interval_seconds
        self.frame_index = 0

        self.pose_extractor = pose_extractor or PoseExtractor(self.source)
        self.feature_extractor = feature_extractor or FeatureExtractor(
            sequence_length=max(
                1,
                int(round(self.fps * feedback_interval_seconds)),
            ),
            stride=1,
        )
        self.analyzer = analyzer or PoseFeedbackAnalyzer()
        self.output_path = output_path
        self.supervisor = supervisor or Q_PoseRewardUpdater()

        self.prev_result = None
        self.prev_state = None
        self.prev_action = None
        self.measure_index = 0

    def run(self, display=True):
        try:
            while self.source.isOpened():
                ret, frame = self.source.read()
                if not ret:
                    break

                self.frame_index += 1
                landmarks, frame = self.pose_extractor.extract(frame)
                self.step(landmarks)

                if display:
                    cv2.imshow("PoseAgent", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
        finally:
            self.release()

    def step(self, landmarks, print_debug=True):
        if landmarks is None:
            return None

        features = self.pose_to_features(landmarks, print_debug=print_debug)
        sequence = self.feature_extractor.update_buffer(features)

        if sequence is None:
            return self._empty_step_result(features)

        timestamp = self.current_video_timestamp()
        if timestamp < self.next_feedback_timestamp:
            return self._empty_step_result(features)

        result = self.analyzer.analyze(sequence)
        feedback = result["summary"]
        current_state = self.supervisor.get_state(result, self.prev_state)
        self.measure_index += 1

        reward_info = None
        transition = None

        if self.prev_result is not None and self.prev_action is not None:
            reward_info = self.supervisor.compute_reward(
                self.prev_result,
                result,
                self.prev_state,
                current_state,
            )
            updated_q = self.supervisor.update(
                self.prev_state,
                self.prev_action,
                reward_info["reward"],
                current_state,
            )
            transition = {
                "previous_state": self.prev_state.as_tuple(),
                "current_state": current_state.as_tuple(),
                "action": self.prev_action,
                "updated_q": updated_q,
            }

        action = self.supervisor.choose_action(current_state, feedback=feedback)
        action_result = self.supervisor.execute_action(action, feedback)
        q_value = self.supervisor.q_value(current_state, action)
        agent_result = self._build_agent_result(
            result=result,
            feedback=feedback,
            state=current_state,
            action=action,
            action_result=action_result,
            reward_info=reward_info,
            q_value=q_value,
            transition=transition,
            timestamp=timestamp,
        )

        self.prev_result = result
        self.prev_state = current_state
        self.prev_action = action

        while self.next_feedback_timestamp <= timestamp:
            self.next_feedback_timestamp += self.feedback_interval_seconds

        self.write_result(agent_result)

        return agent_result

    def _empty_step_result(self, features):
        return {
            "features": features,
            "analysis": None,
            "feedback": None,
            "state": None,
            "action": None,
            "reward": None,
            "transition": None,
        }

    def _get_capture_fps(self):
        fps = self.source.get(cv2.CAP_PROP_FPS)
        if fps and fps > 0:
            return fps
        return 30.0

    def current_video_timestamp(self):
        timestamp = self.source.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        if timestamp > 0:
            return round(timestamp, 2)
        return round(self.frame_index / self.fps, 2)

    def pose_to_features(self, landmarks, print_debug=True):
        features = self.feature_extractor.compute(landmarks)
        return features

    def update_supervisor(self, result):
        if not self.supervisor:
            return None, None

        state = self.supervisor.get_state(result, prev_state=self.prev_state)
        if self.prev_result is None:
            return state, None

        reward_info = self.supervisor.compute_reward(
            self.prev_result,
            result,
            self.prev_state,
            state,
        )
        return state, reward_info

    def _build_agent_result(
        self,
        result,
        feedback,
        state,
        action,
        action_result,
        reward_info,
        q_value,
        transition,
        timestamp,
    ):
        supervisor_payload = {
            "agent": "posture",
            "measure": self.measure_index,
            "state": state.as_tuple(),
            "action_id": action_result["action_id"],
            "action": action,
            "feedback": action_result["feedback"],
            "reward": reward_info["reward"] if reward_info else None,
            "q": q_value,
            "meta": self._build_supervisor_meta(result, feedback),
        }

        return {
            "supervisor_payload": supervisor_payload,
            "pose_agent_meta": {
                "timestamp": timestamp,
                "case": result["case"],
                "final_score": result["final_score"],
                "biomechanical_risk": result["biomechanical_risk"],
                "reward": reward_info,
                "top_issues": feedback.get("top_issues", []),
                "coaching": feedback.get("coaching", []),
                "transition": transition,
            },
        }

    def _build_supervisor_meta(self, result, feedback):
        if self.supervisor.is_stable_result(result):
            return {}

        top_issues = feedback.get("top_issues", [])
        if not top_issues:
            return {}

        top_issue = max(
            top_issues,
            key=lambda item: item.get("risk_percent", 0.0),
        )
        return {
            "feature": top_issue.get("feature"),
            "risk_percent": top_issue.get("risk_percent"),
            "coaching": top_issue.get("coaching"),
        }

    def write_result(self, output):
        if not self.output_path:
            return

        with open(self.output_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(output, ensure_ascii=False, indent=4) + "\n")

    def release(self):
        self.pose_extractor.release()
        self.source.release()
        cv2.destroyAllWindows()
