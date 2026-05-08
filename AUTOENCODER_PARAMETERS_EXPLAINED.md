# 🎯 Autoencoder Parameters - Quick Guide

## 📊 3 Main Parameters:

---

## 1️⃣ **K-Factor (autoencoder_k_factor = 3.0)**

**Kya Hai:** Training time pe threshold calculate karne ka multiplier

**Formula:** `Threshold = Mean + (K × StdDev)`

**Kaam:** 
- Training data ke errors ka mean aur standard deviation se final threshold calculate karta hai
- Higher K = Higher threshold = Kam detection
- Lower K = Lower threshold = Zyada detection

**Kab Use:** Sirf **training time** (model retrain karte waqt)

**Effect:**
- K = 2.0 → Strict (zyada anomalies)
- K = 3.0 → Balanced ✅ (recommended)
- K = 4.0 → Lenient (kam anomalies)

---

## 2️⃣ **Autoencoder Threshold (autoencoder_threshold = 2.92)**

**Kya Hai:** Har transaction ka reconstruction error isse compare hota hai

**Formula:** `If error > threshold → ANOMALY`

**Kaam:**
- Transaction ka pattern check karta hai
- Unusual pattern = High error = Anomaly
- Normal pattern = Low error = Safe

**Kab Use:** **Har transaction** pe runtime

**Effect:**
- Threshold badhao (3.5) → Kam false positives
- Threshold ghatao (2.0) → Zyada detection

**Example:**
```
Error: 0.43 < Threshold: 2.92 → ✅ Normal
Error: 10.5 > Threshold: 2.92 → 🚨 Anomaly
```

**Special:** Config screen se change karo → 60 seconds mein apply (no restart!)

---

## 3️⃣ **AE Score Boost (AE_SCORE_BOOST = 0.10)**

**Kya Hai:** AE anomaly detect kare toh risk score mein kitna boost

**Formula:** `Risk Score += (AE_Error × Boost)`

**Kaam:**
- Autoencoder ka detection final decision mein reflect karta hai
- Bina boost ke AE ka impact kam hota hai
- Boost se serious anomalies HIGH risk ban jate hain

**Kab Use:** Runtime pe jab **AE anomaly detect** kare

**Kyun Zaruri:**
```
Without Boost (0.0):
  AE detects huge anomaly → Risk stays same ❌
  
With Boost (0.10):
  AE detects huge anomaly → Risk increases ✅
  Serious fraud gets HIGH priority
```

**Effect:**
- 0.0 → AE ignored (logging only)
- 0.05 → Minimal impact
- 0.10 → Balanced ✅ (recommended)
- 0.20 → Strong impact (high security)

---

## 🎯 Quick Decision Guide:

### **Zyada False Positives:**
- ✅ Threshold badhao (2.92 → 3.5)
- ✅ Boost ghatao (0.10 → 0.05)

### **Fraud Miss Ho Raha:**
- ✅ Threshold ghatao (2.92 → 2.0)
- ✅ Boost badhao (0.10 → 0.15)

### **Model Retrain:**
- ✅ K-factor adjust karo (if needed)
- ✅ Run: `python backend/train_autoencoder.py`

---

## 📊 Summary Table:

| Parameter | Runtime Change? | Purpose | Default |
|-----------|----------------|---------|---------|
| **K-Factor** | ❌ No (retrain) | Threshold calculation | 3.0 |
| **Threshold** | ✅ Yes (60s) | Anomaly detection | 2.92 |
| **Score Boost** | ✅ Yes (instant) | Risk escalation | 0.10 |

---

## 💡 Real Example:

**Normal Transaction:**
```
Amount: 750 AED
Error: 0.43 < Threshold: 3.5 → ✅ APPROVED
```

**Fraud Transaction:**
```
Amount: 999,999 AED
Error: 10553 > Threshold: 3.5 → 🚨 ANOMALY
Risk: 0.75 + (10553 × 0.10) = 1.0 → HIGH RISK
Decision: BLOCKED
```
