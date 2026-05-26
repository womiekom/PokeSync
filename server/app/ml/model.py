
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from app.ml.feature_engineering import extract_team_features

class ArchetypeModel:
    def __init__(self, model_path=None, encoder_path=None):
        self.model = None
        self.le = None
        self.feature_names = None
        
        if model_path and encoder_path:
            self.load(model_path, encoder_path)

    def train(self, X, y):
        self.le = LabelEncoder()
        y_encoded = self.le.fit_transform(y)
        self.feature_names = X.columns.tolist()

        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
        )

        self.model = RandomForestClassifier(
            n_estimators=300, max_depth=12, min_samples_split=5, random_state=42
        )
        self.model.fit(X_train, y_train)
        
        accuracy = self.model.score(X_test, y_test)
        print(f"Model trained with accuracy: {accuracy}")
        return accuracy

    def save(self, model_path, encoder_path):
        joblib.dump(self.model, model_path)
        joblib.dump({"le": self.le, "feature_names": self.feature_names}, encoder_path)

    def load(self, model_path, encoder_path):
        self.model = joblib.load(model_path)
        meta = joblib.load(encoder_path)
        self.le = meta["le"]
        self.feature_names = meta["feature_names"]

    def predict(self, team, df):
        features = extract_team_features(team, df)
        if features is None:
            return None

        X_input = pd.DataFrame([features])
        X_input = X_input.reindex(columns=self.feature_names, fill_value=0)

        prediction_encoded = self.model.predict(X_input)[0]
        probabilities = self.model.predict_proba(X_input)[0]
        
        prediction = self.le.inverse_transform([prediction_encoded])[0]
        
        prob_dict = {
            label: round(float(prob), 3) 
            for label, prob in zip(self.le.classes_, probabilities)
        }

        return {
            "prediction": prediction,
            "probabilities": prob_dict,
            "features": features
        }

def explain_prediction(team, features):
    explanations = []
    
    if features.get("rain_synergy", 0) >= 4: explanations.append("Strong rain synergy detected.")
    if features.get("sun_synergy", 0) >= 4: explanations.append("Strong sun synergy detected.")
    if features.get("sand_synergy", 0) >= 4: explanations.append("Strong sand synergy detected.")
    if features.get("snow_synergy", 0) >= 4: explanations.append("Strong snow synergy detected.")
    if features.get("trick_room_synergy", 0) >= 4: explanations.append("Strong Trick Room synergy detected.")
    
    if features.get("fast_count", 0) >= 4: explanations.append("Team contains many fast attackers.")
    if features.get("very_bulky_count", 0) >= 3: explanations.append("Team contains multiple bulky walls.")
    if features.get("hyper_offense_score", 0) >= 8: explanations.append("High offensive pressure detected.")
    if features.get("stall_score", 0) >= 8: explanations.append("High defensive/stall presence detected.")

    if not explanations:
        explanations.append("Team has mixed archetype characteristics.")
        
    return explanations
