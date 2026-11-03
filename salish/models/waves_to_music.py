"""
Turn a WAVEWATCH III swell forecast into sound.

Takes the DataFrame produced by salish.ingest.wavewatch.fetch_forecast (one row per
valid time per partition: valid, partition, height, period, direction) and renders
each partition (Swell 1-3, Wind wave) as its own voice:

    pitch    = wave frequency (1/period) shifted up OCTAVES_UP octaves, so the ratios
               between swells are kept (a 15 s swell -> ~273 Hz, a 5 s wind wave -> ~819 Hz)
    loudness = significant height, relative to the largest height in the forecast
    pan      = direction the waves come from: westerly swell on the left, easterly on
               the right (as if facing north on a map)

Each forecast time step lasts seconds_per_step; pitch, loudness and pan glide
linearly between steps so the sound evolves with the forecast.

The track opens with a short reference tone: an INTRO_PERIOD wave of INTRO_HEIGHT,
on the same pitch and loudness scale as the forecast, so the swells that follow
can be heard against it.
"""

import wave

import numpy as np
import pandas as pd

from salish.paths import ARTIFACTS

# 12.5 seocnd period is a low E on a guitar
# 6 seocnd period is the high e 

AUDIO = ARTIFACTS / "audio"
OUT_PATH = AUDIO / "swell_forecast.mp3"
SAMPLE_RATE = 44100
MP3_BITRATE = 192            # kbps
SECONDS_PER_STEP = 2.0
OCTAVES_UP = 10            # x4096: ocean wave frequencies (0.05-0.25 Hz) -> ~200-1000 Hz
MIN_HEIGHT = 0.05            # m; partitions smaller than this are silent
FADE_SECONDS = 0.5           # fade in/out at the ends of the file
INTRO_PERIOD = 12.5          # s; reference tone played before the forecast (an E)
INTRO_HEIGHT = 1.0           # m
INTRO_SECONDS = 4.0
INTRO_FADE_SECONDS = 0.5    # fade in and out within the intro

PARTITIONS = ["Swell 1", "Swell 2", "Swell 3", "Wind wave"]


def reference_height(df):
    """Height that maps to amplitude 1: the largest non-negligible height in the
    forecast, or 1.0 if every partition is calm."""
    hmax = df.height[df.height > MIN_HEIGHT].max()
    return hmax if hmax > 0 else 1.0                # NaN > 0 is False, so all-NaN -> 1.0


def forecast_to_tracks(df):
    """
    Pivot the long forecast DataFrame into one row per valid time and, per partition,
    audible frequency (Hz), amplitude (0-1) and pan (-1 left .. 1 right).
    Missing or negligible partitions get amplitude 0.
    """
    hmax = reference_height(df)
    df = df.copy()
    df.loc[~(df.height > MIN_HEIGHT), "height"] = 0.0
    times = sorted(df.valid.unique())

    tracks = {}
    for name in PARTITIONS:
        p = df[df.partition == name].set_index("valid").reindex(times)
        height = p.height.fillna(0.0)
        # hold the last known period/direction through gaps so a voice doesn't jump
        period = p.period.ffill().bfill().fillna(10.0)
        direction = p.direction.ffill().bfill().fillna(270.0)
        tracks[name] = pd.DataFrame({
            "freq": 2 ** OCTAVES_UP / period,
            "amp": height / hmax,
            "pan": np.sin(np.radians(direction)),
        }, index=pd.DatetimeIndex(times, name="valid"))
    return tracks


def render_tracks(tracks, seconds_per_step=SECONDS_PER_STEP, sample_rate=SAMPLE_RATE):
    """Synthesise the tracks into a stereo float array of shape (n_samples, 2)."""
    n_steps = len(next(iter(tracks.values())))
    n = int(round(n_steps * seconds_per_step * sample_rate))
    # sample positions in units of forecast steps, so interpolation hits each step's value
    x = np.arange(n) / (seconds_per_step * sample_rate)
    steps = np.arange(n_steps)

    out = np.zeros((n, 2))
    for track in tracks.values():
        freq = np.interp(x, steps, track.freq.values)
        amp = np.interp(x, steps, track.amp.values)
        pan = np.interp(x, steps, track.pan.values)
        # integrate frequency to get phase, so gliding pitch has no clicks
        phase = 2 * np.pi * np.cumsum(freq) / sample_rate
        tone = amp * np.sin(phase)
        # equal-power pan
        angle = (pan + 1) * np.pi / 4
        out[:, 0] += tone * np.cos(angle)
        out[:, 1] += tone * np.sin(angle)

    return apply_fade(out, FADE_SECONDS, sample_rate)


def apply_fade(audio, seconds, sample_rate=SAMPLE_RATE):
    """Linear fade in at the start and out at the end of a (n_samples, 2) array, in place."""
    n = len(audio)
    fade = min(int(seconds * sample_rate), n // 2)
    ramp = np.linspace(0, 1, fade)[:, None]
    audio[:fade] *= ramp
    audio[n - fade:] *= ramp[::-1]
    return audio


def intro_tone(hmax, sample_rate=SAMPLE_RATE):
    """Reference tone: an INTRO_PERIOD wave of INTRO_HEIGHT on the forecast's pitch and
    loudness scale (amplitude = INTRO_HEIGHT / hmax), panned centre."""
    t = np.arange(int(INTRO_SECONDS * sample_rate)) / sample_rate
    tone = INTRO_HEIGHT / hmax * np.sin(2 * np.pi * 2 ** OCTAVES_UP / INTRO_PERIOD * t)
    # centre pan with the same equal-power gain the forecast voices get
    out = np.column_stack([tone, tone]) * np.cos(np.pi / 4)
    return apply_fade(out, INTRO_FADE_SECONDS, sample_rate)


def to_pcm(audio):
    """Normalise to 90% full scale and convert to interleaved 16-bit stereo samples."""
    peak = np.abs(audio).max()
    if peak > 0:
        audio = audio * (0.9 / peak)
    return (audio * 32767).astype("<i2")


def write_wav(audio, out_path=OUT_PATH, sample_rate=SAMPLE_RATE):
    """Write a 16-bit stereo WAV."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(to_pcm(audio).tobytes())
    print(f"Saved {out_path} ({len(audio) / sample_rate:.1f} s)")
    return out_path


def write_mp3(audio, out_path=OUT_PATH, sample_rate=SAMPLE_RATE, bitrate=MP3_BITRATE):
    """Write a stereo MP3 with the LAME encoder."""
    import lameenc

    encoder = lameenc.Encoder()
    encoder.set_bit_rate(bitrate)
    encoder.set_in_sample_rate(sample_rate)
    encoder.set_channels(2)
    encoder.set_quality(2)                          # 2 = high quality, 7 = fast
    mp3 = encoder.encode(to_pcm(audio).tobytes()) + encoder.flush()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(mp3)
    print(f"Saved {out_path} ({len(audio) / sample_rate:.1f} s)")
    return out_path


def forecast_to_audio(df, out_path=OUT_PATH, seconds_per_step=SECONDS_PER_STEP,
                      sample_rate=SAMPLE_RATE, intro=True):
    """WAVEWATCH III forecast DataFrame (from fetch_forecast) -> audio file; returns its path.
    The format follows out_path's extension: .mp3 or .wav. With intro=True the
    reference tone plays first."""
    if df.empty:
        raise ValueError("forecast DataFrame is empty")
    tracks = forecast_to_tracks(df)
    audio = render_tracks(tracks, seconds_per_step, sample_rate)
    if intro:
        audio = np.concatenate([intro_tone(reference_height(df), sample_rate), audio])
    write = write_wav if out_path.suffix.lower() == ".wav" else write_mp3
    return write(audio, out_path, sample_rate)


def test_forecast(n_steps=8):
    """Made-up forecast in fetch_forecast's format: a building groundswell, steady
    southwest swell and an easterly wind wave that drops out halfway."""
    rows = []
    for i, valid in enumerate(pd.date_range("2026-01-01", periods=n_steps, freq="h")):
        rows += [dict(valid=valid, partition="Swell 1", height=1.5 + 0.2 * i, period=17 - 0.5 * i, direction=275),
                 dict(valid=valid, partition="Swell 2", height=0.8, period=10.0, direction=220),
                 dict(valid=valid, partition="Wind wave", height=0.5 if i < n_steps // 2 else np.nan,
                      period=5.0, direction=100)]
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import subprocess
    import sys

    if "--test" in sys.argv:      # python -m salish.models.waves_to_music --test
        path = forecast_to_audio(test_forecast(), out_path=AUDIO / "test_waves.mp3")
        subprocess.run(["afplay", str(path)])
        sys.exit()

    from salish.core.stations import get_station
    from salish.ingest.wavewatch import STATION_ID, fetch_forecast, hourly_times, latest_run

    station = get_station(STATION_ID)
    run = latest_run()
    df, _ = fetch_forecast(station["lat"], station["lon"], run, hourly_times(run))
    forecast_to_audio(df)

