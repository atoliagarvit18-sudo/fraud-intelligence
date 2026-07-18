import librosa


def analyze_voice(audio_path):
    y, sr = librosa.load(audio_path, sr=16000)

    duration = librosa.get_duration(y=y, sr=sr)

    rms = librosa.feature.rms(y=y)[0].mean()

    zero_crossing = librosa.feature.zero_crossing_rate(y)[0].mean()

    if rms > 0.05:
        quality = "Good"
    elif rms > 0.02:
        quality = "Fair"
    else:
        quality = "Poor"

    return {
        "duration_seconds": round(duration, 2),
        "sample_rate": sr,
        "average_energy": round(float(rms), 4),
        "zero_crossing_rate": round(float(zero_crossing), 4),
        "audio_quality": quality
    }

if __name__ == "__main__":
    print(analyze_voice("audio/sample.mp3"))