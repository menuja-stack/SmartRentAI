"""
Run this ONCE to train the disaster risk model from your dataset.
Usage: python train_model.py
"""
import requests

print("Training SafeRent Location Intelligence model...")
print("This will process 401,775 records — takes 1–3 minutes...")

try:
    resp = requests.post("http://localhost:8004/train", timeout=300)
    data = resp.json()
    print("\n✅ Training complete!")
    print(f"  AUC-ROC:  {data['metrics']['auc_roc']}")
    print(f"  Accuracy: {data['metrics']['accuracy']}")
    print(f"  F1 Score: {data['metrics']['f1']}")
    print(f"  Samples:  {data['metrics']['samples']:,}")
    print("\nYou can now use http://localhost:8004/score/Colombo")
except Exception as e:
    print(f"❌ Error: {e}")
    print("Make sure the service is running: python app.py")
