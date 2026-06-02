from pathlib import Path
import joblib
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "model" / "pose_model.pkl"


class PoseFeedbackAnalyzer:
    """
    Runtime posture analyzer.
    """

    FEATURE_CONTEXT = {
        0: "왼손목-왼어깨 거리",
        1: "양쪽 어깨의 높이 차이",
        2: "왼손목 속도",
        3: "왼팔 각도",
        4: "오른팔 각도",
        5: "오른손목 각도",
    }

    FEATURE_DIRECTIONS = {
        0: "both",
        1: "both",
        2: "high",
        3: "both",
        4: "low",
        5: "both",
    }

    FEATURE_PROBLEMS = {
        0: "왼손 포지션이 흔들리며 손과 어깨의 정렬이 불안정합니다.",
        1: "양쪽 어깨 높이 차이가 발생하여 상체 균형이 무너지고 있습니다.",
        2: "왼손목 움직임이 과도하여 운지 안정성이 저하되고 있습니다.",
        3: "왼팔 자세가 흐트러지며 바이올린 지지 자세가 불안정합니다.",
        4: "오른팔 각도가 감소하며 보잉 자세가 무너지고 있습니다.",
        5: "오른손목 정렬이 흐트러져 활의 움직임이 불안정합니다.",
    }

    COACHING_RULES = {
        0: lambda z: "왼어깨에 힘을 빼고 손과 어깨 거리를 유지하세요.",
        1: lambda z: "양쪽 어깨 높이를 일정하게 유지하세요.",
        2: lambda z: "왼손목 힘을 빼고 손가락 중심으로 운지하세요.",
        3: lambda z: "왼팔 각도를 안정적으로 유지하세요.",
        4: lambda z: "오른팔 각도를 유지하며 자연스럽게 보잉하세요.",
        5: lambda z: "오른손목 힘을 빼고 활의 직선 움직임을 유지하세요.",
    }

    def __init__(self, model_path=None):
        model_path = self._resolve_model_path(model_path)

        bundle = joblib.load(model_path)
        self.model = bundle["model"]
        self.feature_mean = bundle["feature_mean"]
        self.feature_std = bundle["feature_std"]

    def _resolve_model_path(self, model_path):
        path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        if not path.is_absolute():
            candidates = [
                Path.cwd() / path,
                PROJECT_ROOT / path,
            ]
            path = next((candidate for candidate in candidates if candidate.exists()), path)

        if not path.exists():
            raise FileNotFoundError(
                f"Model file not found: {path}. "
                f"Expected default model at: {DEFAULT_MODEL_PATH}"
            )

        return path

    @staticmethod
    def summarize_sequence(sequence):
        sequence = np.asarray(sequence, dtype=np.float32)
        return np.median(sequence, axis=0)

    def analyze(self, sample):

        feature_vector = self._to_feature_vector(sample)

        bad_probability = self._predict_bad_probability(feature_vector)

        explanations = []
        biomechanical_risk = 0.0
        severe_count = 0
        danger_count = 0

        scaled_sample = self.model.named_steps["scaler"].transform(
            feature_vector.reshape(1, -1)
        )[0]

        weights = self.model.named_steps["classifier"].coef_[0]

        for idx, value in enumerate(feature_vector):

            z_score = (
                (value - self.feature_mean[idx])
                / (self.feature_std[idx] + 1e-8)
            )

            risk_z = self._compute_directional_risk(idx, z_score)

            status = self._classify_deviation(risk_z)

            if status == "심각":
                severe_count += 1
            elif status == "주의":
                danger_count += 1

            contribution = scaled_sample[idx] * weights[idx]
            bad_contribution = max(0.0, float(contribution))

            biomechanical_risk += risk_z

            explanations.append({
                "feature_index": idx,
                "feature": self.FEATURE_CONTEXT[idx],
                "value": float(value),
                "z_score": float(z_score),
                "risk_z": float(risk_z),
                "status": status,
                "contribution": float(contribution),
                "bad_contribution": bad_contribution,
                "warning": self.FEATURE_PROBLEMS[idx],
                "coaching": (
                    self.COACHING_RULES[idx](z_score)
                    if status != "정상"
                    else None
                ),
            })

        total_bad_contribution = sum(
            item["bad_contribution"]
            for item in explanations
        )

        for item in explanations:
            item["risk_percent"] = float(
                item["bad_contribution"]
                / (total_bad_contribution + 1e-8)
                * 100
            )

        explanations.sort(
            key=lambda item: (
                item["risk_z"],
                item["bad_contribution"],
            ),
            reverse=True,
        )

        final_score = self._compute_hybrid_score(
            bad_probability,
            biomechanical_risk,
        )

        posture_case = self._determine_posture_case(
            final_score,
            severe_count,
            danger_count,
            total_bad_contribution,
        )

        return {
            "case": posture_case,
            "final_score": float(round(final_score, 2)),
            "classifier_probability": float(
                round(bad_probability * 100, 2)
            ),
            "biomechanical_risk": float(
                round(biomechanical_risk, 4)
            ),
            "details": explanations,
            "summary": self._build_summary(
                posture_case,
                explanations,
            ),
        }

    def analyze_many(self, samples):
        samples = np.asarray(samples, dtype=np.float32)

        if samples.ndim not in (2, 3):
            raise ValueError(
                "samples must have shape (N, 6) or (N, 30, 6)"
            )

        return [self.analyze(s) for s in samples]

    def _to_feature_vector(self, sample):
        sample = np.asarray(sample, dtype=np.float32)

        if sample.shape == (6,):
            return sample

        if sample.ndim == 2 and sample.shape[1] == 6:
            return self.summarize_sequence(sample)

        raise ValueError("Invalid input shape")

    def _predict_bad_probability(self, x):
        return float(
            self.model.predict_proba(x.reshape(1, -1))[0][1]
        )

    def _compute_directional_risk(self, idx, z):

        direction = self.FEATURE_DIRECTIONS[idx]

        if direction == "high":
            return max(0.0, float(z))
        if direction == "low":
            return max(0.0, float(-z))

        return abs(float(z))

    @staticmethod
    def _classify_deviation(risk_z):

        if risk_z <= 1.5:
            return "정상"
        if risk_z <= 3:
            return "주의"
        return "심각"

    @staticmethod
    def _compute_hybrid_score(
        classifier_probability,
        biomechanical_risk,
    ):

        global_risk = classifier_probability * 100

        biomech_score = min(
            100,
            biomechanical_risk / 6 * 100,
        )

        return (
            0.6 * global_risk
            + 0.4 * biomech_score
        )

    @staticmethod
    def _determine_posture_case(
        final_score,
        severe_count,
        danger_count,
        total_bad_contribution,
    ):


        if final_score < 45:
            return "안정"
        
        if severe_count <= 2 and final_score < 70:
            return "주의"

        if final_score < 70:
            return "주의"
        
        if final_score >= 70:
            return "위험"

        if danger_count < 2:
            return "주의"

        return "위험"

    @staticmethod
    def _build_summary(
        posture_case,
        explanations,
        top_k=3,
    ):

        # 1) 정상 제외 + risk_percent 0.0 제외
        valid_items = [
            item for item in explanations
            if item["status"] != "정상" and item["risk_percent"] > 0.0
        ]

        # 2) risk_percent 기준 정렬 (내림차순)
        valid_items.sort(key=lambda x: x["risk_percent"], reverse=True)

        # 3) top_k 제한 (최대 3개)
        valid_items = valid_items[:top_k]

        # 4) coaching 규칙
        if valid_items:
            # 가장 위험한 1개 coaching만 사용
            coaching = [valid_items[0]["coaching"]]

        if posture_case == "안정":
            coaching = ["현재 자세는 안정적입니다. 계속 유지하세요!"]

        result = {
            "posture": posture_case,
            "coaching": coaching,
        }

        # 5) top_issues 구성
        if valid_items:
            result["top_issues"] = [
                {
                    "feature": item["feature"],
                    "status": item["status"],
                    "risk_percent": round(item["risk_percent"], 2),
                    "coaching": item["coaching"],
                }
                for item in valid_items
            ]

        # 6) severe_count & danger_count 추가
        result["severe_count"] = sum(
            1 for item in explanations if item["status"] == "심각"
        )
        result["danger_count"] = sum(
            1 for item in explanations if item["status"] == "주의"
        )

        return result
