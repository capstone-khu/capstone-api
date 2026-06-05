DEFAULT_MODEL_PATH = "fixtures/models/pose_model.pkl"

FEATURE_DIRECTIONS = {0: "both", 1: "both", 2: "high", 3: "both", 4: "low", 5: "both"}

CAUTION_THRESHOLD = 1.5
SEVERE_THRESHOLD = 3.0
STABLE_SCORE = 45.0
RISK_SCORE = 70.0


class PostureAnalyzer:
    """pose_model.pkl(sklearn 파이프라인) 기반 자세 분석.

    프로토타입 PoseFeedbackAnalyzer 를 트리밍한 것 — 마디별 6 feature 시퀀스를 받아
    case·final_score·가장 위험한 feature 를 산출한다(코칭 문구는 policy 가 담당).
    joblib/numpy 는 측정 deps 라 메서드 안에서 lazy import.
    """

    def __init__(self, model_path: str | None = None) -> None:
        import joblib

        bundle = joblib.load(model_path or DEFAULT_MODEL_PATH)
        self.model = bundle["model"]
        self.feature_mean = bundle["feature_mean"]
        self.feature_std = bundle["feature_std"]

    def analyze(self, sample) -> dict:
        fv = self._to_feature_vector(sample)
        bad_prob = float(self.model.predict_proba(fv.reshape(1, -1))[0][1])
        scaled = self.model.named_steps["scaler"].transform(fv.reshape(1, -1))[0]
        weights = self.model.named_steps["classifier"].coef_[0]

        details = []
        biomech_risk = 0.0
        for idx, value in enumerate(fv):
            z = (value - self.feature_mean[idx]) / (self.feature_std[idx] + 1e-8)
            risk_z = self._directional_risk(idx, float(z))
            biomech_risk += risk_z
            details.append(
                {
                    "feature_index": idx,
                    "risk_z": risk_z,
                    "status": self._status(risk_z),
                    "bad_contribution": max(0.0, float(scaled[idx] * weights[idx])),
                }
            )

        final_score = self._hybrid_score(bad_prob, biomech_risk)
        severe = sum(1 for d in details if d["status"] == "심각")
        danger = sum(1 for d in details if d["status"] == "주의")
        case = self._case(final_score)

        problems = [d for d in details if d["status"] != "정상"]
        problems.sort(key=lambda d: (d["risk_z"], d["bad_contribution"]), reverse=True)
        top = problems[0]["feature_index"] if problems else None

        return {
            "case": case,
            "final_score": round(final_score, 2),
            "stable": case == "안정",
            "top_feature_index": top,
            "severe_count": severe,
            "danger_count": danger,
        }

    def _to_feature_vector(self, sample):
        import numpy as np

        sample = np.asarray(sample, dtype=np.float32)
        if sample.shape == (6,):
            return sample
        if sample.ndim == 2 and sample.shape[1] == 6:
            return np.median(sample, axis=0)
        raise ValueError("feature 는 (6,) 또는 (N, 6) 형태여야 합니다")

    def _directional_risk(self, idx: int, z: float) -> float:
        direction = FEATURE_DIRECTIONS[idx]
        if direction == "high":
            return max(0.0, z)
        if direction == "low":
            return max(0.0, -z)
        return abs(z)

    def _status(self, risk_z: float) -> str:
        if risk_z <= CAUTION_THRESHOLD:
            return "정상"
        if risk_z <= SEVERE_THRESHOLD:
            return "주의"
        return "심각"

    def _hybrid_score(self, bad_prob: float, biomech_risk: float) -> float:
        global_risk = bad_prob * 100
        biomech_score = min(100.0, biomech_risk / 6 * 100)
        return 0.6 * global_risk + 0.4 * biomech_score

    def _case(self, final_score: float) -> str:
        if final_score < STABLE_SCORE:
            return "안정"
        if final_score < RISK_SCORE:
            return "주의"
        return "위험"
